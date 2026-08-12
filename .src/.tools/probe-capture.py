#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import platform
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

from runtime_integrity import IntegrityError, machine_id_digest, parse_machine_id, validate_compiled_identity_file, validate_p3_manifest

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_POLICY = ROOT / ".src/.configs/p4.02-probe-capture-policy.json"
EXPECTED_VERSION = "4.1.0.0.0.0"
EXPECTED_INFERNO = "cc4302a99167abec69b714cfd00c38caece7e7de"
EXPECTED_MACHINE = {"machine": "vmapple", "accelerator": "tcg", "cpu": "apple-gxf"}
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class CaptureError(RuntimeError): pass

def require(value: bool, message: str) -> None:
    if not value: raise CaptureError(message)

def load_json(path: Path) -> dict[str, Any]:
    try: value=json.loads(path.read_text(encoding="utf-8"))
    except (OSError,json.JSONDecodeError) as exc: raise CaptureError(f"could not read JSON {path}: {exc}") from exc
    require(isinstance(value,dict),f"top-level JSON must be object: {path}")
    return value

def canonical(data: Any) -> bytes: return (json.dumps(data,sort_keys=True,separators=(",",":"),ensure_ascii=False)+"\n").encode()
def sha256_bytes(data: bytes) -> str: return hashlib.sha256(data).hexdigest()
def sha256_file(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""): h.update(chunk)
    return h.hexdigest()
def git_blob(path: Path) -> str:
    data=path.read_bytes(); return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()
def digest_file(path: Path) -> dict[str,Any]:
    require(path.is_file(),f"input is not a file: {path}"); size=path.stat().st_size; require(size>0,f"input is empty: {path}")
    return {"sha256":sha256_file(path),"bytes":size}

def fingerprint(data: dict[str,Any], field: str, *, exclude=("classification",)) -> str:
    observed=data.get(field); require(isinstance(observed,str) and SHA256_RE.fullmatch(observed) is not None,f"{field} invalid")
    basis=dict(data); basis.pop(field,None)
    for key in exclude: basis.pop(key,None)
    expected=sha256_bytes(canonical(basis)); require(observed==expected,f"{field} does not reproduce")
    return observed

def validate_policy(policy: dict[str,Any]) -> None:
    require(policy.get("schema")==1 and policy.get("project_version")==EXPECTED_VERSION,"P4.02 schema/version mismatch")
    require(policy.get("part")=="Part 04" and policy.get("objective")=="P4.02" and policy.get("title")=="Integrated TCG Probe Capture","P4.02 identity drift")
    require(policy.get("source_lock",{}).get("inferno_revision")==EXPECTED_INFERNO,"P4.02 Inferno lock drift")
    require(policy.get("probe_contract")=={"machine":"vmapple","accelerator":"tcg","cpu":"apple-gxf","session_plan_classification":"P4_01_SESSION_PLAN_READY","runtime_result_prefix":"P1_07_PROBE_","runtime_manifest_role":"probe"},"P4.02 probe contract drift")
    require(policy.get("runtime_parameters")=={"ram":"4G","ram_mib":4096,"smp":4,"capture_seconds":30,"grace_seconds":3},"P4.02 runtime geometry drift")
    require(policy.get("required_trace_events")==["memory_region_ops_read","memory_region_ops_write"],"trace contract drift")
    require(policy.get("required_debug_items")==["guest_errors","unimp","int","cpu_reset"],"debug contract drift")
    require(policy.get("required_runtime_artifact_kinds")==["launcher_log","serial_log","qemu_debug_log","trace_capability_log"],"artifact contract drift")
    for key,value in policy.get("requirements",{}).items(): require(value is True,f"P4.02 requirement disabled: {key}")
    require(policy.get("next_objective")=="P4.03","P4.02 next objective drift")

def validate_locked_artifacts(policy: dict[str,Any]) -> None:
    seen=set()
    for item in policy.get("locked_project_artifacts",[]):
        rel=item.get("path"); require(isinstance(rel,str) and rel and rel not in seen,f"invalid/duplicate locked artifact: {rel}"); seen.add(rel)
        path=ROOT/rel; require(path.is_file(),f"locked artifact missing: {rel}"); require(git_blob(path)==item.get("git_blob_sha"),f"locked artifact drift: {rel}")

def validate_session_plan(plan: dict[str,Any], policy: dict[str,Any]) -> None:
    require(plan.get("schema")==1 and plan.get("classification")=="P4_01_SESSION_PLAN_READY","P4.01 probe plan not ready")
    require(plan.get("project_version")=="4.0.0.0.0.0" and plan.get("part")=="Part 04" and plan.get("objective")=="P4.01","P4.01 plan identity drift")
    require(plan.get("role")=="probe" and plan.get("guest_execution") is False and plan.get("runtime_evidence") is False,"P4.01 probe role/state drift")
    require(plan.get("integrated_machine")==EXPECTED_MACHINE,"P4.01 probe machine drift")
    fingerprint(plan,"session_fingerprint")
    trace=plan.get("trace_contract",{}); require(trace.get("events")==policy["required_trace_events"] and trace.get("debug_items")==policy["required_debug_items"],"P4.01 trace/debug drift")
    q=plan.get("qemu",{}); require(SHA256_RE.fullmatch(str(q.get("sha256",""))) is not None and isinstance(q.get("bytes"),int) and q["bytes"]>0,"P4.01 QEMU provenance invalid")
    require(q.get("capabilities")=={"machine_vmapple":True,"accelerator":"tcg","cpu":"apple-gxf"},"P4.01 QEMU capabilities drift")
    for name in ("firmware","auxiliary_storage","disk","machine_identity"):
        item=plan.get("guest_inputs",{}).get(name); require(isinstance(item,dict) and SHA256_RE.fullmatch(str(item.get("sha256",""))) is not None and isinstance(item.get("bytes"),int) and item["bytes"]>0,f"P4.01 input invalid: {name}")
    mid=plan.get("machine_uuid",{}); require(mid.get("encoding")=="uint64_decimal" and mid.get("semantic")=="vmapple_sdom_ecid" and mid.get("raw_value_stored") is False,"P4.01 machine-id metadata invalid")

def run_qemu(qemu: Path,*args: str) -> str:
    try: proc=subprocess.run([str(qemu),*args],text=True,capture_output=True,timeout=15,errors="replace")
    except (OSError,subprocess.TimeoutExpired) as exc: raise CaptureError(f"QEMU query failed: {exc}") from exc
    out=(proc.stdout or "")+(proc.stderr or ""); require(proc.returncode==0,f"QEMU query failed: {out.strip()}"); return out

def token_present(text: str,token: str) -> bool: return re.search(r"(^|[\s,])"+re.escape(token)+r"([\s,]|$)",text,re.MULTILINE) is not None

def validate_p3_binding(plan: dict[str,Any],path: Path) -> None:
    require(path.is_file(),"P3.06 manifest missing"); data=load_json(path)
    try: observed=validate_p3_manifest(data)
    except IntegrityError as exc: raise CaptureError(str(exc)) from exc
    expected=plan.get("p3_06",{}); require(sha256_file(path)==expected.get("sha256"),"P3.06 file digest differs from session plan"); require(observed==expected.get("platform_integration_fingerprint"),"P3.06 fingerprint differs from session plan")

def build_preflight(args: argparse.Namespace,policy: dict[str,Any]) -> dict[str,Any]:
    plan=load_json(Path(args.session_plan)); validate_session_plan(plan,policy); validate_p3_binding(plan,Path(args.p3_06_manifest))
    qpath=Path(args.qemu_bin); require(qpath.is_file() and os.access(qpath,os.X_OK),"QEMU missing/not executable"); q=plan["qemu"]
    require(sha256_file(qpath)==q["sha256"] and qpath.stat().st_size==q["bytes"],"QEMU binary changed after P4.01")
    lines=run_qemu(qpath,"-version").strip().splitlines(); require(lines and lines[0]==q["version"],"QEMU version changed")
    require(token_present(run_qemu(qpath,"-machine","help"),"vmapple") and token_present(run_qemu(qpath,"-accel","help"),"tcg") and token_present(run_qemu(qpath,"-cpu","help"),"apple-gxf"),"QEMU role capabilities changed")
    try: mid=parse_machine_id(args.machine_uuid); mid_meta=machine_id_digest(mid); validate_compiled_identity_file(Path(args.machine_identity),expected_machine_id=mid,allow_example=False)
    except IntegrityError as exc: raise CaptureError(str(exc)) from exc
    actual={"firmware":digest_file(Path(args.firmware)),"auxiliary_storage":digest_file(Path(args.auxiliary_storage)),"disk":digest_file(Path(args.disk)),"machine_identity":digest_file(Path(args.machine_identity)),"hardware_model":digest_file(Path(args.hardware_model)) if args.hardware_model else None}
    require(actual==plan["guest_inputs"],"guest inputs differ from P4.01 plan"); require(mid_meta["sha256"]==plan["machine_uuid"]["sha256"],"machine-id digest differs from P4.01 plan")
    result={"schema":1,"classification":"P4_02_PREFLIGHT_PASS","project_version":EXPECTED_VERSION,"role":"probe","guest_execution":False,"session_fingerprint":plan["session_fingerprint"],"platform_integration_fingerprint":plan["p3_06"]["platform_integration_fingerprint"],"host":{"os":platform.system(),"arch":platform.machine()},"qemu":{"binary_label":qpath.name,"sha256":q["sha256"],"bytes":q["bytes"],"version":q["version"],"machine":"vmapple","accelerator":"tcg","cpu":"apple-gxf"},"machine_uuid_sha256":mid_meta["sha256"],"guest_inputs":actual,"trace_contract":copy.deepcopy(plan["trace_contract"]),"raw_paths_stored":False}
    result["preflight_fingerprint"]=sha256_bytes(canonical({k:v for k,v in result.items() if k!="classification"})); return result

def launcher_value(path: Path,label: str,*,first=False) -> str:
    prefix=label+": "; vals=[line[len(prefix):] for line in path.read_text(encoding="utf-8",errors="replace").splitlines() if line.startswith(prefix)]; require(vals,f"launcher missing {label}"); return vals[0] if first else vals[-1]
def artifact_by_kind(manifest: dict[str,Any],kind: str) -> dict[str,Any]:
    matches=[i for i in manifest.get("artifacts",[]) if i.get("kind")==kind]; require(len(matches)==1,f"manifest must contain exactly one {kind}"); return matches[0]
def verify_preflight(pre: dict[str,Any]) -> None:
    require(pre.get("classification")=="P4_02_PREFLIGHT_PASS","P4.02 preflight did not pass"); fingerprint(pre,"preflight_fingerprint")

def finalize_capture(args: argparse.Namespace,policy: dict[str,Any]) -> dict[str,Any]:
    plan=load_json(Path(args.session_plan)); validate_session_plan(plan,policy)
    probe_path=Path(args.probe_manifest); launcher=Path(args.launcher_log); pre_path=Path(args.preflight)
    require(probe_path.is_file() and launcher.is_file() and pre_path.is_file(),"P4.02 finalization input missing")
    pre=load_json(pre_path); verify_preflight(pre); require(pre.get("session_fingerprint")==plan["session_fingerprint"],"preflight/session mismatch"); require(pre.get("platform_integration_fingerprint")==plan["p3_06"]["platform_integration_fingerprint"],"preflight/platform mismatch")
    probe=load_json(probe_path); require(probe.get("role")=="probe" and probe.get("source",{}).get("revision")==EXPECTED_INFERNO,"probe manifest identity/source drift")
    machine=probe.get("machine",{}); require(machine=={"type":"vmapple","accelerator":"tcg","cpu_model":"apple-gxf","ram_mib":4096,"smp":4},"probe machine geometry drift")
    result=probe.get("run",{}).get("result"); require(result in ("P1_07_PROBE_EXITED","P1_07_PROBE_TIMED_OUT"),"probe result is not admissible completed runtime")
    require(probe.get("guest_inputs")==plan.get("guest_inputs"),"probe inputs differ from plan"); require(probe.get("trace")=={"events":policy["required_trace_events"],"debug_items":policy["required_debug_items"]},"probe trace/debug contract drift")
    for kind in policy["required_runtime_artifact_kinds"]: artifact_by_kind(probe,kind)
    la=artifact_by_kind(probe,"launcher_log"); require(sha256_file(launcher)==la["sha256"] and launcher.stat().st_size==la["bytes"],"launcher artifact binding mismatch")
    require(launcher_value(launcher,"Run ID",first=True)==probe["run"]["id"],"launcher run ID differs from manifest")
    require(launcher_value(launcher,"Accelerator",first=True)=="tcg" and launcher_value(launcher,"CPU profile",first=True)=="apple-gxf","launcher role drift")
    require(launcher_value(launcher,"Classification")==result,"launcher result differs from manifest")
    require(launcher_value(launcher,"Machine ID SHA-256",first=True)==plan["machine_uuid"]["sha256"],"launcher machine-id digest differs from plan")
    capture={"schema":1,"classification":"P4_02_PROBE_CAPTURE_READY","project_version":EXPECTED_VERSION,"part":"Part 04","objective":"P4.02","runtime_observation":True,"divergence_promoted":False,"session_fingerprint":plan["session_fingerprint"],"platform_integration_fingerprint":plan["p3_06"]["platform_integration_fingerprint"],"preflight":{"sha256":sha256_file(pre_path),"preflight_fingerprint":pre["preflight_fingerprint"]},"probe_manifest":{"sha256":sha256_file(probe_path),"run_id":probe["run"]["id"],"started_utc":probe["run"]["started_utc"],"ended_utc":probe["run"]["ended_utc"],"result":result},"machine":{"type":"vmapple","accelerator":"tcg","cpu_model":"apple-gxf"},"guest_inputs":copy.deepcopy(probe["guest_inputs"]),"trace":copy.deepcopy(probe["trace"]),"artifacts":copy.deepcopy(probe["artifacts"]),"sanitization":{"raw_local_paths_stored":False,"raw_uuid_stored":False,"guest_input_contents_stored":False},"runtime_authority":{"manifest":"P1.09","promotion":"P1.10"},"next_objective":"P4.03"}
    capture["capture_fingerprint"]=sha256_bytes(canonical({k:v for k,v in capture.items() if k!="classification"})); return capture

def expect_policy_failure(policy,mutate,label):
    broken=copy.deepcopy(policy); mutate(broken)
    try: validate_policy(broken)
    except CaptureError: print(f"self-check reject: PASS: {label}"); return
    raise CaptureError(f"self-check mutation accepted: {label}")
def self_check(policy):
    validate_policy(policy); expect_policy_failure(policy,lambda d:d["probe_contract"].__setitem__("cpu","max"),"probe CPU drift"); expect_policy_failure(policy,lambda d:d["required_trace_events"].pop(),"trace weakening"); expect_policy_failure(policy,lambda d:d.__setitem__("next_objective","P4.04"),"objective skip"); print("P4.02 self-check: PASS")
def write_result(path,data):
    raw=canonical(data)
    if path: out=Path(path); out.parent.mkdir(parents=True,exist_ok=True); out.write_bytes(raw)
    sys.stdout.buffer.write(raw)
def main() -> int:
    p=argparse.ArgumentParser(); p.add_argument("--policy",default=str(DEFAULT_POLICY)); sub=p.add_subparsers(dest="command",required=True); sub.add_parser("validate-policy"); sub.add_parser("self-check")
    pre=sub.add_parser("preflight")
    for arg in ("session-plan","p3-06-manifest","qemu-bin","machine-uuid","firmware","auxiliary-storage","disk","machine-identity"): pre.add_argument("--"+arg,required=True)
    pre.add_argument("--hardware-model"); pre.add_argument("--output")
    fin=sub.add_parser("finalize"); fin.add_argument("--session-plan",required=True); fin.add_argument("--probe-manifest",required=True); fin.add_argument("--launcher-log",required=True); fin.add_argument("--preflight",required=True); fin.add_argument("--output")
    a=p.parse_args()
    try:
        policy=load_json(Path(a.policy)); validate_policy(policy); validate_locked_artifacts(policy)
        if a.command=="validate-policy": print("P4.02 probe capture policy: PASS")
        elif a.command=="self-check": self_check(policy)
        elif a.command=="preflight": write_result(a.output,build_preflight(a,policy))
        else: write_result(a.output,finalize_capture(a,policy))
        return 0
    except (OSError,json.JSONDecodeError,CaptureError,IntegrityError) as exc: print(f"P4.02 capture failure: {exc}",file=sys.stderr); return 1
if __name__=="__main__": raise SystemExit(main())

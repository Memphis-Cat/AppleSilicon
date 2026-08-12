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

ROOT=Path(__file__).resolve().parents[2]
DEFAULT_POLICY=ROOT/".src/.configs/p4.03-reference-capture-policy.json"
EXPECTED_VERSION="4.2.0.0.0.0"
EXPECTED_INFERNO="cc4302a99167abec69b714cfd00c38caece7e7de"
EXPECTED_MACHINE={"machine":"vmapple","accelerator":"hvf","cpu":"host"}
EXPECTED_HOST={"os":"Darwin","arch":"arm64"}
SHA256_RE=re.compile(r"^[0-9a-f]{64}$")

class ReferenceCaptureError(RuntimeError): pass
def require(v:bool,m:str)->None:
    if not v: raise ReferenceCaptureError(m)
def load_json(p:Path)->dict[str,Any]:
    try:v=json.loads(p.read_text(encoding="utf-8"))
    except (OSError,json.JSONDecodeError) as exc: raise ReferenceCaptureError(f"could not read JSON {p}: {exc}") from exc
    require(isinstance(v,dict),f"top-level JSON must be object: {p}"); return v
def canonical(d:Any)->bytes:return (json.dumps(d,sort_keys=True,separators=(",",":"),ensure_ascii=False)+"\n").encode()
def sha256_bytes(b:bytes)->str:return hashlib.sha256(b).hexdigest()
def sha256_file(p:Path)->str:
    h=hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda:f.read(1024*1024),b""):h.update(c)
    return h.hexdigest()
def git_blob(p:Path)->str:
    d=p.read_bytes();return hashlib.sha1(b"blob "+str(len(d)).encode()+b"\0"+d).hexdigest()
def digest_file(p:Path)->dict[str,Any]:
    require(p.is_file(),f"input is not a file: {p}");s=p.stat().st_size;require(s>0,f"input is empty: {p}");return {"sha256":sha256_file(p),"bytes":s}
def fingerprint(d:dict[str,Any],field:str,*,exclude=("classification",))->str:
    o=d.get(field);require(isinstance(o,str) and SHA256_RE.fullmatch(o) is not None,f"{field} invalid");b=dict(d);b.pop(field,None)
    for k in exclude:b.pop(k,None)
    require(o==sha256_bytes(canonical(b)),f"{field} does not reproduce");return o

def validate_policy(p:dict[str,Any])->None:
    require(p.get("schema")==1 and p.get("project_version")==EXPECTED_VERSION,"P4.03 schema/version mismatch")
    require(p.get("part")=="Part 04" and p.get("objective")=="P4.03" and p.get("title")=="Apple Silicon HVF Reference Capture","P4.03 identity drift")
    require(p.get("source_lock",{}).get("inferno_revision")==EXPECTED_INFERNO,"P4.03 Inferno lock drift")
    require(p.get("reference_contract")=={"machine":"vmapple","accelerator":"hvf","cpu":"host","required_host":EXPECTED_HOST,"session_plan_classification":"P4_01_SESSION_PLAN_READY","runtime_result_prefix":"P1_09_REFERENCE_","runtime_manifest_role":"reference"},"P4.03 contract drift")
    require(p.get("runtime_parameters")=={"ram":"4G","ram_mib":4096,"smp":4,"capture_seconds":30,"grace_seconds":3},"P4.03 runtime geometry drift")
    require(p.get("required_trace_events")==["memory_region_ops_read","memory_region_ops_write"],"trace contract drift")
    require(p.get("required_debug_items")==["guest_errors","unimp","int","cpu_reset"],"debug contract drift")
    require(p.get("required_manifest_artifact_kinds")==["serial_log","qemu_debug_log","trace_capability_log"],"manifest artifact drift")
    require(p.get("capture_only_artifact_kinds")==["launcher_log"],"capture-only artifact drift")
    for k,v in p.get("requirements",{}).items():require(v is True,f"P4.03 requirement disabled: {k}")
    require(p.get("next_objective")=="P4.04","P4.03 next objective drift")
def validate_locked_artifacts(p:dict[str,Any])->None:
    seen=set()
    for item in p.get("locked_project_artifacts",[]):
        rel=item.get("path");require(isinstance(rel,str) and rel and rel not in seen,f"invalid/duplicate locked artifact: {rel}");seen.add(rel);path=ROOT/rel;require(path.is_file(),f"locked artifact missing: {rel}");require(git_blob(path)==item.get("git_blob_sha"),f"locked artifact drift: {rel}")
def validate_session_plan(plan:dict[str,Any],policy:dict[str,Any])->None:
    require(plan.get("schema")==1 and plan.get("classification")=="P4_01_SESSION_PLAN_READY","P4.01 reference plan not ready")
    require(plan.get("project_version")=="4.0.0.0.0.0" and plan.get("part")=="Part 04" and plan.get("objective")=="P4.01","P4.01 plan identity drift")
    require(plan.get("role")=="reference" and plan.get("guest_execution") is False and plan.get("runtime_evidence") is False,"P4.01 reference role/state drift")
    require(plan.get("integrated_machine")==EXPECTED_MACHINE and plan.get("host")==EXPECTED_HOST,"P4.01 reference machine/host drift")
    fingerprint(plan,"session_fingerprint")
    t=plan.get("trace_contract",{});require(t.get("events")==policy["required_trace_events"] and t.get("debug_items")==policy["required_debug_items"],"P4.01 trace/debug drift")
    q=plan.get("qemu",{});require(SHA256_RE.fullmatch(str(q.get("sha256",""))) is not None and isinstance(q.get("bytes"),int) and q["bytes"]>0,"P4.01 QEMU provenance invalid");require(q.get("capabilities")=={"machine_vmapple":True,"accelerator":"hvf","cpu":"host"},"P4.01 QEMU capabilities drift")
    for name in ("firmware","auxiliary_storage","disk","machine_identity"):
        item=plan.get("guest_inputs",{}).get(name);require(isinstance(item,dict) and SHA256_RE.fullmatch(str(item.get("sha256",""))) is not None and isinstance(item.get("bytes"),int) and item["bytes"]>0,f"P4.01 input invalid: {name}")
    mid=plan.get("machine_uuid",{});require(mid.get("encoding")=="uint64_decimal" and mid.get("semantic")=="vmapple_sdom_ecid" and mid.get("raw_value_stored") is False,"P4.01 machine-id metadata invalid")
def run_qemu(q:Path,*args:str)->str:
    try:p=subprocess.run([str(q),*args],text=True,capture_output=True,timeout=15,errors="replace")
    except (OSError,subprocess.TimeoutExpired) as exc:raise ReferenceCaptureError(f"QEMU query failed: {exc}") from exc
    out=(p.stdout or "")+(p.stderr or "");require(p.returncode==0,f"QEMU query failed: {out.strip()}");return out
def token_present(t:str,x:str)->bool:return re.search(r"(^|[\s,])"+re.escape(x)+r"([\s,]|$)",t,re.MULTILINE) is not None
def validate_p3_binding(plan:dict[str,Any],path:Path)->None:
    require(path.is_file(),"P3.06 manifest missing");d=load_json(path)
    try:fp=validate_p3_manifest(d)
    except IntegrityError as exc:raise ReferenceCaptureError(str(exc)) from exc
    e=plan.get("p3_06",{});require(sha256_file(path)==e.get("sha256"),"P3.06 file digest differs from plan");require(fp==e.get("platform_integration_fingerprint"),"P3.06 fingerprint differs from plan")
def build_preflight(a:argparse.Namespace,p:dict[str,Any])->dict[str,Any]:
    host={"os":platform.system(),"arch":platform.machine()};require(host==EXPECTED_HOST,f"P4.03 requires Darwin/arm64; observed {host}")
    plan=load_json(Path(a.session_plan));validate_session_plan(plan,p);validate_p3_binding(plan,Path(a.p3_06_manifest))
    qp=Path(a.qemu_bin);require(qp.is_file() and os.access(qp,os.X_OK),"QEMU missing/not executable");q=plan["qemu"];require(sha256_file(qp)==q["sha256"] and qp.stat().st_size==q["bytes"],"QEMU changed after P4.01");lines=run_qemu(qp,"-version").strip().splitlines();require(lines and lines[0]==q["version"],"QEMU version changed");require(token_present(run_qemu(qp,"-machine","help"),"vmapple") and token_present(run_qemu(qp,"-accel","help"),"hvf") and token_present(run_qemu(qp,"-cpu","help"),"host"),"QEMU reference capabilities changed")
    try:mid=parse_machine_id(a.machine_uuid);meta=machine_id_digest(mid);validate_compiled_identity_file(Path(a.machine_identity),expected_machine_id=mid,allow_example=False)
    except IntegrityError as exc:raise ReferenceCaptureError(str(exc)) from exc
    actual={"firmware":digest_file(Path(a.firmware)),"auxiliary_storage":digest_file(Path(a.auxiliary_storage)),"disk":digest_file(Path(a.disk)),"machine_identity":digest_file(Path(a.machine_identity)),"hardware_model":digest_file(Path(a.hardware_model)) if a.hardware_model else None};require(actual==plan["guest_inputs"],"guest inputs differ from plan");require(meta["sha256"]==plan["machine_uuid"]["sha256"],"machine-id digest differs from plan")
    r={"schema":1,"classification":"P4_03_PREFLIGHT_PASS","project_version":EXPECTED_VERSION,"role":"reference","guest_execution":False,"session_fingerprint":plan["session_fingerprint"],"platform_integration_fingerprint":plan["p3_06"]["platform_integration_fingerprint"],"host":host,"qemu":{"binary_label":qp.name,"sha256":q["sha256"],"bytes":q["bytes"],"version":q["version"],"machine":"vmapple","accelerator":"hvf","cpu":"host"},"machine_uuid_sha256":meta["sha256"],"guest_inputs":actual,"trace_contract":copy.deepcopy(plan["trace_contract"]),"raw_paths_stored":False};r["preflight_fingerprint"]=sha256_bytes(canonical({k:v for k,v in r.items() if k!="classification"}));return r
def launcher_value(path:Path,label:str,*,first=False)->str:
    pre=label+": ";vals=[line[len(pre):] for line in path.read_text(encoding="utf-8",errors="replace").splitlines() if line.startswith(pre)];require(vals,f"launcher missing {label}");return vals[0] if first else vals[-1]
def artifact_by_kind(m:dict[str,Any],kind:str)->dict[str,Any]:
    xs=[i for i in m.get("artifacts",[]) if i.get("kind")==kind];require(len(xs)==1,f"reference manifest must contain exactly one {kind}");return xs[0]
def verify_preflight(pre:dict[str,Any])->None:require(pre.get("classification")=="P4_03_PREFLIGHT_PASS","P4.03 preflight did not pass");fingerprint(pre,"preflight_fingerprint")
def finalize_capture(a:argparse.Namespace,p:dict[str,Any])->dict[str,Any]:
    plan=load_json(Path(a.session_plan));validate_session_plan(plan,p);rp=Path(a.reference_manifest);launcher=Path(a.launcher_log);pp=Path(a.preflight);require(rp.is_file() and launcher.is_file() and pp.is_file(),"P4.03 finalization input missing");pre=load_json(pp);verify_preflight(pre);require(pre.get("session_fingerprint")==plan["session_fingerprint"] and pre.get("platform_integration_fingerprint")==plan["p3_06"]["platform_integration_fingerprint"],"preflight binding mismatch")
    ref=load_json(rp);require(ref.get("role")=="reference" and ref.get("source",{}).get("revision")==EXPECTED_INFERNO,"reference manifest identity/source drift");m=ref.get("machine",{});require(m=={"type":"vmapple","accelerator":"hvf","cpu_model":"host","ram_mib":4096,"smp":4},"reference machine geometry drift");result=ref.get("run",{}).get("result");require(result in ("P1_09_REFERENCE_EXITED","P1_09_REFERENCE_TIMED_OUT"),"reference result is not admissible completed runtime");require(ref.get("guest_inputs")==plan.get("guest_inputs"),"reference inputs differ from plan");require(ref.get("trace")=={"events":p["required_trace_events"],"debug_items":p["required_debug_items"]},"reference trace/debug contract drift")
    for kind in p["required_manifest_artifact_kinds"]:artifact_by_kind(ref,kind)
    require(launcher_value(launcher,"Run ID",first=True)==ref["run"]["id"],"launcher run ID differs from manifest");require(launcher_value(launcher,"Host OS",first=True)=="Darwin" and launcher_value(launcher,"Host architecture",first=True)=="arm64","launcher host drift");require(launcher_value(launcher,"Accelerator",first=True)=="hvf" and launcher_value(launcher,"CPU profile",first=True)=="host","launcher role drift");require(launcher_value(launcher,"Classification")==result,"launcher result differs from manifest");require(launcher_value(launcher,"Machine ID SHA-256",first=True)==plan["machine_uuid"]["sha256"],"launcher machine-id digest differs from plan")
    launcher_digest={"kind":"launcher_log","label":launcher.name,"sha256":sha256_file(launcher),"bytes":launcher.stat().st_size};require(launcher_digest["bytes"]>0,"launcher log empty")
    c={"schema":1,"classification":"P4_03_REFERENCE_CAPTURE_READY","project_version":EXPECTED_VERSION,"part":"Part 04","objective":"P4.03","runtime_observation":True,"divergence_promoted":False,"session_fingerprint":plan["session_fingerprint"],"platform_integration_fingerprint":plan["p3_06"]["platform_integration_fingerprint"],"preflight":{"sha256":sha256_file(pp),"preflight_fingerprint":pre["preflight_fingerprint"]},"reference_manifest":{"sha256":sha256_file(rp),"run_id":ref["run"]["id"],"started_utc":ref["run"]["started_utc"],"ended_utc":ref["run"]["ended_utc"],"result":result},"machine":{"type":"vmapple","accelerator":"hvf","cpu_model":"host"},"guest_inputs":copy.deepcopy(ref["guest_inputs"]),"trace":copy.deepcopy(ref["trace"]),"artifacts":copy.deepcopy(ref["artifacts"])+[launcher_digest],"sanitization":{"raw_local_paths_stored":False,"raw_uuid_stored":False,"guest_input_contents_stored":False},"runtime_authority":{"manifest":"P1.09","promotion":"P1.10"},"next_objective":"P4.04"};c["capture_fingerprint"]=sha256_bytes(canonical({k:v for k,v in c.items() if k!="classification"}));return c
def expect_policy_failure(p,mut,label):
    b=copy.deepcopy(p);mut(b)
    try:validate_policy(b)
    except ReferenceCaptureError:print(f"self-check reject: PASS: {label}");return
    raise ReferenceCaptureError(f"self-check mutation accepted: {label}")
def self_check(p):validate_policy(p);expect_policy_failure(p,lambda d:d["reference_contract"].__setitem__("accelerator","tcg"),"reference accelerator drift");expect_policy_failure(p,lambda d:d["required_trace_events"].pop(),"trace weakening");expect_policy_failure(p,lambda d:d.__setitem__("next_objective","P4.05"),"objective skip");print("P4.03 self-check: PASS")
def write_result(path,data):
    raw=canonical(data)
    if path:o=Path(path);o.parent.mkdir(parents=True,exist_ok=True);o.write_bytes(raw)
    sys.stdout.buffer.write(raw)
def main()->int:
    ap=argparse.ArgumentParser();ap.add_argument("--policy",default=str(DEFAULT_POLICY));sub=ap.add_subparsers(dest="command",required=True);sub.add_parser("validate-policy");sub.add_parser("self-check");pre=sub.add_parser("preflight")
    for x in ("session-plan","p3-06-manifest","qemu-bin","machine-uuid","firmware","auxiliary-storage","disk","machine-identity"):pre.add_argument("--"+x,required=True)
    pre.add_argument("--hardware-model");pre.add_argument("--output");fin=sub.add_parser("finalize");fin.add_argument("--session-plan",required=True);fin.add_argument("--reference-manifest",required=True);fin.add_argument("--launcher-log",required=True);fin.add_argument("--preflight",required=True);fin.add_argument("--output");a=ap.parse_args()
    try:
        p=load_json(Path(a.policy));validate_policy(p);validate_locked_artifacts(p)
        if a.command=="validate-policy":print("P4.03 reference capture policy: PASS")
        elif a.command=="self-check":self_check(p)
        elif a.command=="preflight":write_result(a.output,build_preflight(a,p))
        else:write_result(a.output,finalize_capture(a,p))
        return 0
    except (OSError,json.JSONDecodeError,ReferenceCaptureError,IntegrityError) as exc:print(f"P4.03 capture failure: {exc}",file=sys.stderr);return 1
if __name__=="__main__":raise SystemExit(main())

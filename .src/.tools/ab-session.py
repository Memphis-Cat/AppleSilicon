#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parents[2]
DEFAULT_POLICY=ROOT/".src/.configs/p4.04-ab-session-policy.json"
P1_POLICY=ROOT/".src/.configs/p1.09-manifest-policy.json"
P1_TOOL=ROOT/".src/.tools/reference-manifest.py"
EXPECTED_VERSION="4.3.0.0.0.0"
EXPECTED_INFERNO="cc4302a99167abec69b714cfd00c38caece7e7de"
SHA256_RE=re.compile(r"^[0-9a-f]{64}$")

class ABError(RuntimeError): pass
def require(v:bool,m:str)->None:
    if not v:raise ABError(m)
def load_json(p:Path)->dict[str,Any]:
    try:v=json.loads(p.read_text(encoding="utf-8"))
    except (OSError,json.JSONDecodeError) as exc:raise ABError(f"could not read JSON {p}: {exc}") from exc
    require(isinstance(v,dict),f"top-level JSON must be object: {p}");return v
def canonical(d:Any)->bytes:return (json.dumps(d,sort_keys=True,separators=(",",":"),ensure_ascii=False)+"\n").encode()
def sha256_bytes(b:bytes)->str:return hashlib.sha256(b).hexdigest()
def sha256_file(p:Path)->str:
    h=hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda:f.read(1024*1024),b""):h.update(c)
    return h.hexdigest()
def git_blob(p:Path)->str:
    d=p.read_bytes();return hashlib.sha1(b"blob "+str(len(d)).encode()+b"\0"+d).hexdigest()
def get_path(d:dict[str,Any],path:str)->Any:
    v:Any=d
    for part in path.split("."):require(isinstance(v,dict) and part in v,f"missing required field: {path}");v=v[part]
    return v
def verify_fingerprint(d:dict[str,Any],field:str,*,exclude=("classification",))->str:
    o=d.get(field);require(isinstance(o,str) and SHA256_RE.fullmatch(o) is not None,f"{field} invalid");b=dict(d);b.pop(field,None)
    for k in exclude:b.pop(k,None)
    require(o==sha256_bytes(canonical(b)),f"{field} does not reproduce");return o

def validate_policy(p:dict[str,Any])->None:
    require(p.get("schema")==1 and p.get("project_version")==EXPECTED_VERSION,"P4.04 schema/version mismatch")
    require(p.get("part")=="Part 04" and p.get("objective")=="P4.04" and p.get("title")=="Comparable A/B Session Assembly","P4.04 identity drift")
    require(p.get("source_lock",{}).get("inferno_revision")==EXPECTED_INFERNO,"P4.04 Inferno lock drift")
    roles=p.get("roles",{})
    require(roles.get("reference")=={"capture_classification":"P4_03_REFERENCE_CAPTURE_READY","plan_role":"reference","manifest_role":"reference","machine":"vmapple","accelerator":"hvf","cpu":"host"},"P4.04 reference role drift")
    require(roles.get("probe")=={"capture_classification":"P4_02_PROBE_CAPTURE_READY","plan_role":"probe","manifest_role":"probe","machine":"vmapple","accelerator":"tcg","cpu":"apple-gxf"},"P4.04 probe role drift")
    require(p.get("runtime_parameters")=={"ram_mib":4096,"smp":4},"P4.04 runtime geometry drift")
    equal=p.get("plan_pair_equal_paths",[])
    for path in ("p3_06.sha256","p3_06.platform_integration_fingerprint","machine_uuid.sha256","guest_inputs","trace_contract","locked_project_artifacts","qemu.version"):require(path in equal,f"P4.04 pair equality missing: {path}")
    require(p.get("expected_role_differences")==["role","host","integrated_machine.accelerator","integrated_machine.cpu","qemu.sha256","qemu.bytes","qemu.capabilities.accelerator","qemu.capabilities.cpu","session_fingerprint"],"P4.04 expected differences drift")
    for k,v in p.get("requirements",{}).items():require(v is True,f"P4.04 requirement disabled: {k}")
    require(p.get("next_objective")=="P4.05","P4.04 next objective drift")
def validate_locked_artifacts(p:dict[str,Any])->None:
    seen=set()
    for item in p.get("locked_project_artifacts",[]):
        rel=item.get("path");require(isinstance(rel,str) and rel and rel not in seen,f"invalid/duplicate locked artifact: {rel}");seen.add(rel);path=ROOT/rel;require(path.is_file(),f"locked artifact missing: {rel}");require(git_blob(path)==item.get("git_blob_sha"),f"locked artifact drift: {rel}")
def validate_plan(plan:dict[str,Any],role:str,p:dict[str,Any])->None:
    spec=p["roles"][role];require(plan.get("schema")==1 and plan.get("classification")=="P4_01_SESSION_PLAN_READY",f"{role} P4.01 plan not ready");require(plan.get("project_version")=="4.0.0.0.0.0" and plan.get("part")=="Part 04" and plan.get("objective")=="P4.01",f"{role} P4.01 plan identity drift");require(plan.get("role")==spec["plan_role"],f"{role} plan role drift");require(plan.get("guest_execution") is False and plan.get("runtime_evidence") is False,f"{role} plan claims runtime")
    require(plan.get("integrated_machine")=={"machine":spec["machine"],"accelerator":spec["accelerator"],"cpu":spec["cpu"]},f"{role} integrated machine drift");verify_fingerprint(plan,"session_fingerprint")
    p3=plan.get("p3_06",{});require(SHA256_RE.fullmatch(str(p3.get("sha256",""))) is not None and SHA256_RE.fullmatch(str(p3.get("platform_integration_fingerprint",""))) is not None,f"{role} P3 provenance invalid")
    mid=plan.get("machine_uuid",{});require(SHA256_RE.fullmatch(str(mid.get("sha256",""))) is not None and mid.get("encoding")=="uint64_decimal" and mid.get("semantic")=="vmapple_sdom_ecid" and mid.get("raw_value_stored") is False,f"{role} machine-id metadata invalid")
    q=plan.get("qemu",{});require(SHA256_RE.fullmatch(str(q.get("sha256",""))) is not None and isinstance(q.get("bytes"),int) and q["bytes"]>0 and isinstance(q.get("version"),str) and q["version"],f"{role} QEMU provenance invalid")
    for name in ("firmware","auxiliary_storage","disk","machine_identity"):
        item=plan.get("guest_inputs",{}).get(name);require(isinstance(item,dict) and SHA256_RE.fullmatch(str(item.get("sha256",""))) is not None and isinstance(item.get("bytes"),int) and item["bytes"]>0,f"{role} guest input invalid: {name}")
def verify_capture_fingerprint(c:dict[str,Any],role:str)->None:
    o=c.get("capture_fingerprint");require(isinstance(o,str) and SHA256_RE.fullmatch(o) is not None,f"{role} capture fingerprint invalid");payload={k:v for k,v in c.items() if k not in ("classification","capture_fingerprint")};require(o==sha256_bytes(canonical(payload)),f"{role} capture fingerprint does not reproduce")
def validate_capture(c:dict[str,Any],plan:dict[str,Any],manifest:dict[str,Any],manifest_path:Path,role:str,p:dict[str,Any])->None:
    spec=p["roles"][role];require(c.get("schema")==1 and c.get("classification")==spec["capture_classification"],f"{role} capture not ready");require(c.get("runtime_observation") is True and c.get("divergence_promoted") is False,f"{role} capture state invalid");verify_capture_fingerprint(c,role);require(c.get("session_fingerprint")==plan["session_fingerprint"],f"{role} capture/session mismatch");require(c.get("platform_integration_fingerprint")==plan["p3_06"]["platform_integration_fingerprint"],f"{role} capture/platform mismatch");require(c.get("guest_inputs")==plan["guest_inputs"],f"{role} capture/plan inputs differ");require(c.get("trace")=={"events":plan["trace_contract"]["events"],"debug_items":plan["trace_contract"]["debug_items"]},f"{role} capture trace contract differs")
    pre=c.get("preflight",{});require(SHA256_RE.fullmatch(str(pre.get("sha256",""))) is not None and SHA256_RE.fullmatch(str(pre.get("preflight_fingerprint",""))) is not None,f"{role} preflight binding invalid")
    require(c.get("machine")=={"type":"vmapple","accelerator":spec["accelerator"],"cpu_model":spec["cpu"]},f"{role} capture machine drift");key="reference_manifest" if role=="reference" else "probe_manifest";bind=c.get(key,{});require(bind.get("sha256")==sha256_file(manifest_path),f"{role} capture does not bind supplied manifest");require(bind.get("run_id")==manifest.get("run",{}).get("id") and bind.get("result")==manifest.get("run",{}).get("result"),f"{role} capture/manifest run binding mismatch")
    require(manifest.get("role")==spec["manifest_role"] and manifest.get("guest_inputs")==plan["guest_inputs"] and manifest.get("trace")==c["trace"],f"{role} P1.09 manifest differs from plan/capture");m=manifest.get("machine",{});require(m=={"type":"vmapple","accelerator":spec["accelerator"],"cpu_model":spec["cpu"],"ram_mib":p["runtime_parameters"]["ram_mib"],"smp":p["runtime_parameters"]["smp"]},f"{role} P1.09 machine geometry drift");require(manifest.get("source",{}).get("revision")==EXPECTED_INFERNO,f"{role} P1.09 Inferno drift")
def validate_plan_pair(r:dict[str,Any],q:dict[str,Any],p:dict[str,Any])->None:
    mismatch=[]
    for path in p["plan_pair_equal_paths"]:
        rv,pv=get_path(r,path),get_path(q,path)
        if rv!=pv:mismatch.append(path)
    require(not mismatch,f"P4.01 plan pair not comparable: {mismatch}");require(r["session_fingerprint"]!=q["session_fingerprint"],"reference/probe session fingerprints unexpectedly identical")
def run_p1_compare(rp:Path,pp:Path)->dict[str,Any]:
    require(P1_TOOL.is_file() and P1_POLICY.is_file(),"P1.09 tool/policy missing")
    with tempfile.TemporaryDirectory(prefix="applesilicon-p4.04-") as td:
        out=Path(td)/"pair.json";proc=subprocess.run([sys.executable,str(P1_TOOL),"compare",str(rp),str(pp),"--policy",str(P1_POLICY),"--report-json",str(out)],text=True,capture_output=True,timeout=30);require(proc.returncode==0,f"P1.09 rejected A/B pair: {((proc.stdout or '')+(proc.stderr or '')).strip()}");d=load_json(out)
    require(d.get("comparable") is True and d.get("contract_mismatches")==[],"P1.09 pair not comparable");return d
def assemble(a:argparse.Namespace,p:dict[str,Any])->dict[str,Any]:
    validate_policy(p);validate_locked_artifacts(p);rpp=Path(a.reference_plan);qpp=Path(a.probe_plan);rcp=Path(a.reference_capture);qcp=Path(a.probe_capture);rmp=Path(a.reference_manifest);qmp=Path(a.probe_manifest)
    for path in (rpp,qpp,rcp,qcp,rmp,qmp):require(path.is_file(),f"assembly input missing: {path}")
    rplan,qplan,rcap,qcap,rm,qm=[load_json(x) for x in (rpp,qpp,rcp,qcp,rmp,qmp)];validate_plan(rplan,"reference",p);validate_plan(qplan,"probe",p);validate_plan_pair(rplan,qplan,p);validate_capture(rcap,rplan,rm,rmp,"reference",p);validate_capture(qcap,qplan,qm,qmp,"probe",p);report=run_p1_compare(rmp,qmp)
    shared={"source_revision":EXPECTED_INFERNO,"machine":"vmapple","ram_mib":4096,"smp":4,"platform_integration_fingerprint":rplan["p3_06"]["platform_integration_fingerprint"],"p3_06_manifest_sha256":rplan["p3_06"]["sha256"],"machine_uuid_sha256":rplan["machine_uuid"]["sha256"],"machine_id_encoding":"uint64_decimal","guest_inputs":copy.deepcopy(rplan["guest_inputs"]),"trace_contract":copy.deepcopy(rplan["trace_contract"]),"qemu_version":rplan["qemu"]["version"]}
    def role_block(plan,cap,manifest,path_plan,path_cap,path_manifest):return {"session_plan_sha256":sha256_file(path_plan),"session_fingerprint":plan["session_fingerprint"],"capture_sha256":sha256_file(path_cap),"capture_fingerprint":cap["capture_fingerprint"],"manifest_sha256":sha256_file(path_manifest),"run_id":manifest["run"]["id"],"result":manifest["run"]["result"],"host":copy.deepcopy(plan["host"]),"qemu":{k:plan["qemu"][k] for k in ("sha256","bytes","version")},"machine":copy.deepcopy(cap["machine"])}
    b={"schema":1,"classification":"P4_04_AB_SESSION_READY","project_version":EXPECTED_VERSION,"part":"Part 04","objective":"P4.04","runtime_observation":True,"divergence_promoted":False,"shared_contract":shared,"reference":role_block(rplan,rcap,rm,rpp,rcp,rmp),"probe":role_block(qplan,qcap,qm,qpp,qcp,qmp),"p1_09_pairing":{"comparable":True,"reference_run_id":report["reference_run_id"],"probe_run_id":report["probe_run_id"],"contract_mismatches":[],"expected_differences":copy.deepcopy(report["expected_differences"])},"expected_role_differences":list(p["expected_role_differences"]),"runtime_authority":{"pair_comparability":"P1.09","trace_comparison":"P1.08","promotion":"P1.10"},"sanitization":{"raw_local_paths_stored":False,"raw_uuid_stored":False,"guest_input_contents_stored":False},"next_objective":"P4.05"};b["ab_fingerprint"]=sha256_bytes(canonical({k:v for k,v in b.items() if k!="classification"}));return b
def expect_policy_failure(p,mut,label):
    b=copy.deepcopy(p);mut(b)
    try:validate_policy(b)
    except ABError:print(f"self-check reject: PASS: {label}");return
    raise ABError(f"self-check mutation accepted: {label}")
def self_check(p):validate_policy(p);expect_policy_failure(p,lambda d:d["runtime_parameters"].__setitem__("smp",8),"SMP drift");expect_policy_failure(p,lambda d:d["roles"]["reference"].__setitem__("accelerator","tcg"),"reference accelerator drift");expect_policy_failure(p,lambda d:d["plan_pair_equal_paths"].remove("machine_uuid.sha256"),"machine-id equality removal");expect_policy_failure(p,lambda d:d.__setitem__("next_objective","P4.06"),"objective skip");print("P4.04 self-check: PASS")
def write_result(path,data):
    raw=canonical(data)
    if path:o=Path(path);o.parent.mkdir(parents=True,exist_ok=True);o.write_bytes(raw)
    sys.stdout.buffer.write(raw)
def main()->int:
    ap=argparse.ArgumentParser(description="AppleSilicon P4.04 comparable A/B session assembler");ap.add_argument("--policy",default=str(DEFAULT_POLICY));sub=ap.add_subparsers(dest="command",required=True);sub.add_parser("validate-policy");sub.add_parser("self-check");x=sub.add_parser("assemble")
    for name in ("reference-plan","probe-plan","reference-capture","probe-capture","reference-manifest","probe-manifest"):x.add_argument("--"+name,required=True)
    x.add_argument("--output");a=ap.parse_args()
    try:
        p=load_json(Path(a.policy));validate_policy(p);validate_locked_artifacts(p)
        if a.command=="validate-policy":print("P4.04 policy: PASS")
        elif a.command=="self-check":self_check(p)
        else:write_result(a.output,assemble(a,p))
        return 0
    except (ABError,OSError,subprocess.TimeoutExpired) as exc:print(f"error: {exc}",file=sys.stderr);return 2
if __name__=="__main__":raise SystemExit(main())

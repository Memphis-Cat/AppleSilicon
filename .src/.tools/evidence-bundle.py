#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

VERSION="1.0.0.0.0.0"
ROOT_DIR=Path(__file__).resolve().parents[2]
DEFAULT_POLICY=ROOT_DIR/".src/.configs/p1.10-promotion-policy.json"
DEFAULT_MANIFEST_POLICY=ROOT_DIR/".src/.configs/p1.09-manifest-policy.json"
DEFAULT_TRACE_CONFIG=ROOT_DIR/".src/.configs/p1.08-compare.json"
MANIFEST_TOOL=ROOT_DIR/".src/.tools/reference-manifest.py"
TRACE_TOOL=ROOT_DIR/".src/.tools/compare-boot-traces.py"
INPUT_ERROR=2
GATE_REJECTED=10

class BundleError(Exception): pass
def load_module(name:str,path:Path):
    spec=importlib.util.spec_from_file_location(name,path)
    if spec is None or spec.loader is None:raise BundleError(f"could not load module: {path}")
    module=importlib.util.module_from_spec(spec);sys.modules[name]=module;spec.loader.exec_module(module);return module
def load_json(path:Path)->dict[str,Any]:
    try:v=json.loads(path.read_text(encoding="utf-8"))
    except (OSError,json.JSONDecodeError) as exc:raise BundleError(f"could not read JSON {path}: {exc}") from exc
    if not isinstance(v,dict):raise BundleError(f"top-level JSON must be object: {path}")
    return v
def save_json(path:Path,value:dict[str,Any])->None:path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,indent=2,sort_keys=True)+"\n",encoding="utf-8")
def canonical_json(v:Any)->bytes:return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()
def digest_object(v:Any)->str:return hashlib.sha256(canonical_json(v)).hexdigest()
def is_sha256(value:Any)->bool:return isinstance(value,str) and len(value)==64 and all(ch in "0123456789abcdef" for ch in value)
def sha256_file(path:Path)->dict[str,Any]:
    h=hashlib.sha256();size=0
    try:
        with path.open("rb") as f:
            while True:
                chunk=f.read(1024*1024)
                if not chunk:break
                h.update(chunk);size+=len(chunk)
    except OSError as exc:raise BundleError(f"could not hash {path}: {exc}") from exc
    return {"sha256":h.hexdigest(),"bytes":size}
def load_policy(path:Path)->dict[str,Any]:
    p=load_json(path)
    if p.get("schema")!=1 or p.get("project_version")!=VERSION:raise BundleError("P1.10 policy schema/version mismatch")
    if not isinstance(p.get("minimum_reproductions"),int) or p["minimum_reproductions"]<2:raise BundleError("minimum_reproductions must be at least 2")
    if not isinstance(p.get("minimum_canonical_events_per_trace"),int) or p["minimum_canonical_events_per_trace"]<1:raise BundleError("minimum_canonical_events_per_trace must be at least 1")
    for key in ("require_structured_trace_events","require_unique_run_pairs","require_unique_reference_runs","require_unique_probe_runs","require_unique_reference_manifests","require_unique_probe_manifests","require_candidate_fingerprint","require_same_contract_fingerprint","require_same_divergence_signature"):
        if p.get(key) is not True:raise BundleError(f"P1.10 requirement disabled: {key}")
    if p.get("auto_commit_promotion") is not False:raise BundleError("P1.10 auto-commit must remain disabled")
    req=p.get("requirements",{})
    for key in ("empty_canonical_stream_is_insufficient_evidence","unstructured_trace_fallback_is_not_promotable_runtime_evidence","candidate_fingerprint_must_reproduce","candidate_id_must_reproduce","independent_reference_runs_required","independent_probe_runs_required","independent_reference_manifests_required","independent_probe_manifests_required"):
        if req.get(key) is not True:raise BundleError(f"P1.10 policy requirement disabled: {key}")
    return p
def result_is_runtime(role:str,result:str,p:dict[str,Any])->bool:
    if any(x.lower() in result.lower() for x in p["blocked_result_fragments"]):return False
    prefixes=p["reference_result_prefixes"] if role=="reference" else p["probe_result_prefixes"]
    return any(result.startswith(x) for x in prefixes)
def verify_trace_artifact(manifest:dict[str,Any],trace_path:Path,p:dict[str,Any])->dict[str,Any]:
    observed=sha256_file(trace_path);allowed=set(p["allowed_trace_artifact_kinds"]);matches=[a for a in manifest.get("artifacts",[]) if a.get("kind") in allowed and a.get("sha256")==observed["sha256"] and a.get("bytes")==observed["bytes"]]
    if not matches:raise BundleError(f"trace evidence {trace_path.name} does not match an allowed manifest artifact")
    return {"label":trace_path.name,"sha256":observed["sha256"],"bytes":observed["bytes"],"manifest_artifact_kinds":sorted({x["kind"] for x in matches})}
def contract_fingerprint(reference:dict[str,Any],policy:dict[str,Any],module)->str:return digest_object({path:module.get_path(reference,path) for path in policy["pair_equal_paths"]})
def trace_quality(stream,p:dict[str,Any],role:str)->dict[str,Any]:
    count=len(stream.records);structured=sum(1 for r in stream.records if r.structured)
    if count<p["minimum_canonical_events_per_trace"]:raise BundleError(f"{role} trace is insufficient: {count} canonical events; minimum is {p['minimum_canonical_events_per_trace']}")
    if p["require_structured_trace_events"] and structured!=count:
        bad=[r.source_line for r in stream.records if not r.structured][:5]
        raise BundleError(f"{role} trace contains unstructured fallback records at source lines {bad}")
    return {"event_count":count,"structured_event_count":structured,"all_events_structured":structured==count,"minimum_required":p["minimum_canonical_events_per_trace"]}
def mismatch_signature(comparison:dict[str,Any])->tuple[str|None,dict[str,Any]|None]:
    if comparison["identical"]:return None,None
    m=comparison["first_mismatch"];ref=m.get("reference");probe=m.get("probe");resync=m.get("resynchronization");material={"classification":m["classification"],"reference":ref.get("canonical") if ref else None,"probe":probe.get("canonical") if probe else None,"resynchronization_anchor":resync.get("anchor") if resync else None};return digest_object(material),material
def candidate_identity_material(c:dict[str,Any])->dict[str,Any]:return {"reference_run_id":c.get("reference_run_id"),"probe_run_id":c.get("probe_run_id"),"reference_manifest_sha256":c.get("reference_manifest_sha256"),"probe_manifest_sha256":c.get("probe_manifest_sha256"),"divergence_signature":c.get("divergence_signature")}
def seal_candidate(c:dict[str,Any])->dict[str,Any]:
    c.pop("candidate_fingerprint",None);c["candidate_id"]="p01-candidate-"+digest_object(candidate_identity_material(c))[:20];c["candidate_fingerprint"]=digest_object(c);return c
def verify_candidate_auth(c:dict[str,Any],p:dict[str,Any])->None:
    expected_id="p01-candidate-"+digest_object(candidate_identity_material(c))[:20]
    if c.get("candidate_id")!=expected_id:raise BundleError(f"candidate id does not reproduce: {c.get('candidate_id')}")
    for field in ("reference_manifest_sha256","probe_manifest_sha256","contract_fingerprint","divergence_signature"):
        if not is_sha256(c.get(field)):raise BundleError(f"candidate {c.get('candidate_id')} has invalid {field}")
    for role in ("reference_trace","probe_trace"):
        item=c.get(role,{})
        if not isinstance(item,dict) or not is_sha256(item.get("sha256")):raise BundleError(f"candidate {c.get('candidate_id')} has invalid {role} digest")
    if p["require_candidate_fingerprint"]:
        observed=c.get("candidate_fingerprint")
        if not is_sha256(observed):raise BundleError(f"candidate {c.get('candidate_id')} fingerprint invalid")
        basis=dict(c);basis.pop("candidate_fingerprint",None);expected=digest_object(basis)
        if observed!=expected:raise BundleError(f"candidate {c.get('candidate_id')} fingerprint does not reproduce")
def build_candidate(reference,probe,reference_trace,probe_trace,p,manifest_policy,trace_config,manifest_module,trace_module):
    pair=manifest_module.compare_manifests(reference,probe,manifest_policy)
    if not pair["comparable"]:raise BundleError("P1.09 pairing contract rejected A/B pair: "+", ".join(x["path"] for x in pair["contract_mismatches"]))
    ref_evidence=verify_trace_artifact(reference,reference_trace,p);probe_evidence=verify_trace_artifact(probe,probe_trace,p)
    ref_stream=trace_module.parse_file(reference_trace,trace_config);probe_stream=trace_module.parse_file(probe_trace,trace_config)
    ref_quality=trace_quality(ref_stream,p,"reference");probe_quality=trace_quality(probe_stream,p,"probe")
    comparison=trace_module.compare_streams(ref_stream,probe_stream,trace_config);signature,material=mismatch_signature(comparison)
    runtime=result_is_runtime("reference",reference["run"]["result"],p) and result_is_runtime("probe",probe["run"]["result"],p)
    status="no_divergence" if comparison["identical"] else "divergence_candidate";promotable=status=="divergence_candidate" and runtime
    candidate={"schema":1,"project_version":VERSION,"status":status,"promotion_eligible":promotable,"evidence_origin":"runtime" if runtime else "non-runtime","reference_run_id":reference["run"]["id"],"probe_run_id":probe["run"]["id"],"reference_result":reference["run"]["result"],"probe_result":probe["run"]["result"],"reference_manifest_sha256":digest_object(reference),"probe_manifest_sha256":digest_object(probe),"contract_fingerprint":contract_fingerprint(reference,manifest_policy,manifest_module),"reference_trace":ref_evidence,"probe_trace":probe_evidence,"trace_quality":{"reference":ref_quality,"probe":probe_quality},"comparison":{"identical":comparison["identical"],"reference_event_count":comparison["reference"]["event_count"],"probe_event_count":comparison["probe"]["event_count"],"first_mismatch":comparison["first_mismatch"]},"divergence_signature":signature,"signature_material":material,"gate":{"minimum_reproductions":p["minimum_reproductions"],"minimum_canonical_events_per_trace":p["minimum_canonical_events_per_trace"],"require_structured_trace_events":True,"auto_commit":False}}
    seal_candidate(candidate);return candidate,ref_stream,probe_stream,pair
def write_candidate_markdown(c:dict[str,Any],path:Path)->None:
    lines=["# P01-DIVERGENCE-CANDIDATE","",f"Candidate: `{c['candidate_id']}`",f"Candidate fingerprint: `{c['candidate_fingerprint']}`",f"Status: **{c['status']}**",f"Evidence origin: **{c['evidence_origin']}**",f"Promotion eligible: **{str(c['promotion_eligible']).lower()}**","",f"Reference run: `{c['reference_run_id']}`",f"Probe run: `{c['probe_run_id']}`",f"Contract fingerprint: `{c['contract_fingerprint']}`",f"Reference canonical events: **{c['trace_quality']['reference']['event_count']}**",f"Probe canonical events: **{c['trace_quality']['probe']['event_count']}**"]
    if c["status"]=="divergence_candidate":
        m=c["comparison"]["first_mismatch"];ref=m.get("reference");probe=m.get("probe");lines += [f"Divergence signature: `{c['divergence_signature']}`","",f"Classification: **`{m['classification']}`**","","## Reference event","","```text",ref.get("canonical") if ref else "<end-of-trace>","```","","## Probe event","","```text",probe.get("canonical") if probe else "<end-of-trace>","```"]
    else:lines += ["","No canonical trace divergence was found in this A/B pair."]
    lines += ["","This candidate is not `P01-DIVERGENCE-0001`. Promotion requires the P1.10 reproduction gate.",""];path.parent.mkdir(parents=True,exist_ok=True);path.write_text("\n".join(lines),encoding="utf-8")
def validate_candidate_quality(c:dict[str,Any],p:dict[str,Any])->None:
    q=c.get("trace_quality",{})
    for role in ("reference","probe"):
        item=q.get(role,{});count=item.get("event_count");require=isinstance(count,int) and count>=p["minimum_canonical_events_per_trace"]
        if not require:raise BundleError(f"candidate {c.get('candidate_id')} has insufficient {role} trace")
        if p["require_structured_trace_events"] and item.get("all_events_structured") is not True:raise BundleError(f"candidate {c.get('candidate_id')} contains unstructured {role} trace records")
def evaluate_promotion(candidates:list[dict[str,Any]],p:dict[str,Any],*,strict_runtime=True)->dict[str,Any]:
    if len(candidates)<p["minimum_reproductions"]:raise BundleError(f"promotion requires at least {p['minimum_reproductions']} reproduced candidate bundles")
    for c in candidates:
        if c.get("schema")!=1 or c.get("project_version")!=VERSION or c.get("status")!="divergence_candidate":raise BundleError("promotion candidate schema/version/status invalid")
        verify_candidate_auth(c,p);validate_candidate_quality(c,p)
        if strict_runtime and (c.get("evidence_origin")!="runtime" or c.get("promotion_eligible") is not True):raise BundleError(f"candidate {c.get('candidate_id')} is not eligible runtime evidence")
        if not c.get("divergence_signature"):raise BundleError("candidate has no divergence signature")
    pairs=[(c["reference_run_id"],c["probe_run_id"]) for c in candidates]
    refs=[c["reference_run_id"] for c in candidates];probes=[c["probe_run_id"] for c in candidates];ref_manifests=[c["reference_manifest_sha256"] for c in candidates];probe_manifests=[c["probe_manifest_sha256"] for c in candidates]
    if p["require_unique_run_pairs"] and len(pairs)!=len(set(pairs)):raise BundleError("promotion cannot reuse same reference/probe pair")
    if p["require_unique_reference_runs"] and len(refs)!=len(set(refs)):raise BundleError("promotion cannot reuse a reference runtime run")
    if p["require_unique_probe_runs"] and len(probes)!=len(set(probes)):raise BundleError("promotion cannot reuse a probe runtime run")
    if p["require_unique_reference_manifests"] and len(ref_manifests)!=len(set(ref_manifests)):raise BundleError("promotion cannot reuse a reference runtime manifest")
    if p["require_unique_probe_manifests"] and len(probe_manifests)!=len(set(probe_manifests)):raise BundleError("promotion cannot reuse a probe runtime manifest")
    sigs={c["divergence_signature"] for c in candidates};contracts={c["contract_fingerprint"] for c in candidates}
    if p["require_same_divergence_signature"] and len(sigs)!=1:raise BundleError("candidate reproductions do not share divergence signature")
    if p["require_same_contract_fingerprint"] and len(contracts)!=1:raise BundleError("candidate reproductions do not share P1.09 contract fingerprint")
    first=candidates[0]
    return {"schema":1,"project_version":VERSION,"id":p["promotion_id"],"status":"promoted","reproduction_count":len(candidates),"divergence_signature":first["divergence_signature"],"contract_fingerprint":first["contract_fingerprint"],"classification":first["comparison"]["first_mismatch"]["classification"],"signature_material":first["signature_material"],"reproductions":[{"candidate_id":c["candidate_id"],"candidate_fingerprint":c["candidate_fingerprint"],"reference_run_id":c["reference_run_id"],"probe_run_id":c["probe_run_id"],"reference_manifest_sha256":c["reference_manifest_sha256"],"probe_manifest_sha256":c["probe_manifest_sha256"],"reference_trace_sha256":c["reference_trace"]["sha256"],"probe_trace_sha256":c["probe_trace"]["sha256"],"reference_event_count":c["trace_quality"]["reference"]["event_count"],"probe_event_count":c["trace_quality"]["probe"]["event_count"]} for c in candidates],"auto_committed":False}
def write_promotion_markdown(r:dict[str,Any],path:Path)->None:
    m=r["signature_material"];lines=[f"# {r['id']}","",f"Status: **{r['status']}**",f"Reproductions: **{r['reproduction_count']}**",f"Classification: **`{r['classification']}`**",f"Divergence signature: `{r['divergence_signature']}`",f"Contract fingerprint: `{r['contract_fingerprint']}`","","Stage: `earliest normalized VMApple trace divergence`","PC: `unknown from current MMIO trace contract`","","## Expected/reference behavior","","```text",m.get("reference") or "<end-of-trace>","```","","## Observed/probe behavior","","```text",m.get("probe") or "<end-of-trace>","```","","## Reproductions",""]
    for x in r["reproductions"]:lines.append(f"- `{x['candidate_id']}` — reference `{x['reference_run_id']}`, probe `{x['probe_run_id']}`")
    lines += ["","This record passed pairing, artifact-integrity, trace-sufficiency, runtime-origin, candidate-authentication, uniqueness, contract, and reproduction gates.","","It is intentionally not auto-committed.",""];path.parent.mkdir(parents=True,exist_ok=True);path.write_text("\n".join(lines),encoding="utf-8")
def run_candidate(a)->int:
    p=load_policy(a.policy);mm=load_module("applesilicon_p109_manifest",MANIFEST_TOOL);tm=load_module("applesilicon_p108_trace",TRACE_TOOL);mp=mm.load_policy(a.manifest_policy);tc=tm.load_config(a.trace_config);ref=mm.load_json(a.reference_manifest);probe=mm.load_json(a.probe_manifest);c,rs,ps,pair=build_candidate(ref,probe,a.reference_trace,a.probe_trace,p,mp,tc,mm,tm);a.output_dir.mkdir(parents=True,exist_ok=True);tm.write_normalized(rs,a.output_dir/"normalized-reference.log");tm.write_normalized(ps,a.output_dir/"normalized-probe.log");save_json(a.output_dir/"pair-report.json",pair);save_json(a.output_dir/"candidate.json",c);write_candidate_markdown(c,a.output_dir/"P01-divergence-candidate.md");print(f"candidate_id={c['candidate_id']}");print(f"candidate_fingerprint={c['candidate_fingerprint']}");print(f"status={c['status']}");print(f"evidence_origin={c['evidence_origin']}");print(f"promotion_eligible={str(c['promotion_eligible']).lower()}");print(f"reference_events={c['trace_quality']['reference']['event_count']}");print(f"probe_events={c['trace_quality']['probe']['event_count']}");return 0
def run_promote(a)->int:
    p=load_policy(a.policy);cs=[load_json(x) for x in a.candidate];r=evaluate_promotion(cs,p,strict_runtime=True);a.output_dir.mkdir(parents=True,exist_ok=True);save_json(a.output_dir/f"{r['id']}.json",r);write_promotion_markdown(r,a.output_dir/f"{r['id']}.md");print(f"promoted={r['id']}");print(f"reproduction_count={r['reproduction_count']}");print("auto_committed=false");return 0
def expect_promotion_rejected(candidates:list[dict[str,Any]],p:dict[str,Any],label:str)->None:
    try:evaluate_promotion(candidates,p,strict_runtime=True)
    except BundleError:print(f"self-check reject: PASS: {label}");return
    raise BundleError(f"self-check promotion mutation was accepted: {label}")
def run_self_check(a)->int:
    p=load_policy(a.policy);mm=load_module("applesilicon_p109_manifest_selfcheck",MANIFEST_TOOL);tm=load_module("applesilicon_p108_trace_selfcheck",TRACE_TOOL);mp=mm.load_policy(a.manifest_policy);tc=tm.load_config(a.trace_config);ref=copy.deepcopy(mm.load_json(ROOT_DIR/".src/.configs/p1.09-reference.example.json"));probe=copy.deepcopy(mm.load_json(ROOT_DIR/".src/.configs/p1.09-probe.example.json"));rt=ROOT_DIR/".src/.fixtures/.p1.08/reference.trace";dt=ROOT_DIR/".src/.fixtures/.p1.08/value-divergence.trace";et=ROOT_DIR/".src/.fixtures/.p1.08/equivalent.trace";ref["run"]["id"]="p1.10-self-reference";probe["run"]["id"]="p1.10-self-probe";ref["run"]["result"]=probe["run"]["result"]="synthetic-self-check";ref["artifacts"]=[{"kind":"serial_log","label":rt.name,**sha256_file(rt)}];probe["artifacts"]=[{"kind":"serial_log","label":dt.name,**sha256_file(dt)}];c,_,_,_=build_candidate(ref,probe,rt,dt,p,mp,tc,mm,tm)
    if c["status"]!="divergence_candidate" or c["promotion_eligible"]:raise BundleError("synthetic divergence self-check failed")
    verify_candidate_auth(c,p)
    ep=copy.deepcopy(probe);ep["artifacts"]=[{"kind":"serial_log","label":et.name,**sha256_file(et)}];eq,_,_,_=build_candidate(ref,ep,rt,et,p,mp,tc,mm,tm)
    if eq["status"]!="no_divergence":raise BundleError("equivalent trace self-check failed")
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        empty=Path(td)/"empty.trace";empty.write_text("",encoding="utf-8");badref=copy.deepcopy(ref);badprobe=copy.deepcopy(probe);badref["artifacts"]=[{"kind":"serial_log","label":empty.name,**sha256_file(empty)}];badprobe["artifacts"]=[{"kind":"serial_log","label":empty.name,**sha256_file(empty)}]
        try:build_candidate(badref,badprobe,empty,empty,p,mp,tc,mm,tm)
        except BundleError:pass
        else:raise BundleError("empty traces were incorrectly accepted as evidence")
    first=copy.deepcopy(c);second=copy.deepcopy(c);first["reference_run_id"],first["probe_run_id"]="ref-a","probe-a";second["reference_run_id"],second["probe_run_id"]="ref-b","probe-b";first["reference_manifest_sha256"],first["probe_manifest_sha256"]=digest_object({"reference":"a"}),digest_object({"probe":"a"});second["reference_manifest_sha256"],second["probe_manifest_sha256"]=digest_object({"reference":"b"}),digest_object({"probe":"b"})
    for x in (first,second):x["evidence_origin"]="runtime";x["promotion_eligible"]=True;seal_candidate(x)
    r=evaluate_promotion([first,second],p,strict_runtime=True)
    if r["id"]!=p["promotion_id"]:raise BundleError("positive promotion self-check failed")
    stale=copy.deepcopy(first);stale["reference_run_id"]="ref-edited";expect_promotion_rejected([stale,second],p,"stale candidate fingerprint")
    bad_id=copy.deepcopy(first);bad_id["candidate_id"]="p01-candidate-edited";bad_id.pop("candidate_fingerprint",None);bad_id["candidate_fingerprint"]=digest_object(bad_id);expect_promotion_rejected([bad_id,second],p,"candidate id mismatch")
    reused_ref=copy.deepcopy(second);reused_ref["reference_run_id"]=first["reference_run_id"];seal_candidate(reused_ref);expect_promotion_rejected([first,reused_ref],p,"reference run reuse")
    reused_probe=copy.deepcopy(second);reused_probe["probe_run_id"]=first["probe_run_id"];seal_candidate(reused_probe);expect_promotion_rejected([first,reused_probe],p,"probe run reuse")
    reused_ref_manifest=copy.deepcopy(second);reused_ref_manifest["reference_manifest_sha256"]=first["reference_manifest_sha256"];seal_candidate(reused_ref_manifest);expect_promotion_rejected([first,reused_ref_manifest],p,"reference manifest reuse")
    reused_probe_manifest=copy.deepcopy(second);reused_probe_manifest["probe_manifest_sha256"]=first["probe_manifest_sha256"];seal_candidate(reused_probe_manifest);expect_promotion_rejected([first,reused_probe_manifest],p,"probe manifest reuse")
    print("P1.10 self-check: PASS");print("checks=pairing,artifact-integrity,trace-sufficiency,structured-events,synthetic-block,candidate-authentication,independent-runs,independent-manifests,reproduction-count,signature-match");return 0
def build_parser():
    ap=argparse.ArgumentParser(description="AppleSilicon P1.10 evidence bundler and promotion gate");ap.add_argument("--version",action="version",version=f"AppleSilicon evidence bundle {VERSION}");sub=ap.add_subparsers(dest="command",required=True);c=sub.add_parser("candidate")
    for x in ("reference-manifest","probe-manifest","reference-trace","probe-trace","output-dir"):c.add_argument("--"+x,required=True,type=Path)
    c.add_argument("--policy",type=Path,default=DEFAULT_POLICY);c.add_argument("--manifest-policy",type=Path,default=DEFAULT_MANIFEST_POLICY);c.add_argument("--trace-config",type=Path,default=DEFAULT_TRACE_CONFIG);c.set_defaults(func=run_candidate);p=sub.add_parser("promote");p.add_argument("--candidate",required=True,action="append",type=Path);p.add_argument("--output-dir",required=True,type=Path);p.add_argument("--policy",type=Path,default=DEFAULT_POLICY);p.set_defaults(func=run_promote);s=sub.add_parser("self-check");s.add_argument("--policy",type=Path,default=DEFAULT_POLICY);s.add_argument("--manifest-policy",type=Path,default=DEFAULT_MANIFEST_POLICY);s.add_argument("--trace-config",type=Path,default=DEFAULT_TRACE_CONFIG);s.set_defaults(func=run_self_check);return ap
def main()->int:
    a=build_parser().parse_args()
    try:return a.func(a)
    except BundleError as exc:print(f"error: {exc}",file=sys.stderr);return GATE_REJECTED
    except (OSError,ValueError,KeyError,TypeError) as exc:print(f"error: {exc}",file=sys.stderr);return INPUT_ERROR
if __name__=="__main__":raise SystemExit(main())

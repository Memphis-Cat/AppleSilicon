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

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_POLICY = ROOT / ".src/.configs/p4.04-ab-session-policy.json"
P1_POLICY = ROOT / ".src/.configs/p1.09-manifest-policy.json"
P1_TOOL = ROOT / ".src/.tools/reference-manifest.py"
EXPECTED_VERSION = "4.3.0.0.0.0"
EXPECTED_INFERNO = "cc4302a99167abec69b714cfd00c38caece7e7de"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class ABError(RuntimeError):
    pass


def require(value: bool, message: str) -> None:
    if not value:
        raise ABError(message)


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ABError(f"could not read JSON {path}: {exc}") from exc
    require(isinstance(value, dict), f"top-level JSON must be an object: {path}")
    return value


def canonical(data: dict[str, Any]) -> bytes:
    return (json.dumps(data, sort_keys=True, separators=(",", ":")) + "\n").encode()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def git_blob(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def get_path(data: dict[str, Any], dotted: str) -> Any:
    value: Any = data
    for part in dotted.split("."):
        require(isinstance(value, dict) and part in value, f"missing required field: {dotted}")
        value = value[part]
    return value


def validate_policy(policy: dict[str, Any]) -> None:
    require(policy.get("schema") == 1, "P4.04 schema mismatch")
    require(policy.get("project_version") == EXPECTED_VERSION, "P4.04 version mismatch")
    require(policy.get("part") == "Part 04", "P4.04 part mismatch")
    require(policy.get("objective") == "P4.04", "P4.04 objective mismatch")
    require(policy.get("title") == "Comparable A/B Session Assembly", "P4.04 title mismatch")
    require(policy.get("source_lock", {}).get("inferno_revision") == EXPECTED_INFERNO,
            "P4.04 Inferno source lock drift")
    roles = policy.get("roles", {})
    require(roles.get("reference") == {
        "capture_classification": "P4_03_REFERENCE_CAPTURE_READY",
        "plan_role": "reference", "manifest_role": "reference",
        "machine": "vmapple", "accelerator": "hvf", "cpu": "host",
    }, "P4.04 reference role drift")
    require(roles.get("probe") == {
        "capture_classification": "P4_02_PROBE_CAPTURE_READY",
        "plan_role": "probe", "manifest_role": "probe",
        "machine": "vmapple", "accelerator": "tcg", "cpu": "apple-gxf",
    }, "P4.04 probe role drift")
    require(policy.get("runtime_parameters") == {"ram_mib": 4096, "smp": 4},
            "P4.04 runtime geometry drift")
    pair_paths = policy.get("plan_pair_equal_paths", [])
    for required_path in (
        "p3_06.sha256", "p3_06.platform_integration_fingerprint", "machine_uuid.sha256",
        "guest_inputs", "trace_contract", "locked_project_artifacts", "qemu.version",
    ):
        require(required_path in pair_paths, f"P4.04 pair equality missing: {required_path}")
    require(policy.get("expected_role_differences") == [
        "role", "host", "integrated_machine.accelerator", "integrated_machine.cpu",
        "qemu.sha256", "qemu.bytes", "qemu.capabilities.accelerator",
        "qemu.capabilities.cpu", "session_fingerprint",
    ], "P4.04 expected role difference set drift")
    for key, value in policy.get("requirements", {}).items():
        require(value is True, f"P4.04 requirement disabled: {key}")
    require(policy.get("next_objective") == "P4.05", "P4.04 next objective must be P4.05")


def validate_locked_artifacts(policy: dict[str, Any]) -> None:
    seen: set[str] = set()
    for item in policy.get("locked_project_artifacts", []):
        rel = item.get("path")
        require(isinstance(rel, str) and rel and rel not in seen, f"invalid/duplicate locked artifact: {rel}")
        seen.add(rel)
        path = ROOT / rel
        require(path.is_file(), f"locked artifact missing: {rel}")
        observed = git_blob(path)
        require(observed == item.get("git_blob_sha"), f"locked artifact drift: {rel}: {observed}")


def validate_plan(plan: dict[str, Any], role: str, policy: dict[str, Any]) -> None:
    spec = policy["roles"][role]
    require(plan.get("schema") == 1, f"{role} P4.01 plan schema mismatch")
    require(plan.get("classification") == "P4_01_SESSION_PLAN_READY", f"{role} P4.01 plan is not ready")
    require(plan.get("project_version") == "4.0.0.0.0.0", f"{role} P4.01 plan version mismatch")
    require(plan.get("role") == spec["plan_role"], f"{role} P4.01 plan role mismatch")
    require(plan.get("guest_execution") is False and plan.get("runtime_evidence") is False,
            f"{role} P4.01 plan must remain pre-execution metadata")
    require(plan.get("integrated_machine") == {
        "machine": spec["machine"], "accelerator": spec["accelerator"], "cpu": spec["cpu"],
    }, f"{role} P4.01 machine contract drift")
    require(SHA256_RE.fullmatch(str(plan.get("session_fingerprint", ""))) is not None,
            f"{role} session fingerprint invalid")
    p3 = plan.get("p3_06", {})
    require(SHA256_RE.fullmatch(str(p3.get("sha256", ""))) is not None,
            f"{role} P3.06 manifest digest invalid")
    require(SHA256_RE.fullmatch(str(p3.get("platform_integration_fingerprint", ""))) is not None,
            f"{role} P3.06 platform fingerprint invalid")
    machine_uuid = plan.get("machine_uuid", {})
    require(SHA256_RE.fullmatch(str(machine_uuid.get("sha256", ""))) is not None,
            f"{role} machine UUID digest invalid")
    require(machine_uuid.get("raw_value_stored") is False, f"{role} plan stored raw UUID")
    qemu = plan.get("qemu", {})
    require(SHA256_RE.fullmatch(str(qemu.get("sha256", ""))) is not None,
            f"{role} QEMU digest invalid")
    require(isinstance(qemu.get("bytes"), int) and qemu["bytes"] > 0, f"{role} QEMU size invalid")
    require(isinstance(qemu.get("version"), str) and qemu["version"], f"{role} QEMU version missing")
    inputs = plan.get("guest_inputs", {})
    for name in ("firmware", "auxiliary_storage", "disk", "machine_identity"):
        item = inputs.get(name)
        require(isinstance(item, dict), f"{role} missing guest input {name}")
        require(SHA256_RE.fullmatch(str(item.get("sha256", ""))) is not None,
                f"{role} guest input digest invalid: {name}")
        require(isinstance(item.get("bytes"), int) and item["bytes"] > 0,
                f"{role} guest input size invalid: {name}")


def verify_capture_fingerprint(capture: dict[str, Any], role: str) -> None:
    observed = capture.get("capture_fingerprint")
    require(isinstance(observed, str) and SHA256_RE.fullmatch(observed) is not None,
            f"{role} capture fingerprint invalid")
    payload = {k: v for k, v in capture.items() if k not in ("classification", "capture_fingerprint")}
    require(observed == sha256_bytes(canonical(payload)), f"{role} capture fingerprint does not reproduce")


def validate_capture(capture: dict[str, Any], plan: dict[str, Any], manifest: dict[str, Any],
                     manifest_path: Path, role: str, policy: dict[str, Any]) -> None:
    spec = policy["roles"][role]
    require(capture.get("schema") == 1, f"{role} capture schema mismatch")
    require(capture.get("classification") == spec["capture_classification"], f"{role} capture is not ready")
    require(capture.get("runtime_observation") is True, f"{role} capture is not runtime evidence provenance")
    require(capture.get("divergence_promoted") is False, f"{role} capture arrived with a promoted divergence")
    verify_capture_fingerprint(capture, role)
    require(capture.get("session_fingerprint") == plan["session_fingerprint"],
            f"{role} capture/session fingerprint mismatch")
    require(capture.get("platform_integration_fingerprint") == plan["p3_06"]["platform_integration_fingerprint"],
            f"{role} capture/platform fingerprint mismatch")
    require(capture.get("guest_inputs") == plan.get("guest_inputs"), f"{role} capture/plan guest inputs differ")
    require(capture.get("trace") == {
        "events": plan["trace_contract"]["events"],
        "debug_items": plan["trace_contract"]["debug_items"],
    }, f"{role} capture/plan trace contract differs")
    require(capture.get("machine") == {
        "type": spec["machine"], "accelerator": spec["accelerator"], "cpu_model": spec["cpu"],
    }, f"{role} capture machine contract drift")
    manifest_key = "reference_manifest" if role == "reference" else "probe_manifest"
    binding = capture.get(manifest_key, {})
    require(binding.get("sha256") == sha256_file(manifest_path),
            f"{role} capture does not bind the supplied P1.09 manifest")
    require(binding.get("run_id") == manifest.get("run", {}).get("id"), f"{role} capture/manifest run id mismatch")
    require(binding.get("result") == manifest.get("run", {}).get("result"), f"{role} capture/manifest result mismatch")
    require(manifest.get("role") == spec["manifest_role"], f"{role} P1.09 manifest role mismatch")
    require(manifest.get("guest_inputs") == plan.get("guest_inputs"), f"{role} P1.09 manifest/plan guest inputs differ")
    require(manifest.get("trace") == capture.get("trace"), f"{role} P1.09 manifest/capture trace contract differs")
    machine = manifest.get("machine", {})
    require(machine.get("type") == "vmapple" and machine.get("accelerator") == spec["accelerator"]
            and machine.get("cpu_model") == spec["cpu"], f"{role} P1.09 machine contract drift")
    require(machine.get("ram_mib") == policy["runtime_parameters"]["ram_mib"]
            and machine.get("smp") == policy["runtime_parameters"]["smp"], f"{role} P1.09 RAM/SMP drift")
    require(manifest.get("source", {}).get("revision") == EXPECTED_INFERNO, f"{role} P1.09 Inferno revision drift")


def validate_plan_pair(reference: dict[str, Any], probe: dict[str, Any], policy: dict[str, Any]) -> None:
    mismatches = []
    for path in policy["plan_pair_equal_paths"]:
        rv = get_path(reference, path)
        pv = get_path(probe, path)
        if rv != pv:
            mismatches.append({"path": path, "reference": rv, "probe": pv})
    require(not mismatches, f"P4.01 plan pair is not comparable: {mismatches}")
    require(reference["session_fingerprint"] != probe["session_fingerprint"],
            "reference and probe session fingerprints unexpectedly identical")


def run_p1_compare(reference_path: Path, probe_path: Path) -> dict[str, Any]:
    require(P1_TOOL.is_file(), "P1.09 manifest tool is missing")
    require(P1_POLICY.is_file(), "P1.09 manifest policy is missing")
    with tempfile.TemporaryDirectory(prefix="applesilicon-p4.04-") as td:
        report = Path(td) / "pair.json"
        proc = subprocess.run(
            [sys.executable, str(P1_TOOL), "compare", str(reference_path), str(probe_path),
             "--policy", str(P1_POLICY), "--report-json", str(report)],
            text=True, capture_output=True, timeout=30,
        )
        if proc.returncode != 0:
            detail = (proc.stdout or "") + (proc.stderr or "")
            raise ABError(f"P1.09 rejected the A/B pair: {detail.strip()}")
        data = load_json(report)
    require(data.get("comparable") is True, "P1.09 pair report is not comparable")
    require(data.get("contract_mismatches") == [], "P1.09 pair report contains mismatches")
    return data


def assemble(args: argparse.Namespace, policy: dict[str, Any]) -> dict[str, Any]:
    validate_policy(policy)
    validate_locked_artifacts(policy)
    ref_plan_path = Path(args.reference_plan)
    probe_plan_path = Path(args.probe_plan)
    ref_capture_path = Path(args.reference_capture)
    probe_capture_path = Path(args.probe_capture)
    ref_manifest_path = Path(args.reference_manifest)
    probe_manifest_path = Path(args.probe_manifest)
    reference_plan = load_json(ref_plan_path)
    probe_plan = load_json(probe_plan_path)
    reference_capture = load_json(ref_capture_path)
    probe_capture = load_json(probe_capture_path)
    reference_manifest = load_json(ref_manifest_path)
    probe_manifest = load_json(probe_manifest_path)
    validate_plan(reference_plan, "reference", policy)
    validate_plan(probe_plan, "probe", policy)
    validate_plan_pair(reference_plan, probe_plan, policy)
    validate_capture(reference_capture, reference_plan, reference_manifest, ref_manifest_path, "reference", policy)
    validate_capture(probe_capture, probe_plan, probe_manifest, probe_manifest_path, "probe", policy)
    p1_report = run_p1_compare(ref_manifest_path, probe_manifest_path)
    shared = {
        "source_revision": EXPECTED_INFERNO,
        "machine": "vmapple",
        "ram_mib": policy["runtime_parameters"]["ram_mib"],
        "smp": policy["runtime_parameters"]["smp"],
        "platform_integration_fingerprint": reference_plan["p3_06"]["platform_integration_fingerprint"],
        "p3_06_manifest_sha256": reference_plan["p3_06"]["sha256"],
        "machine_uuid_sha256": reference_plan["machine_uuid"]["sha256"],
        "guest_inputs": copy.deepcopy(reference_plan["guest_inputs"]),
        "trace_contract": copy.deepcopy(reference_plan["trace_contract"]),
        "qemu_version": reference_plan["qemu"]["version"],
    }
    bundle = {
        "schema": 1,
        "classification": "P4_04_AB_SESSION_READY",
        "project_version": EXPECTED_VERSION,
        "part": "Part 04",
        "objective": "P4.04",
        "runtime_observation": True,
        "divergence_promoted": False,
        "shared_contract": shared,
        "reference": {
            "session_plan_sha256": sha256_file(ref_plan_path),
            "session_fingerprint": reference_plan["session_fingerprint"],
            "capture_sha256": sha256_file(ref_capture_path),
            "capture_fingerprint": reference_capture["capture_fingerprint"],
            "manifest_sha256": sha256_file(ref_manifest_path),
            "run_id": reference_manifest["run"]["id"],
            "result": reference_manifest["run"]["result"],
            "host": copy.deepcopy(reference_plan["host"]),
            "qemu": {k: reference_plan["qemu"][k] for k in ("sha256", "bytes", "version")},
            "machine": copy.deepcopy(reference_capture["machine"]),
        },
        "probe": {
            "session_plan_sha256": sha256_file(probe_plan_path),
            "session_fingerprint": probe_plan["session_fingerprint"],
            "capture_sha256": sha256_file(probe_capture_path),
            "capture_fingerprint": probe_capture["capture_fingerprint"],
            "manifest_sha256": sha256_file(probe_manifest_path),
            "run_id": probe_manifest["run"]["id"],
            "result": probe_manifest["run"]["result"],
            "host": copy.deepcopy(probe_plan["host"]),
            "qemu": {k: probe_plan["qemu"][k] for k in ("sha256", "bytes", "version")},
            "machine": copy.deepcopy(probe_capture["machine"]),
        },
        "p1_09_pairing": {
            "comparable": True,
            "reference_run_id": p1_report["reference_run_id"],
            "probe_run_id": p1_report["probe_run_id"],
            "contract_mismatches": [],
            "expected_differences": copy.deepcopy(p1_report["expected_differences"]),
        },
        "expected_role_differences": list(policy["expected_role_differences"]),
        "runtime_authority": {"pair_comparability": "P1.09", "trace_comparison": "P1.08", "promotion": "P1.10"},
        "sanitization": {"raw_local_paths_stored": False, "raw_uuid_stored": False, "guest_input_contents_stored": False},
        "next_objective": "P4.05",
    }
    bundle["ab_fingerprint"] = sha256_bytes(canonical({k: v for k, v in bundle.items() if k != "classification"}))
    return bundle


def expect_policy_failure(policy: dict[str, Any], mutate, label: str) -> None:
    broken = copy.deepcopy(policy)
    mutate(broken)
    try:
        validate_policy(broken)
    except ABError:
        print(f"self-check reject: PASS: {label}")
        return
    raise ABError(f"self-check mutation was accepted: {label}")


def self_check(policy: dict[str, Any]) -> None:
    validate_policy(policy)
    expect_policy_failure(policy, lambda d: d["runtime_parameters"].__setitem__("smp", 8), "SMP drift")
    expect_policy_failure(policy, lambda d: d["roles"]["reference"].__setitem__("accelerator", "tcg"), "reference accelerator drift")
    expect_policy_failure(policy, lambda d: d["roles"]["probe"].__setitem__("cpu", "max"), "probe CPU drift")
    expect_policy_failure(policy, lambda d: d["plan_pair_equal_paths"].remove("machine_uuid.sha256"), "UUID equality removal")
    expect_policy_failure(policy, lambda d: d["plan_pair_equal_paths"].remove("qemu.version"), "QEMU version equality removal")
    expect_policy_failure(policy, lambda d: d["requirements"].__setitem__("p1_09_pair_must_be_comparable", False), "P1.09 authority weakening")
    expect_policy_failure(policy, lambda d: d.__setitem__("next_objective", "P4.06"), "objective skip")
    print("P4.04 self-check: PASS")


def write_result(path: str | None, data: dict[str, Any]) -> None:
    raw = canonical(data)
    if path:
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(raw)
    sys.stdout.buffer.write(raw)


def main() -> int:
    parser = argparse.ArgumentParser(description="AppleSilicon P4.04 comparable A/B session assembler")
    parser.add_argument("--policy", default=str(DEFAULT_POLICY))
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("validate-policy")
    sub.add_parser("self-check")
    ap = sub.add_parser("assemble")
    ap.add_argument("--reference-plan", required=True)
    ap.add_argument("--probe-plan", required=True)
    ap.add_argument("--reference-capture", required=True)
    ap.add_argument("--probe-capture", required=True)
    ap.add_argument("--reference-manifest", required=True)
    ap.add_argument("--probe-manifest", required=True)
    ap.add_argument("--output")
    args = parser.parse_args()
    try:
        policy = load_json(Path(args.policy))
        validate_policy(policy)
        validate_locked_artifacts(policy)
        if args.command == "validate-policy":
            print("P4.04 policy: PASS")
            return 0
        if args.command == "self-check":
            self_check(policy)
            return 0
        result = assemble(args, policy)
        write_result(args.output, result)
        return 0
    except (ABError, OSError, subprocess.TimeoutExpired) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

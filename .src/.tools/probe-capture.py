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
import uuid
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_POLICY = ROOT / ".src/.configs/p4.02-probe-capture-policy.json"
EXPECTED_VERSION = "4.1.0.0.0.0"
EXPECTED_INFERNO = "cc4302a99167abec69b714cfd00c38caece7e7de"
EXPECTED_MACHINE = {"machine": "vmapple", "accelerator": "tcg", "cpu": "apple-gxf"}
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class CaptureError(RuntimeError):
    pass


def require(value: bool, message: str) -> None:
    if not value:
        raise CaptureError(message)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


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


def digest_file(path: Path) -> dict[str, Any]:
    require(path.is_file(), f"input is not a file: {path}")
    size = path.stat().st_size
    require(size > 0, f"input is empty: {path}")
    return {"sha256": sha256_file(path), "bytes": size}


def validate_policy(policy: dict[str, Any]) -> None:
    require(policy.get("schema") == 1, "P4.02 schema mismatch")
    require(policy.get("project_version") == EXPECTED_VERSION, "P4.02 version mismatch")
    require(policy.get("part") == "Part 04", "P4.02 part mismatch")
    require(policy.get("objective") == "P4.02", "P4.02 objective mismatch")
    require(policy.get("title") == "Integrated TCG Probe Capture", "P4.02 title mismatch")
    require(policy.get("source_lock", {}).get("inferno_revision") == EXPECTED_INFERNO,
            "P4.02 Inferno source lock drift")
    contract = policy.get("probe_contract", {})
    require(contract == {
        "machine": "vmapple",
        "accelerator": "tcg",
        "cpu": "apple-gxf",
        "session_plan_classification": "P4_01_SESSION_PLAN_READY",
        "runtime_result_prefix": "P1_07_PROBE_",
        "runtime_manifest_role": "probe",
    }, "P4.02 probe contract drift")
    require(policy.get("required_trace_events") ==
            ["memory_region_ops_read", "memory_region_ops_write"], "trace event contract drift")
    require(policy.get("required_debug_items") ==
            ["guest_errors", "unimp", "int", "cpu_reset"], "debug item contract drift")
    require(policy.get("required_runtime_artifact_kinds") ==
            ["launcher_log", "serial_log", "qemu_debug_log", "trace_capability_log"],
            "runtime artifact contract drift")
    requirements = policy.get("requirements", {})
    for key in (
        "p4_01_probe_session_plan_must_be_ready",
        "session_fingerprint_required",
        "qemu_and_inputs_must_match_session_plan_before_run",
        "qemu_and_inputs_must_match_session_plan_after_run",
        "preflight_results_must_be_byte_identical",
        "p3_06_runtime_delegate_must_be_reused",
        "p1_07_runtime_probe_must_be_reused",
        "probe_accelerator_must_be_tcg",
        "probe_cpu_must_be_apple_gxf",
        "probe_manifest_must_validate_under_p1_09",
        "probe_manifest_inputs_must_match_session_plan",
        "probe_manifest_trace_contract_must_match_session_plan",
        "runtime_artifacts_must_be_digest_bound",
        "capture_manifest_must_store_no_raw_local_paths",
        "capture_manifest_is_not_a_divergence_promotion",
        "p1_10_promotion_gate_remains_authoritative",
        "no_new_inferno_patch_for_p4_02",
        "root_readme_remains_frozen",
    ):
        require(requirements.get(key) is True, f"P4.02 requirement disabled: {key}")
    require(policy.get("next_objective") == "P4.03", "P4.02 next objective must be P4.03")


def validate_locked_artifacts(policy: dict[str, Any]) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in policy.get("locked_project_artifacts", []):
        rel = item.get("path")
        require(isinstance(rel, str) and rel and rel not in seen, f"invalid/duplicate locked artifact: {rel}")
        seen.add(rel)
        path = ROOT / rel
        require(path.is_file(), f"locked artifact missing: {rel}")
        observed = git_blob(path)
        require(observed == item.get("git_blob_sha"), f"locked artifact drift: {rel}: {observed}")
        out.append({"path": rel, "role": item["role"], "git_blob_sha": observed})
    return out


def validate_session_plan(plan: dict[str, Any], policy: dict[str, Any]) -> None:
    require(plan.get("schema") == 1, "P4.01 session plan schema mismatch")
    require(plan.get("classification") == "P4_01_SESSION_PLAN_READY", "P4.01 probe session plan is not ready")
    require(plan.get("project_version") == "4.0.0.0.0.0", "P4.01 session plan version mismatch")
    require(plan.get("part") == "Part 04" and plan.get("objective") == "P4.01",
            "P4.01 session plan identity mismatch")
    require(plan.get("role") == "probe", "P4.02 requires role=probe session plan")
    require(plan.get("guest_execution") is False and plan.get("runtime_evidence") is False,
            "P4.01 session plan must remain pre-execution metadata")
    require(plan.get("integrated_machine") == EXPECTED_MACHINE, "P4.01 probe machine contract drift")
    fp = plan.get("session_fingerprint")
    require(isinstance(fp, str) and SHA256_RE.fullmatch(fp) is not None, "P4.01 session fingerprint invalid")
    trace = plan.get("trace_contract", {})
    require(trace.get("events") == policy["required_trace_events"], "session trace events drift")
    require(trace.get("debug_items") == policy["required_debug_items"], "session debug items drift")
    qemu = plan.get("qemu", {})
    require(isinstance(qemu.get("sha256"), str) and SHA256_RE.fullmatch(qemu["sha256"]),
            "session QEMU digest invalid")
    require(qemu.get("capabilities") == {
        "machine_vmapple": True,
        "accelerator": "tcg",
        "cpu": "apple-gxf",
    }, "session QEMU capabilities drift")
    inputs = plan.get("guest_inputs", {})
    for name in ("firmware", "auxiliary_storage", "disk", "machine_identity"):
        value = inputs.get(name)
        require(isinstance(value, dict) and SHA256_RE.fullmatch(str(value.get("sha256", ""))) is not None,
                f"session input digest invalid: {name}")
        require(isinstance(value.get("bytes"), int) and value["bytes"] > 0, f"session input size invalid: {name}")
    hw = inputs.get("hardware_model")
    if hw is not None:
        require(isinstance(hw, dict) and SHA256_RE.fullmatch(str(hw.get("sha256", ""))) is not None,
                "session hardware-model digest invalid")
    uuid_meta = plan.get("machine_uuid", {})
    require(SHA256_RE.fullmatch(str(uuid_meta.get("sha256", ""))) is not None,
            "session machine UUID digest invalid")
    require(uuid_meta.get("raw_value_stored") is False, "session plan stored a raw machine UUID")


def run_qemu(qemu: Path, *args: str) -> str:
    try:
        proc = subprocess.run([str(qemu), *args], text=True, capture_output=True, timeout=15, errors="replace")
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise CaptureError(f"QEMU capability query failed ({' '.join(args)}): {exc}") from exc
    output = (proc.stdout or "") + (proc.stderr or "")
    require(proc.returncode == 0, f"QEMU capability query failed ({' '.join(args)}): {output.strip()}")
    return output


def token_present(text: str, token: str) -> bool:
    return re.search(r"(^|[\s,])" + re.escape(token) + r"([\s,]|$)", text, re.MULTILINE) is not None


def normalized_uuid(value: str) -> str:
    try:
        return str(uuid.UUID(value)).lower()
    except ValueError as exc:
        raise CaptureError("machine UUID must be canonicalizable") from exc


def validate_p3_binding(plan: dict[str, Any], path: Path) -> None:
    require(path.is_file(), f"P3.06 integration manifest missing: {path}")
    data = load_json(path)
    require(data.get("classification") == "P3_06_INTEGRATION_PASS", "P3.06 integration manifest did not pass")
    require(data.get("part_status") == "closed_implementation_complete", "Part 03 is not closed")
    require(data.get("guest_execution") is False, "P3.06 manifest unexpectedly records guest execution")
    expected = plan.get("p3_06", {})
    require(sha256_file(path) == expected.get("sha256"), "P3.06 manifest digest differs from P4.01 session plan")
    require(data.get("platform_integration_fingerprint") == expected.get("platform_integration_fingerprint"),
            "P3.06 platform fingerprint differs from P4.01 session plan")


def build_preflight(args: argparse.Namespace, policy: dict[str, Any]) -> dict[str, Any]:
    plan = load_json(Path(args.session_plan))
    validate_session_plan(plan, policy)
    validate_p3_binding(plan, Path(args.p3_06_manifest))

    qemu_path = Path(args.qemu_bin)
    require(qemu_path.is_file() and os.access(qemu_path, os.X_OK), "QEMU binary missing or not executable")
    qemu_plan = plan["qemu"]
    require(sha256_file(qemu_path) == qemu_plan["sha256"], "QEMU binary digest changed after P4.01 planning")
    require(qemu_path.stat().st_size == qemu_plan["bytes"], "QEMU binary size changed after P4.01 planning")
    version_lines = run_qemu(qemu_path, "-version").strip().splitlines()
    require(version_lines and version_lines[0] == qemu_plan["version"], "QEMU version changed after P4.01 planning")
    require(token_present(run_qemu(qemu_path, "-machine", "help"), "vmapple"), "QEMU no longer advertises vmapple")
    require(token_present(run_qemu(qemu_path, "-accel", "help"), "tcg"), "QEMU no longer advertises TCG")
    require(token_present(run_qemu(qemu_path, "-cpu", "help"), "apple-gxf"), "QEMU no longer advertises apple-gxf")

    actual_inputs = {
        "firmware": digest_file(Path(args.firmware)),
        "auxiliary_storage": digest_file(Path(args.auxiliary_storage)),
        "disk": digest_file(Path(args.disk)),
        "machine_identity": digest_file(Path(args.machine_identity)),
        "hardware_model": digest_file(Path(args.hardware_model)) if args.hardware_model else None,
    }
    require(actual_inputs == plan["guest_inputs"], "guest input digest set differs from P4.01 session plan")
    normalized = normalized_uuid(args.machine_uuid)
    uuid_digest = sha256_bytes(normalized.encode("ascii"))
    require(uuid_digest == plan["machine_uuid"]["sha256"], "machine UUID digest differs from P4.01 session plan")

    result = {
        "schema": 1,
        "classification": "P4_02_PREFLIGHT_PASS",
        "project_version": EXPECTED_VERSION,
        "role": "probe",
        "guest_execution": False,
        "session_fingerprint": plan["session_fingerprint"],
        "platform_integration_fingerprint": plan["p3_06"]["platform_integration_fingerprint"],
        "host": {"os": platform.system(), "arch": platform.machine()},
        "qemu": {
            "binary_label": qemu_path.name,
            "sha256": qemu_plan["sha256"],
            "bytes": qemu_plan["bytes"],
            "version": qemu_plan["version"],
            "machine": "vmapple",
            "accelerator": "tcg",
            "cpu": "apple-gxf",
        },
        "machine_uuid_sha256": uuid_digest,
        "guest_inputs": actual_inputs,
        "trace_contract": plan["trace_contract"],
        "raw_paths_stored": False,
    }
    result["preflight_fingerprint"] = sha256_bytes(canonical({k: v for k, v in result.items() if k != "classification"}))
    return result


def launcher_value(path: Path, label: str, *, first: bool = False) -> str:
    values = []
    prefix = label + ": "
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith(prefix):
            values.append(line[len(prefix):])
    require(bool(values), f"launcher log missing field: {label}")
    return values[0] if first else values[-1]


def artifact_by_kind(manifest: dict[str, Any], kind: str) -> dict[str, Any]:
    matches = [item for item in manifest.get("artifacts", []) if item.get("kind") == kind]
    require(len(matches) == 1, f"probe manifest must contain exactly one {kind} artifact")
    return matches[0]


def finalize_capture(args: argparse.Namespace, policy: dict[str, Any]) -> dict[str, Any]:
    plan_path = Path(args.session_plan)
    probe_path = Path(args.probe_manifest)
    launcher_path = Path(args.launcher_log)
    preflight_path = Path(args.preflight)
    plan = load_json(plan_path)
    validate_session_plan(plan, policy)
    require(probe_path.is_file(), "P1.09 probe manifest is missing")
    require(launcher_path.is_file(), "P1.07 launcher log is missing")
    require(preflight_path.is_file(), "P4.02 preflight result is missing")
    preflight = load_json(preflight_path)
    require(preflight.get("classification") == "P4_02_PREFLIGHT_PASS", "P4.02 preflight did not pass")
    require(preflight.get("session_fingerprint") == plan["session_fingerprint"], "preflight/session fingerprint mismatch")

    probe = load_json(probe_path)
    require(probe.get("role") == "probe", "runtime manifest role is not probe")
    require(probe.get("source", {}).get("revision") == EXPECTED_INFERNO, "probe Inferno revision drift")
    require(probe.get("machine", {}).get("type") == "vmapple", "probe machine type drift")
    require(probe.get("machine", {}).get("accelerator") == "tcg", "probe accelerator is not TCG")
    require(probe.get("machine", {}).get("cpu_model") == "apple-gxf", "probe CPU is not apple-gxf")
    result = probe.get("run", {}).get("result")
    require(isinstance(result, str) and result.startswith("P1_07_PROBE_"), "probe runtime result is not a completed P1.07 observation")
    require(probe.get("guest_inputs") == plan.get("guest_inputs"), "P1.09 probe inputs differ from P4.01 session plan")
    require(probe.get("trace") == {
        "events": policy["required_trace_events"],
        "debug_items": policy["required_debug_items"],
    }, "P1.09 probe trace/debug contract differs from P4.01")

    for kind in policy["required_runtime_artifact_kinds"]:
        artifact_by_kind(probe, kind)
    launcher_artifact = artifact_by_kind(probe, "launcher_log")
    require(sha256_file(launcher_path) == launcher_artifact["sha256"], "launcher log digest differs from P1.09 artifact record")
    require(launcher_path.stat().st_size == launcher_artifact["bytes"], "launcher log size differs from P1.09 artifact record")
    require(launcher_value(launcher_path, "Accelerator", first=True) == "tcg", "launcher accelerator is not TCG")
    require(launcher_value(launcher_path, "CPU profile", first=True) == "apple-gxf", "launcher CPU is not apple-gxf")
    require(launcher_value(launcher_path, "Classification").startswith("P1_07_PROBE_"), "launcher classification is not a completed probe")
    require(launcher_value(launcher_path, "UUID SHA-256", first=True) == plan["machine_uuid"]["sha256"],
            "launcher UUID digest differs from P4.01 session plan")

    capture = {
        "schema": 1,
        "classification": "P4_02_PROBE_CAPTURE_READY",
        "project_version": EXPECTED_VERSION,
        "part": "Part 04",
        "objective": "P4.02",
        "runtime_observation": True,
        "divergence_promoted": False,
        "session_fingerprint": plan["session_fingerprint"],
        "platform_integration_fingerprint": plan["p3_06"]["platform_integration_fingerprint"],
        "preflight": {
            "sha256": sha256_file(preflight_path),
            "preflight_fingerprint": preflight["preflight_fingerprint"],
        },
        "probe_manifest": {
            "sha256": sha256_file(probe_path),
            "run_id": probe["run"]["id"],
            "started_utc": probe["run"]["started_utc"],
            "ended_utc": probe["run"]["ended_utc"],
            "result": result,
        },
        "machine": {"type": "vmapple", "accelerator": "tcg", "cpu_model": "apple-gxf"},
        "guest_inputs": copy.deepcopy(probe["guest_inputs"]),
        "trace": copy.deepcopy(probe["trace"]),
        "artifacts": copy.deepcopy(probe["artifacts"]),
        "sanitization": {
            "raw_local_paths_stored": False,
            "raw_uuid_stored": False,
            "guest_input_contents_stored": False,
        },
        "runtime_authority": {
            "manifest": "P1.09",
            "promotion": "P1.10",
        },
        "next_objective": "P4.03",
    }
    capture["capture_fingerprint"] = sha256_bytes(canonical({k: v for k, v in capture.items() if k != "classification"}))
    return capture


def expect_policy_failure(policy: dict[str, Any], mutate, label: str) -> None:
    broken = copy.deepcopy(policy)
    mutate(broken)
    try:
        validate_policy(broken)
    except CaptureError:
        print(f"self-check reject: PASS: {label}")
        return
    raise CaptureError(f"self-check mutation was accepted: {label}")


def self_check(policy: dict[str, Any]) -> None:
    validate_policy(policy)
    expect_policy_failure(policy, lambda d: d["probe_contract"].__setitem__("cpu", "max"), "probe CPU drift")
    expect_policy_failure(policy, lambda d: d["probe_contract"].__setitem__("accelerator", "hvf"), "probe accelerator drift")
    expect_policy_failure(policy, lambda d: d["required_trace_events"].pop(), "trace contract weakening")
    expect_policy_failure(policy, lambda d: d["required_runtime_artifact_kinds"].pop(), "artifact contract weakening")
    expect_policy_failure(policy, lambda d: d["requirements"].__setitem__("capture_manifest_is_not_a_divergence_promotion", False), "automatic promotion")
    expect_policy_failure(policy, lambda d: d.__setitem__("next_objective", "P4.04"), "objective skip")
    print("P4.02 self-check: PASS")


def write_result(path: str | None, data: dict[str, Any]) -> None:
    raw = canonical(data)
    if path:
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(raw)
    sys.stdout.buffer.write(raw)


def main() -> int:
    parser = argparse.ArgumentParser(description="AppleSilicon P4.02 integrated TCG probe capture")
    parser.add_argument("--policy", default=str(DEFAULT_POLICY))
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("validate-policy")
    sub.add_parser("self-check")

    pre = sub.add_parser("preflight")
    pre.add_argument("--session-plan", required=True)
    pre.add_argument("--p3-06-manifest", required=True)
    pre.add_argument("--qemu-bin", required=True)
    pre.add_argument("--machine-uuid", required=True)
    pre.add_argument("--firmware", required=True)
    pre.add_argument("--auxiliary-storage", required=True)
    pre.add_argument("--disk", required=True)
    pre.add_argument("--machine-identity", required=True)
    pre.add_argument("--hardware-model")
    pre.add_argument("--output")

    fin = sub.add_parser("finalize")
    fin.add_argument("--session-plan", required=True)
    fin.add_argument("--probe-manifest", required=True)
    fin.add_argument("--launcher-log", required=True)
    fin.add_argument("--preflight", required=True)
    fin.add_argument("--output")

    args = parser.parse_args()
    try:
        policy = load_json(Path(args.policy))
        validate_policy(policy)
        validate_locked_artifacts(policy)
        if args.command == "validate-policy":
            print("P4.02 probe capture policy: PASS")
        elif args.command == "self-check":
            self_check(policy)
        elif args.command == "preflight":
            write_result(args.output, build_preflight(args, policy))
        elif args.command == "finalize":
            write_result(args.output, finalize_capture(args, policy))
        return 0
    except (OSError, json.JSONDecodeError, CaptureError) as exc:
        print(f"P4.02 capture failure: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

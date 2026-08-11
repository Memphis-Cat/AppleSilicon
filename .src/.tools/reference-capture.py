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
DEFAULT_POLICY = ROOT / ".src/.configs/p4.03-reference-capture-policy.json"
EXPECTED_VERSION = "4.2.0.0.0.0"
EXPECTED_INFERNO = "cc4302a99167abec69b714cfd00c38caece7e7de"
EXPECTED_MACHINE = {"machine": "vmapple", "accelerator": "hvf", "cpu": "host"}
EXPECTED_HOST = {"os": "Darwin", "arch": "arm64"}
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class ReferenceCaptureError(RuntimeError):
    pass


def require(value: bool, message: str) -> None:
    if not value:
        raise ReferenceCaptureError(message)


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
    require(policy.get("schema") == 1, "P4.03 schema mismatch")
    require(policy.get("project_version") == EXPECTED_VERSION, "P4.03 version mismatch")
    require(policy.get("part") == "Part 04", "P4.03 part mismatch")
    require(policy.get("objective") == "P4.03", "P4.03 objective mismatch")
    require(policy.get("title") == "Apple Silicon HVF Reference Capture", "P4.03 title mismatch")
    require(policy.get("source_lock", {}).get("inferno_revision") == EXPECTED_INFERNO,
            "P4.03 Inferno source lock drift")
    contract = policy.get("reference_contract", {})
    require(contract == {
        "machine": "vmapple",
        "accelerator": "hvf",
        "cpu": "host",
        "required_host": EXPECTED_HOST,
        "session_plan_classification": "P4_01_SESSION_PLAN_READY",
        "runtime_result_prefix": "P1_09_REFERENCE_",
        "runtime_manifest_role": "reference",
    }, "P4.03 reference contract drift")
    require(policy.get("runtime_parameters") == {
        "ram": "4G", "ram_mib": 4096, "smp": 4, "capture_seconds": 30, "grace_seconds": 3,
    }, "P4.03 runtime parameter lock drift")
    require(policy.get("required_trace_events") ==
            ["memory_region_ops_read", "memory_region_ops_write"], "trace event contract drift")
    require(policy.get("required_debug_items") ==
            ["guest_errors", "unimp", "int", "cpu_reset"], "debug item contract drift")
    require(policy.get("required_manifest_artifact_kinds") ==
            ["serial_log", "qemu_debug_log", "trace_capability_log"], "manifest artifact contract drift")
    require(policy.get("capture_only_artifact_kinds") == ["launcher_log"],
            "capture-only artifact contract drift")
    for key, value in policy.get("requirements", {}).items():
        require(value is True, f"P4.03 requirement disabled: {key}")
    require(policy.get("next_objective") == "P4.04", "P4.03 next objective must be P4.04")


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
    require(plan.get("classification") == "P4_01_SESSION_PLAN_READY", "P4.01 reference session plan is not ready")
    require(plan.get("project_version") == "4.0.0.0.0.0", "P4.01 session plan version mismatch")
    require(plan.get("part") == "Part 04" and plan.get("objective") == "P4.01",
            "P4.01 session plan identity mismatch")
    require(plan.get("role") == "reference", "P4.03 requires role=reference session plan")
    require(plan.get("guest_execution") is False and plan.get("runtime_evidence") is False,
            "P4.01 session plan must remain pre-execution metadata")
    require(plan.get("integrated_machine") == EXPECTED_MACHINE, "P4.01 reference machine contract drift")
    require(plan.get("host") == EXPECTED_HOST, "P4.01 reference host contract drift")
    fp = plan.get("session_fingerprint")
    require(isinstance(fp, str) and SHA256_RE.fullmatch(fp) is not None, "P4.01 session fingerprint invalid")
    trace = plan.get("trace_contract", {})
    require(trace.get("events") == policy["required_trace_events"], "session trace events drift")
    require(trace.get("debug_items") == policy["required_debug_items"], "session debug items drift")
    qemu = plan.get("qemu", {})
    require(isinstance(qemu.get("sha256"), str) and SHA256_RE.fullmatch(qemu["sha256"]) is not None,
            "session QEMU digest invalid")
    require(qemu.get("capabilities") == {
        "machine_vmapple": True, "accelerator": "hvf", "cpu": "host",
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
        proc = subprocess.run([str(qemu), *args], text=True, capture_output=True,
                              timeout=15, errors="replace")
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ReferenceCaptureError(f"QEMU capability query failed ({' '.join(args)}): {exc}") from exc
    output = (proc.stdout or "") + (proc.stderr or "")
    require(proc.returncode == 0, f"QEMU capability query failed ({' '.join(args)}): {output.strip()}")
    return output


def token_present(text: str, token: str) -> bool:
    return re.search(r"(^|[\s,])" + re.escape(token) + r"([\s,]|$)", text, re.MULTILINE) is not None


def normalized_uuid(value: str) -> str:
    try:
        return str(uuid.UUID(value)).lower()
    except ValueError as exc:
        raise ReferenceCaptureError("machine UUID must be canonicalizable") from exc


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
    host = {"os": platform.system(), "arch": platform.machine()}
    require(host == EXPECTED_HOST,
            f"P4.03 reference requires Darwin/arm64; observed {host['os']}/{host['arch']}")
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
    require(token_present(run_qemu(qemu_path, "-accel", "help"), "hvf"), "QEMU no longer advertises HVF")
    require(token_present(run_qemu(qemu_path, "-cpu", "help"), "host"), "QEMU no longer advertises host CPU")

    actual_inputs = {
        "firmware": digest_file(Path(args.firmware)),
        "auxiliary_storage": digest_file(Path(args.auxiliary_storage)),
        "disk": digest_file(Path(args.disk)),
        "machine_identity": digest_file(Path(args.machine_identity)),
        "hardware_model": digest_file(Path(args.hardware_model)) if args.hardware_model else None,
    }
    require(actual_inputs == plan["guest_inputs"], "guest input digest set differs from P4.01 session plan")
    uuid_digest = sha256_bytes(normalized_uuid(args.machine_uuid).encode("ascii"))
    require(uuid_digest == plan["machine_uuid"]["sha256"], "machine UUID digest differs from P4.01 session plan")

    result = {
        "schema": 1,
        "classification": "P4_03_PREFLIGHT_PASS",
        "project_version": EXPECTED_VERSION,
        "role": "reference",
        "guest_execution": False,
        "session_fingerprint": plan["session_fingerprint"],
        "platform_integration_fingerprint": plan["p3_06"]["platform_integration_fingerprint"],
        "host": host,
        "qemu": {
            "binary_label": qemu_path.name,
            "sha256": qemu_plan["sha256"],
            "bytes": qemu_plan["bytes"],
            "version": qemu_plan["version"],
            "machine": "vmapple",
            "accelerator": "hvf",
            "cpu": "host",
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
    require(len(matches) == 1, f"reference manifest must contain exactly one {kind} artifact")
    return matches[0]


def finalize_capture(args: argparse.Namespace, policy: dict[str, Any]) -> dict[str, Any]:
    plan_path = Path(args.session_plan)
    reference_path = Path(args.reference_manifest)
    launcher_path = Path(args.launcher_log)
    preflight_path = Path(args.preflight)
    plan = load_json(plan_path)
    validate_session_plan(plan, policy)
    require(reference_path.is_file(), "P1.09 reference manifest is missing")
    require(launcher_path.is_file(), "P1.09 reference launcher log is missing")
    require(preflight_path.is_file(), "P4.03 preflight result is missing")
    preflight = load_json(preflight_path)
    require(preflight.get("classification") == "P4_03_PREFLIGHT_PASS", "P4.03 preflight did not pass")
    require(preflight.get("session_fingerprint") == plan["session_fingerprint"], "preflight/session fingerprint mismatch")

    reference = load_json(reference_path)
    require(reference.get("role") == "reference", "runtime manifest role is not reference")
    require(reference.get("source", {}).get("revision") == EXPECTED_INFERNO, "reference Inferno revision drift")
    machine = reference.get("machine", {})
    require(machine.get("type") == "vmapple", "reference machine type drift")
    require(machine.get("accelerator") == "hvf", "reference accelerator is not HVF")
    require(machine.get("cpu_model") == "host", "reference CPU is not host")
    require(machine.get("ram_mib") == 4096 and machine.get("smp") == 4, "reference RAM/SMP drift")
    result = reference.get("run", {}).get("result")
    require(isinstance(result, str) and result.startswith("P1_09_REFERENCE_"),
            "reference runtime result is not a completed P1.09 observation")
    require(reference.get("guest_inputs") == plan.get("guest_inputs"),
            "P1.09 reference inputs differ from P4.01 session plan")
    require(reference.get("trace") == {
        "events": policy["required_trace_events"],
        "debug_items": policy["required_debug_items"],
    }, "P1.09 reference trace/debug contract differs from P4.01")
    for kind in policy["required_manifest_artifact_kinds"]:
        artifact_by_kind(reference, kind)

    require(launcher_value(launcher_path, "Host OS", first=True) == "Darwin", "launcher host OS is not Darwin")
    require(launcher_value(launcher_path, "Host architecture", first=True) == "arm64", "launcher host architecture is not arm64")
    require(launcher_value(launcher_path, "Accelerator", first=True) == "hvf", "launcher accelerator is not HVF")
    require(launcher_value(launcher_path, "CPU profile", first=True) == "host", "launcher CPU is not host")
    require(launcher_value(launcher_path, "SMP", first=True) == "4", "launcher SMP drift")
    require(launcher_value(launcher_path, "RAM", first=True) == "4G", "launcher RAM drift")
    require(launcher_value(launcher_path, "Reference seconds", first=True) == "30", "launcher capture duration drift")
    require(launcher_value(launcher_path, "Classification").startswith("P1_09_REFERENCE_"),
            "launcher classification is not a completed reference")
    require(launcher_value(launcher_path, "UUID SHA-256", first=True) == plan["machine_uuid"]["sha256"],
            "launcher UUID digest differs from P4.01 session plan")

    launcher_artifact = {"kind": "launcher_log", "label": launcher_path.name,
                         "sha256": sha256_file(launcher_path), "bytes": launcher_path.stat().st_size}
    capture = {
        "schema": 1,
        "classification": "P4_03_REFERENCE_CAPTURE_READY",
        "project_version": EXPECTED_VERSION,
        "part": "Part 04",
        "objective": "P4.03",
        "runtime_observation": True,
        "divergence_promoted": False,
        "session_fingerprint": plan["session_fingerprint"],
        "platform_integration_fingerprint": plan["p3_06"]["platform_integration_fingerprint"],
        "preflight": {
            "sha256": sha256_file(preflight_path),
            "preflight_fingerprint": preflight["preflight_fingerprint"],
        },
        "reference_manifest": {
            "sha256": sha256_file(reference_path),
            "run_id": reference["run"]["id"],
            "started_utc": reference["run"]["started_utc"],
            "ended_utc": reference["run"]["ended_utc"],
            "result": result,
        },
        "machine": {"type": "vmapple", "accelerator": "hvf", "cpu_model": "host"},
        "host": {"os": "Darwin", "arch": "arm64"},
        "guest_inputs": copy.deepcopy(reference["guest_inputs"]),
        "trace": copy.deepcopy(reference["trace"]),
        "artifacts": copy.deepcopy(reference["artifacts"]) + [launcher_artifact],
        "sanitization": {
            "raw_local_paths_stored": False,
            "raw_uuid_stored": False,
            "guest_input_contents_stored": False,
        },
        "runtime_authority": {"manifest": "P1.09", "promotion": "P1.10"},
        "next_objective": "P4.04",
    }
    capture["capture_fingerprint"] = sha256_bytes(canonical({k: v for k, v in capture.items() if k != "classification"}))
    return capture


def expect_policy_failure(policy: dict[str, Any], mutate, label: str) -> None:
    broken = copy.deepcopy(policy)
    mutate(broken)
    try:
        validate_policy(broken)
    except ReferenceCaptureError:
        print(f"self-check reject: PASS: {label}")
        return
    raise ReferenceCaptureError(f"self-check mutation was accepted: {label}")


def self_check(policy: dict[str, Any]) -> None:
    validate_policy(policy)
    expect_policy_failure(policy, lambda d: d["reference_contract"].__setitem__("cpu", "max"), "reference CPU drift")
    expect_policy_failure(policy, lambda d: d["reference_contract"].__setitem__("accelerator", "tcg"), "reference accelerator drift")
    expect_policy_failure(policy, lambda d: d["reference_contract"]["required_host"].__setitem__("arch", "x86_64"), "reference host drift")
    expect_policy_failure(policy, lambda d: d["runtime_parameters"].__setitem__("smp", 8), "runtime parameter drift")
    expect_policy_failure(policy, lambda d: d["required_trace_events"].pop(), "trace contract weakening")
    expect_policy_failure(policy, lambda d: d["requirements"].__setitem__("reference_unavailable_must_fail_closed", False), "fabricated reference allowance")
    expect_policy_failure(policy, lambda d: d.__setitem__("next_objective", "P4.05"), "objective skip")
    print("P4.03 self-check: PASS")


def write_result(path: str | None, data: dict[str, Any]) -> None:
    raw = canonical(data)
    if path:
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(raw)
    sys.stdout.buffer.write(raw)


def main() -> int:
    parser = argparse.ArgumentParser(description="AppleSilicon P4.03 Apple Silicon HVF reference capture")
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
    fin.add_argument("--reference-manifest", required=True)
    fin.add_argument("--launcher-log", required=True)
    fin.add_argument("--preflight", required=True)
    fin.add_argument("--output")

    args = parser.parse_args()
    try:
        policy = load_json(Path(args.policy))
        validate_policy(policy)
        validate_locked_artifacts(policy)
        if args.command == "validate-policy":
            print("P4.03 reference capture policy: PASS")
        elif args.command == "self-check":
            self_check(policy)
        elif args.command == "preflight":
            write_result(args.output, build_preflight(args, policy))
        elif args.command == "finalize":
            write_result(args.output, finalize_capture(args, policy))
        return 0
    except (OSError, json.JSONDecodeError, ReferenceCaptureError) as exc:
        print(f"P4.03 capture failure: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

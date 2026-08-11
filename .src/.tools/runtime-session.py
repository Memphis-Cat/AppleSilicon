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
DEFAULT_POLICY = ROOT / ".src/.configs/p4.01-runtime-session-policy.json"
EXPECTED_VERSION = "4.0.0.0.0.0"
EXPECTED_INFERNO = "cc4302a99167abec69b714cfd00c38caece7e7de"
EXPECTED_TRACE_EVENTS = ["memory_region_ops_read", "memory_region_ops_write"]
EXPECTED_DEBUG_ITEMS = ["guest_errors", "unimp", "int", "cpu_reset"]


class SessionError(RuntimeError):
    pass


def require(value: bool, message: str) -> None:
    if not value:
        raise SessionError(message)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def canonical(data: dict[str, Any]) -> bytes:
    return (json.dumps(data, sort_keys=True, separators=(",", ":")) + "\n").encode()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
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


def validate_policy(data: dict[str, Any]) -> None:
    require(data.get("schema") == 1, "P4.01 schema mismatch")
    require(data.get("project_version") == EXPECTED_VERSION, "P4.01 version mismatch")
    require(data.get("part") == "Part 04", "P4.01 part mismatch")
    require(data.get("objective") == "P4.01", "P4.01 objective mismatch")
    require(data.get("title") == "Runtime Session Provenance and Input Lock", "P4.01 title mismatch")
    scope = data.get("scope", {})
    require(scope.get("machine") == "vmapple", "P4.01 machine scope drift")
    require(scope.get("guest_execution") is False, "P4.01 must not execute a guest")
    require(scope.get("runtime_evidence_authority") == "Part 01", "runtime evidence authority drift")
    require(data.get("source_lock", {}).get("inferno_revision") == EXPECTED_INFERNO,
            "P4.01 Inferno source lock drift")

    roles = data.get("roles", {})
    require(roles.get("probe") == {"accelerator": "tcg", "cpu": "apple-gxf", "required_host": None},
            "probe role drift")
    require(roles.get("reference") == {
        "accelerator": "hvf",
        "cpu": "host",
        "required_host": {"os": "Darwin", "arch": "arm64"},
    }, "reference role drift")

    require(data.get("required_guest_inputs") ==
            ["firmware", "auxiliary_storage", "disk", "machine_identity"],
            "required guest input set drift")
    require(data.get("optional_guest_inputs") == ["hardware_model"],
            "optional guest input set drift")
    runtime = data.get("runtime_parameters", {}).get("machine_uuid", {})
    require(runtime == {
        "required": True,
        "store_raw_value": False,
        "store_sha256": True,
        "normalization": "lowercase_canonical_uuid",
    }, "machine UUID privacy/provenance policy drift")

    trace = data.get("trace_contract", {})
    require(trace.get("events") == EXPECTED_TRACE_EVENTS, "P4.01 trace event contract drift")
    require(trace.get("debug_items") == EXPECTED_DEBUG_ITEMS, "P4.01 debug item contract drift")
    require(trace.get("qemu_log_backend_supported") is True, "QEMU log trace backend contract disabled")

    privacy = data.get("privacy", {})
    for key in (
        "store_raw_local_paths", "store_raw_machine_uuid", "store_raw_machine_identity",
        "store_raw_hardware_model", "store_real_serial_or_account_identifiers",
        "store_firmware_or_disk_content", "store_hostname",
    ):
        require(privacy.get(key) is False, f"privacy rule must remain false: {key}")
    require(privacy.get("qemu_binary_label_may_use_basename_only") is True,
            "QEMU label privacy rule drift")

    req = data.get("requirements", {})
    for key in (
        "p3_06_manifest_must_pass", "p3_06_part_must_be_closed",
        "p3_06_guest_execution_must_be_false", "platform_integration_fingerprint_required",
        "qemu_binary_sha256_required", "qemu_version_required",
        "qemu_role_capabilities_must_be_verified", "machine_uuid_digest_required",
        "all_required_inputs_must_be_hashed_before_execution", "trace_contract_must_match_part_01",
        "session_plan_must_be_deterministic", "session_plan_is_not_runtime_evidence",
        "part_01_manifest_and_promotion_gates_remain_authoritative", "no_guest_execution_in_p4_01",
        "no_new_inferno_patch_for_p4_01", "root_readme_remains_frozen",
    ):
        require(req.get(key) is True, f"P4.01 requirement disabled: {key}")

    objectives = data.get("part_04_objectives", [])
    require(len(objectives) == 6, "Part 04 must contain exactly six objectives")
    require(objectives[0].startswith("P4.01 "), "Part 04 must start at P4.01")
    require(objectives[-1].startswith("P4.06 "), "Part 04 must end at P4.06")
    require(not any(item.startswith("P4.07") for item in objectives), "P4.07 is forbidden")
    require(data.get("next_objective") == "P4.02", "P4.01 next objective must be P4.02")


def validate_locked_artifacts(policy: dict[str, Any]) -> list[dict[str, str]]:
    result = []
    seen: set[str] = set()
    for item in policy.get("locked_project_artifacts", []):
        rel = item.get("path")
        require(isinstance(rel, str) and rel and rel not in seen, f"invalid/duplicate artifact: {rel}")
        seen.add(rel)
        path = ROOT / rel
        require(path.is_file(), f"locked artifact missing: {rel}")
        observed = git_blob(path)
        require(observed == item.get("git_blob_sha"), f"locked artifact drift: {rel}: {observed}")
        result.append({"path": rel, "role": item["role"], "git_blob_sha": observed})
    return result


def validate_p3_manifest(path: Path) -> dict[str, str]:
    require(path.is_file(), f"P3.06 integration manifest missing: {path}")
    data = load_json(path)
    require(data.get("classification") == "P3_06_INTEGRATION_PASS", "P3.06 integration did not pass")
    require(data.get("part_status") == "closed_implementation_complete", "Part 03 is not closed")
    require(data.get("guest_execution") is False, "P3.06 manifest unexpectedly records guest execution")
    require(data.get("next_part") == "Part 04" and data.get("next_objective") == "P4.01",
            "P3.06 transition to Part 04 drifted")
    fp = data.get("platform_integration_fingerprint")
    require(isinstance(fp, str) and re.fullmatch(r"[0-9a-f]{64}", fp) is not None,
            "P3.06 platform integration fingerprint invalid")
    return {"classification": data["classification"], "platform_integration_fingerprint": fp,
            "sha256": sha256_file(path)}


def run_qemu(qemu: Path, *args: str) -> str:
    try:
        proc = subprocess.run([str(qemu), *args], text=True, capture_output=True,
                              timeout=15, errors="replace")
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise SessionError(f"QEMU capability query failed ({' '.join(args)}): {exc}") from exc
    output = (proc.stdout or "") + (proc.stderr or "")
    require(proc.returncode == 0, f"QEMU capability query failed ({' '.join(args)}): {output.strip()}")
    return output


def token_present(text: str, token: str) -> bool:
    return re.search(r"(^|[\s,])" + re.escape(token) + r"([\s,]|$)", text, re.MULTILINE) is not None


def qemu_provenance(qemu: Path, role: str, policy: dict[str, Any]) -> dict[str, Any]:
    require(qemu.is_file(), f"QEMU binary missing: {qemu}")
    require(os.access(qemu, os.X_OK), f"QEMU binary is not executable: {qemu}")
    version = run_qemu(qemu, "-version").strip().splitlines()
    require(version, "QEMU version output is empty")
    machines = run_qemu(qemu, "-machine", "help")
    accelerators = run_qemu(qemu, "-accel", "help")
    cpus = run_qemu(qemu, "-cpu", "help")
    role_data = policy["roles"][role]
    require(token_present(machines, "vmapple"), "QEMU does not advertise vmapple")
    require(token_present(accelerators, role_data["accelerator"]),
            f"QEMU does not advertise accelerator {role_data['accelerator']}")
    require(token_present(cpus, role_data["cpu"]), f"QEMU does not advertise CPU {role_data['cpu']}")
    return {
        "binary_label": qemu.name,
        "sha256": sha256_file(qemu),
        "bytes": qemu.stat().st_size,
        "version": version[0],
        "capabilities": {
            "machine_vmapple": True,
            "accelerator": role_data["accelerator"],
            "cpu": role_data["cpu"],
        },
    }


def normalized_uuid_digest(value: str) -> dict[str, Any]:
    try:
        normalized = str(uuid.UUID(value)).lower()
    except ValueError as exc:
        raise SessionError("machine UUID must be a canonicalizable UUID") from exc
    encoded = normalized.encode("ascii")
    return {"sha256": sha256_bytes(encoded), "normalized_bytes": len(encoded), "raw_value_stored": False}


def build_plan(args: argparse.Namespace, policy: dict[str, Any]) -> dict[str, Any]:
    validate_policy(policy)
    locked = validate_locked_artifacts(policy)
    role_data = policy["roles"][args.role]
    host = {"os": platform.system(), "arch": platform.machine()}
    required_host = role_data.get("required_host")
    if required_host:
        require(host == required_host,
                f"{args.role} role requires host {required_host['os']}/{required_host['arch']}; observed {host['os']}/{host['arch']}")

    p3 = validate_p3_manifest(Path(args.p3_06_manifest))
    qemu = qemu_provenance(Path(args.qemu_bin), args.role, policy)
    inputs = {
        "firmware": digest_file(Path(args.firmware)),
        "auxiliary_storage": digest_file(Path(args.auxiliary_storage)),
        "disk": digest_file(Path(args.disk)),
        "machine_identity": digest_file(Path(args.machine_identity)),
        "hardware_model": digest_file(Path(args.hardware_model)) if args.hardware_model else None,
    }
    machine_uuid = normalized_uuid_digest(args.machine_uuid)

    plan: dict[str, Any] = {
        "schema": 1,
        "classification": "P4_01_SESSION_PLAN_READY",
        "project_version": EXPECTED_VERSION,
        "part": "Part 04",
        "objective": "P4.01",
        "role": args.role,
        "guest_execution": False,
        "runtime_evidence": False,
        "integrated_machine": {
            "machine": "vmapple",
            "accelerator": role_data["accelerator"],
            "cpu": role_data["cpu"],
        },
        "host": host,
        "p3_06": p3,
        "qemu": qemu,
        "machine_uuid": machine_uuid,
        "guest_inputs": inputs,
        "trace_contract": policy["trace_contract"],
        "locked_project_artifacts": locked,
        "sanitization": {
            "raw_paths_stored": False,
            "raw_machine_uuid_stored": False,
            "raw_identity_content_stored": False,
            "guest_artifact_content_copied": False,
            "hostname_stored": False,
        },
        "redacted_command_template": (
            f"{qemu['binary_label']} -accel {role_data['accelerator']} -cpu {role_data['cpu']} "
            "-M vmapple,uuid=<redacted> -bios <firmware> -drive <aux> -drive <disk> ..."
        ),
        "runtime_authority": {
            "manifest_policy": ".src/.configs/p1.09-manifest-policy.json",
            "promotion_policy": ".src/.configs/p1.10-promotion-policy.json",
        },
        "next_objective": "P4.02",
    }
    basis = dict(plan)
    basis.pop("classification", None)
    plan["session_fingerprint"] = sha256_bytes(canonical(basis))
    return plan


def expect_failure(policy: dict[str, Any], mutate, label: str) -> None:
    broken = copy.deepcopy(policy)
    mutate(broken)
    try:
        validate_policy(broken)
    except SessionError:
        print(f"self-check reject: PASS: {label}")
        return
    raise SessionError(f"self-check mutation was accepted: {label}")


def self_check(policy: dict[str, Any]) -> None:
    validate_policy(policy)
    expect_failure(policy, lambda d: d["privacy"].__setitem__("store_raw_local_paths", True), "raw local paths")
    expect_failure(policy, lambda d: d["runtime_parameters"]["machine_uuid"].__setitem__("store_raw_value", True), "raw machine UUID")
    expect_failure(policy, lambda d: d["roles"]["probe"].__setitem__("cpu", "max"), "probe CPU drift")
    expect_failure(policy, lambda d: d["roles"]["reference"].__setitem__("accelerator", "tcg"), "reference accelerator drift")
    expect_failure(policy, lambda d: d["trace_contract"].__setitem__("events", ["memory_region_ops_read"]), "trace contract weakening")
    expect_failure(policy, lambda d: d["requirements"].__setitem__("session_plan_is_not_runtime_evidence", False), "plan promoted to evidence")
    expect_failure(policy, lambda d: d["part_04_objectives"].append("P4.07 Scope Creep"), "P4.07 scope creep")
    expect_failure(policy, lambda d: d.__setitem__("next_objective", "P4.03"), "objective skip")
    print("P4.01 self-check: PASS")


def main() -> int:
    parser = argparse.ArgumentParser(description="AppleSilicon P4.01 runtime session provenance planner")
    parser.add_argument("--policy", default=str(DEFAULT_POLICY))
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("validate-policy")
    sub.add_parser("self-check")
    plan = sub.add_parser("plan")
    plan.add_argument("--role", choices=["probe", "reference"], required=True)
    plan.add_argument("--p3-06-manifest", required=True)
    plan.add_argument("--qemu-bin", required=True)
    plan.add_argument("--machine-uuid", required=True)
    plan.add_argument("--firmware", required=True)
    plan.add_argument("--auxiliary-storage", required=True)
    plan.add_argument("--disk", required=True)
    plan.add_argument("--machine-identity", required=True)
    plan.add_argument("--hardware-model")
    plan.add_argument("--output", required=True)
    args = parser.parse_args()

    try:
        policy = load_json(Path(args.policy))
        if args.command == "validate-policy":
            validate_policy(policy)
            validate_locked_artifacts(policy)
            print("P4.01 runtime session policy: PASS")
        elif args.command == "self-check":
            self_check(policy)
        elif args.command == "plan":
            result = build_plan(args, policy)
            out = Path(args.output)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(canonical(result))
            print(json.dumps(result, indent=2, sort_keys=True))
            print(f"P4.01 session fingerprint: {result['session_fingerprint']}")
        return 0
    except (OSError, json.JSONDecodeError, SessionError) as exc:
        print(f"P4.01 session failure: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

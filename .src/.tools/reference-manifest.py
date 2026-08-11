#!/usr/bin/env python3

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

VERSION = "0.9.0.0.0.0"
ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_POLICY = ROOT_DIR / ".src" / ".configs" / "p1.09-manifest-policy.json"
INPUT_ERROR = 2
NOT_COMPARABLE = 10
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
UUID_RE = re.compile(r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}\b")
EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
LOCAL_PATH_RES = [
    re.compile(r"/Users/[^/\s]+/"),
    re.compile(r"/home/[^/\s]+/"),
    re.compile(r"[A-Za-z]:\\\\Users\\\\[^\\\s]+\\\\"),
]
PEM_MARKERS = ("-----BEGIN PRIVATE KEY-----", "-----BEGIN RSA PRIVATE KEY-----", "-----BEGIN OPENSSH PRIVATE KEY-----")


class ManifestError(Exception):
    pass


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ManifestError(f"file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ManifestError(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ManifestError(f"top-level JSON value must be an object: {path}")
    return data


def save_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_policy(path: Path) -> dict[str, Any]:
    policy = load_json(path)
    if policy.get("schema") != 1:
        raise ManifestError(f"unsupported policy schema: {policy.get('schema')!r}")
    return policy


def sha256_file(path: Path) -> dict[str, Any]:
    digest = hashlib.sha256()
    size = 0
    try:
        with path.open("rb") as handle:
            while True:
                chunk = handle.read(1024 * 1024)
                if not chunk:
                    break
                digest.update(chunk)
                size += len(chunk)
    except OSError as exc:
        raise ManifestError(f"could not hash {path}: {exc}") from exc
    return {"sha256": digest.hexdigest(), "bytes": size}


def get_path(data: dict[str, Any], dotted: str) -> Any:
    value: Any = data
    for part in dotted.split("."):
        if not isinstance(value, dict) or part not in value:
            raise ManifestError(f"missing required field: {dotted}")
        value = value[part]
    return value


def require_dict(data: dict[str, Any], key: str) -> dict[str, Any]:
    value = data.get(key)
    if not isinstance(value, dict):
        raise ManifestError(f"{key} must be an object")
    return value


def require_string(data: dict[str, Any], key: str, *, nonempty: bool = True) -> str:
    value = data.get(key)
    if not isinstance(value, str) or (nonempty and not value.strip()):
        raise ManifestError(f"{key} must be a non-empty string")
    return value


def validate_utc(value: str, field: str) -> None:
    if not value.endswith("Z"):
        raise ManifestError(f"{field} must be UTC and end in Z")
    try:
        datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ManifestError(f"{field} is not a valid ISO-8601 UTC timestamp") from exc


def walk_values(value: Any, path: str = "") -> Iterable[tuple[str, Any]]:
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else key
            yield child_path, child
            yield from walk_values(child, child_path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            child_path = f"{path}[{index}]"
            yield child_path, child
            yield from walk_values(child, child_path)


def validate_privacy(manifest: dict[str, Any], policy: dict[str, Any]) -> None:
    forbidden_fragments = [x.lower() for x in policy["forbidden_key_fragments"]]
    for path, value in walk_values(manifest):
        leaf = re.sub(r"\[\d+\]$", "", path.split(".")[-1]).lower()
        if not path.startswith("sanitization.") and any(fragment in leaf for fragment in forbidden_fragments):
            raise ManifestError(f"forbidden sensitive key in manifest: {path}")
        if not isinstance(value, str):
            continue
        if UUID_RE.search(value) and "<redacted>" not in value:
            raise ManifestError(f"raw UUID-like value rejected at {path}")
        if EMAIL_RE.search(value):
            raise ManifestError(f"email/account-like value rejected at {path}")
        if any(marker in value for marker in PEM_MARKERS):
            raise ManifestError(f"private-key material rejected at {path}")
        if any(pattern.search(value) for pattern in LOCAL_PATH_RES):
            raise ManifestError(f"local user path rejected at {path}")


def validate_digest_object(value: Any, field: str) -> None:
    if not isinstance(value, dict):
        raise ManifestError(f"{field} must be an object")
    digest = value.get("sha256")
    size = value.get("bytes")
    if not isinstance(digest, str) or not SHA256_RE.fullmatch(digest):
        raise ManifestError(f"{field}.sha256 must be 64 lowercase hexadecimal characters")
    if not isinstance(size, int) or size < 0:
        raise ManifestError(f"{field}.bytes must be a non-negative integer")


def validate_manifest(manifest: dict[str, Any], policy: dict[str, Any]) -> None:
    if manifest.get("schema") != 1:
        raise ManifestError(f"unsupported manifest schema: {manifest.get('schema')!r}")
    if manifest.get("project_version") != policy["project_version"]:
        raise ManifestError(
            f"project_version must be {policy['project_version']}, observed {manifest.get('project_version')!r}"
        )

    role = manifest.get("role")
    if role not in policy["roles"]:
        raise ManifestError(f"role must be one of: {', '.join(sorted(policy['roles']))}")

    run = require_dict(manifest, "run")
    require_string(run, "id")
    started = require_string(run, "started_utc")
    ended = require_string(run, "ended_utc")
    require_string(run, "result")
    validate_utc(started, "run.started_utc")
    validate_utc(ended, "run.ended_utc")
    if datetime.fromisoformat(ended[:-1] + "+00:00") < datetime.fromisoformat(started[:-1] + "+00:00"):
        raise ManifestError("run.ended_utc must not be earlier than run.started_utc")

    source = require_dict(manifest, "source")
    if source.get("repository") != policy["source"]["repository"]:
        raise ManifestError("source.repository does not match the pinned research source")
    if source.get("revision") != policy["source"]["revision"]:
        raise ManifestError("source.revision does not match the pinned Inferno revision")

    host = require_dict(manifest, "host")
    for key in ("os", "architecture", "cpu_family", "virtualization"):
        require_string(host, key)

    machine = require_dict(manifest, "machine")
    if machine.get("type") != "vmapple":
        raise ManifestError("machine.type must be vmapple")
    accelerator = require_string(machine, "accelerator")
    cpu_model = require_string(machine, "cpu_model")
    expected = policy["roles"][role]
    if accelerator not in expected["accelerator"]:
        raise ManifestError(f"{role} accelerator must be one of: {', '.join(expected['accelerator'])}")
    if cpu_model not in expected["cpu_model"]:
        raise ManifestError(f"{role} cpu_model must be one of: {', '.join(expected['cpu_model'])}")
    for key in ("ram_mib", "smp"):
        value = machine.get(key)
        if not isinstance(value, int) or value <= 0:
            raise ManifestError(f"machine.{key} must be a positive integer")

    command = require_dict(manifest, "command")
    command_shape = require_string(command, "redacted_shape")
    for marker in policy["redacted_command_required_markers"]:
        if marker not in command_shape:
            raise ManifestError(f"command.redacted_shape is missing required marker: {marker}")
    if accelerator not in command_shape or cpu_model not in command_shape:
        raise ManifestError("command.redacted_shape must identify the selected accelerator and CPU model")

    trace = require_dict(manifest, "trace")
    events = trace.get("events")
    debug_items = trace.get("debug_items")
    if not isinstance(events, list) or not all(isinstance(x, str) and x for x in events):
        raise ManifestError("trace.events must be a list of non-empty strings")
    if len(events) != len(set(events)):
        raise ManifestError("trace.events must not contain duplicates")
    for event in policy["required_trace_events"]:
        if event not in events:
            raise ManifestError(f"trace.events is missing required event: {event}")
    if not isinstance(debug_items, list) or not all(isinstance(x, str) and x for x in debug_items):
        raise ManifestError("trace.debug_items must be a list of non-empty strings")
    if len(debug_items) != len(set(debug_items)):
        raise ManifestError("trace.debug_items must not contain duplicates")

    guest_inputs = require_dict(manifest, "guest_inputs")
    for name in ("firmware", "auxiliary_storage", "disk", "machine_identity"):
        if name not in guest_inputs:
            raise ManifestError(f"guest_inputs.{name} is required")
        validate_digest_object(guest_inputs[name], f"guest_inputs.{name}")
    hardware_model = guest_inputs.get("hardware_model")
    if hardware_model is not None:
        validate_digest_object(hardware_model, "guest_inputs.hardware_model")

    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list):
        raise ManifestError("artifacts must be a list")
    allowed_kinds = set(policy["allowed_artifact_kinds"])
    labels: set[str] = set()
    for index, artifact in enumerate(artifacts):
        if not isinstance(artifact, dict):
            raise ManifestError(f"artifacts[{index}] must be an object")
        kind = artifact.get("kind")
        label = artifact.get("label")
        if kind not in allowed_kinds:
            raise ManifestError(f"artifacts[{index}].kind is unsupported: {kind!r}")
        if not isinstance(label, str) or not label or "/" in label or "\\" in label:
            raise ManifestError(f"artifacts[{index}].label must be a basename, not a path")
        if label in labels:
            raise ManifestError(f"duplicate artifact label: {label}")
        labels.add(label)
        validate_digest_object(artifact, f"artifacts[{index}]")

    sanitization = require_dict(manifest, "sanitization")
    for key in ("raw_machine_identity_stored", "raw_uuid_stored", "local_paths_stored", "credentials_stored"):
        if sanitization.get(key) is not False:
            raise ManifestError(f"sanitization.{key} must be false for a versionable manifest")

    escalation = require_dict(manifest, "reference_escalation")
    if not isinstance(escalation.get("m1n1_used"), bool):
        raise ManifestError("reference_escalation.m1n1_used must be boolean")
    for key in ("m1n1_revision", "target_macos", "tracer_module_sha256"):
        value = escalation.get(key)
        if value is not None and not isinstance(value, str):
            raise ManifestError(f"reference_escalation.{key} must be string or null")
    tracer_hash = escalation.get("tracer_module_sha256")
    if tracer_hash is not None and not SHA256_RE.fullmatch(tracer_hash):
        raise ManifestError("reference_escalation.tracer_module_sha256 must be lowercase SHA-256 or null")
    if escalation["m1n1_used"] and not escalation.get("m1n1_revision"):
        raise ManifestError("m1n1_revision is required when m1n1_used is true")

    validate_privacy(manifest, policy)


def compare_manifests(reference: dict[str, Any], probe: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
    validate_manifest(reference, policy)
    validate_manifest(probe, policy)
    if reference["role"] != "reference":
        raise ManifestError("first manifest must have role=reference")
    if probe["role"] != "probe":
        raise ManifestError("second manifest must have role=probe")

    mismatches: list[dict[str, Any]] = []
    for path in policy["pair_equal_paths"]:
        ref_value = get_path(reference, path)
        probe_value = get_path(probe, path)
        if ref_value != probe_value:
            mismatches.append({"path": path, "reference": ref_value, "probe": probe_value})

    return {
        "schema": 1,
        "tool_version": VERSION,
        "comparable": not mismatches,
        "reference_run_id": reference["run"]["id"],
        "probe_run_id": probe["run"]["id"],
        "expected_differences": {
            "host": {"reference": reference["host"], "probe": probe["host"]},
            "accelerator": {"reference": reference["machine"]["accelerator"], "probe": probe["machine"]["accelerator"]},
            "cpu_model": {"reference": reference["machine"]["cpu_model"], "probe": probe["machine"]["cpu_model"]},
        },
        "contract_mismatches": mismatches,
    }


def artifact_from_arg(value: str) -> tuple[str, Path]:
    if "=" not in value:
        raise ManifestError("--artifact must be KIND=PATH")
    kind, path = value.split("=", 1)
    if not kind or not path:
        raise ManifestError("--artifact must be KIND=PATH")
    return kind, Path(path)


def collect_manifest(args: argparse.Namespace, policy: dict[str, Any]) -> dict[str, Any]:
    trace_events = args.trace_event or list(policy["required_trace_events"])
    debug_items = args.debug_item or ["guest_errors", "unimp", "int", "cpu_reset"]
    guest_inputs = {
        "firmware": sha256_file(args.firmware),
        "auxiliary_storage": sha256_file(args.auxiliary_storage),
        "disk": sha256_file(args.disk),
        "machine_identity": sha256_file(args.machine_identity),
        "hardware_model": sha256_file(args.hardware_model) if args.hardware_model else None,
    }
    artifacts: list[dict[str, Any]] = []
    for raw in args.artifact:
        kind, path = artifact_from_arg(raw)
        entry = {"kind": kind, "label": path.name, **sha256_file(path)}
        artifacts.append(entry)

    manifest = {
        "schema": 1,
        "project_version": policy["project_version"],
        "role": args.role,
        "run": {
            "id": args.run_id,
            "started_utc": args.started_utc,
            "ended_utc": args.ended_utc,
            "result": args.result,
        },
        "source": copy.deepcopy(policy["source"]),
        "host": {
            "os": args.host_os,
            "architecture": args.host_architecture,
            "cpu_family": args.host_cpu_family,
            "virtualization": args.host_virtualization,
        },
        "machine": {
            "type": "vmapple",
            "accelerator": args.accelerator,
            "cpu_model": args.cpu_model,
            "ram_mib": args.ram_mib,
            "smp": args.smp,
        },
        "command": {"redacted_shape": args.command_shape},
        "trace": {"events": trace_events, "debug_items": debug_items},
        "guest_inputs": guest_inputs,
        "artifacts": artifacts,
        "sanitization": {
            "raw_machine_identity_stored": False,
            "raw_uuid_stored": False,
            "local_paths_stored": False,
            "credentials_stored": False,
        },
        "reference_escalation": {
            "m1n1_used": bool(args.m1n1_revision),
            "m1n1_revision": args.m1n1_revision,
            "target_macos": args.target_macos,
            "tracer_module_sha256": sha256_file(args.tracer_module)["sha256"] if args.tracer_module else None,
        },
    }
    validate_manifest(manifest, policy)
    return manifest


def write_pair_markdown(report: dict[str, Any], path: Path) -> None:
    lines = [
        "# P1.09 Reference/Probe Pair Check",
        "",
        f"Tool version: `{report['tool_version']}`",
        f"Reference run: `{report['reference_run_id']}`",
        f"Probe run: `{report['probe_run_id']}`",
        "",
        f"Comparable: **{str(report['comparable']).lower()}**",
        "",
        "## Expected differences",
        "",
        f"- Accelerator: `{report['expected_differences']['accelerator']['reference']}` → `{report['expected_differences']['accelerator']['probe']}`",
        f"- CPU model: `{report['expected_differences']['cpu_model']['reference']}` → `{report['expected_differences']['cpu_model']['probe']}`",
        "- Host metadata may differ and is recorded, not normalized into equality.",
        "",
        "## Contract mismatches",
        "",
    ]
    if report["contract_mismatches"]:
        for mismatch in report["contract_mismatches"]:
            lines.append(f"- `{mismatch['path']}`")
            lines.append(f"  - reference: `{json.dumps(mismatch['reference'], sort_keys=True)}`")
            lines.append(f"  - probe: `{json.dumps(mismatch['probe'], sort_keys=True)}`")
    else:
        lines.append("None. The manifests satisfy the P1.09 pairing contract.")
    lines.extend(["", "This report establishes comparability only. It does not claim a guest divergence.", ""])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def self_check(policy: dict[str, Any]) -> None:
    with tempfile.TemporaryDirectory(prefix="applesilicon-p109-") as temp:
        root = Path(temp)
        files = {}
        for name, content in {
            "firmware": b"synthetic firmware\n",
            "auxiliary": b"synthetic auxiliary\n",
            "disk": b"synthetic disk\n",
            "identity": b"synthetic identity\n",
            "hardware": b"synthetic hardware model\n",
            "serial": b"synthetic serial log\n",
        }.items():
            path = root / f"{name}.fixture"
            path.write_bytes(content)
            files[name] = path

        def make(role: str) -> dict[str, Any]:
            accel = "hvf" if role == "reference" else "tcg"
            cpu = "host" if role == "reference" else "max"
            return {
                "schema": 1,
                "project_version": VERSION,
                "role": role,
                "run": {"id": f"self-{role}", "started_utc": "2026-08-11T00:00:00Z", "ended_utc": "2026-08-11T00:00:01Z", "result": "synthetic"},
                "source": copy.deepcopy(policy["source"]),
                "host": {"os": "synthetic", "architecture": "arm64" if role == "reference" else "x86_64", "cpu_family": "synthetic", "virtualization": accel.upper()},
                "machine": {"type": "vmapple", "accelerator": accel, "cpu_model": cpu, "ram_mib": 4096, "smp": 4},
                "command": {"redacted_shape": f"qemu-system-aarch64 -accel {accel} -cpu {cpu} -M vmapple,uuid=<redacted> -m 4096 -smp 4"},
                "trace": {"events": list(policy["required_trace_events"]), "debug_items": ["guest_errors", "unimp", "int", "cpu_reset"]},
                "guest_inputs": {
                    "firmware": sha256_file(files["firmware"]),
                    "auxiliary_storage": sha256_file(files["auxiliary"]),
                    "disk": sha256_file(files["disk"]),
                    "machine_identity": sha256_file(files["identity"]),
                    "hardware_model": sha256_file(files["hardware"]),
                },
                "artifacts": [{"kind": "serial_log", "label": files["serial"].name, **sha256_file(files["serial"])}],
                "sanitization": {"raw_machine_identity_stored": False, "raw_uuid_stored": False, "local_paths_stored": False, "credentials_stored": False},
                "reference_escalation": {"m1n1_used": False, "m1n1_revision": None, "target_macos": None, "tracer_module_sha256": None},
            }

        reference = make("reference")
        probe = make("probe")
        validate_manifest(reference, policy)
        validate_manifest(probe, policy)
        report = compare_manifests(reference, probe, policy)
        if not report["comparable"]:
            raise ManifestError("self-check comparable pair was rejected")

        changed = copy.deepcopy(probe)
        changed["guest_inputs"]["disk"]["sha256"] = "f" * 64
        changed_report = compare_manifests(reference, changed, policy)
        if changed_report["comparable"]:
            raise ManifestError("self-check failed to detect guest input mismatch")
        if changed_report["contract_mismatches"][0]["path"] != "guest_inputs.disk.sha256":
            raise ManifestError("self-check reported unexpected mismatch path")

        unsafe = copy.deepcopy(reference)
        unsafe["command"]["redacted_shape"] = "qemu-system-aarch64 -accel hvf -cpu host -M vmapple,uuid=123e4567-e89b-12d3-a456-426614174000"
        try:
            validate_manifest(unsafe, policy)
        except ManifestError:
            pass
        else:
            raise ManifestError("self-check accepted a raw UUID")

        bad_events = copy.deepcopy(reference)
        bad_events["trace"]["events"] = ["memory_region_ops_read"]
        try:
            validate_manifest(bad_events, policy)
        except ManifestError:
            pass
        else:
            raise ManifestError("self-check accepted a missing required trace event")


def run_validate(args: argparse.Namespace) -> int:
    policy = load_policy(args.policy)
    manifest = load_json(args.manifest)
    validate_manifest(manifest, policy)
    print(f"valid=true role={manifest['role']} run_id={manifest['run']['id']}")
    return 0


def run_compare(args: argparse.Namespace) -> int:
    policy = load_policy(args.policy)
    reference = load_json(args.reference)
    probe = load_json(args.probe)
    report = compare_manifests(reference, probe, policy)
    if args.report_json:
        save_json(args.report_json, report)
    if args.report_md:
        write_pair_markdown(report, args.report_md)
    print(f"comparable={str(report['comparable']).lower()}")
    print(f"contract_mismatches={len(report['contract_mismatches'])}")
    return 0 if report["comparable"] else NOT_COMPARABLE


def run_collect(args: argparse.Namespace) -> int:
    policy = load_policy(args.policy)
    manifest = collect_manifest(args, policy)
    save_json(args.output, manifest)
    print(f"manifest={args.output}")
    print(f"role={manifest['role']}")
    print(f"artifacts={len(manifest['artifacts'])}")
    return 0


def run_self_check(args: argparse.Namespace) -> int:
    policy = load_policy(args.policy)
    self_check(policy)
    print("P1.09 self-check: PASS")
    print("checks=privacy,role-contract,input-hashes,pairing,required-trace-events")
    return 0


def add_common_collect(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--role", required=True, choices=("reference", "probe"))
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--started-utc", required=True)
    parser.add_argument("--ended-utc", required=True)
    parser.add_argument("--result", required=True)
    parser.add_argument("--host-os", required=True)
    parser.add_argument("--host-architecture", required=True)
    parser.add_argument("--host-cpu-family", required=True)
    parser.add_argument("--host-virtualization", required=True)
    parser.add_argument("--accelerator", required=True)
    parser.add_argument("--cpu-model", required=True)
    parser.add_argument("--ram-mib", required=True, type=int)
    parser.add_argument("--smp", required=True, type=int)
    parser.add_argument("--command-shape", required=True)
    parser.add_argument("--trace-event", action="append", default=[])
    parser.add_argument("--debug-item", action="append", default=[])
    parser.add_argument("--firmware", required=True, type=Path)
    parser.add_argument("--auxiliary-storage", required=True, type=Path)
    parser.add_argument("--disk", required=True, type=Path)
    parser.add_argument("--machine-identity", required=True, type=Path)
    parser.add_argument("--hardware-model", type=Path)
    parser.add_argument("--artifact", action="append", default=[])
    parser.add_argument("--m1n1-revision")
    parser.add_argument("--target-macos")
    parser.add_argument("--tracer-module", type=Path)
    parser.add_argument("--output", required=True, type=Path)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="AppleSilicon P1.09 reference/probe evidence manifest tool")
    parser.add_argument("--version", action="version", version=f"AppleSilicon reference manifest {VERSION}")
    sub = parser.add_subparsers(dest="command", required=True)

    validate = sub.add_parser("validate", help="validate one versionable evidence manifest")
    validate.add_argument("manifest", type=Path)
    validate.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    validate.set_defaults(func=run_validate)

    compare = sub.add_parser("compare", help="check whether reference/probe manifests satisfy the pairing contract")
    compare.add_argument("reference", type=Path)
    compare.add_argument("probe", type=Path)
    compare.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    compare.add_argument("--report-json", type=Path)
    compare.add_argument("--report-md", type=Path)
    compare.set_defaults(func=run_compare)

    collect = sub.add_parser("collect", help="hash local inputs/artifacts and create a sanitized manifest")
    collect.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    add_common_collect(collect)
    collect.set_defaults(func=run_collect)

    selfcheck = sub.add_parser("self-check", help="run deterministic synthetic P1.09 checks")
    selfcheck.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    selfcheck.set_defaults(func=run_self_check)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return args.func(args)
    except ManifestError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return INPUT_ERROR
    except OSError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return INPUT_ERROR


if __name__ == "__main__":
    raise SystemExit(main())

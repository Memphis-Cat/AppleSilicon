#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
SAFE_GLOBAL_RE = re.compile(r"^vmapple-cfg\.(serial|model|soc_name|mac-en0|mac-en1|mac-wifi0|mac-bt0|run_installer1|run_installer2)=(.*)$")
EXPECTED_P302_VERSION = "3.1.0.0.0.0"
EXPECTED_INFERNO = "cc4302a99167abec69b714cfd00c38caece7e7de"


class IntegrityError(RuntimeError):
    pass


def require(value: bool, message: str) -> None:
    if not value:
        raise IntegrityError(message)


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise IntegrityError(f"could not read JSON {path}: {exc}") from exc
    require(isinstance(value, dict), f"top-level JSON must be an object: {path}")
    return value


def canonical(data: Any) -> bytes:
    return (json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                h.update(chunk)
    except OSError as exc:
        raise IntegrityError(f"could not hash {path}: {exc}") from exc
    return h.hexdigest()


def parse_machine_id(value: Any) -> int:
    if isinstance(value, bool):
        raise IntegrityError("VMApple machine id cannot be boolean")
    if isinstance(value, int):
        parsed = value
    elif isinstance(value, str):
        raw = value.strip()
        require(raw != "", "VMApple machine id cannot be empty")
        try:
            parsed = int(raw, 0)
        except ValueError as exc:
            raise IntegrityError("VMApple machine id must be decimal or 0x-prefixed uint64") from exc
    else:
        raise IntegrityError("VMApple machine id must be an integer or string")
    require(0 <= parsed <= 0xFFFFFFFFFFFFFFFF, "VMApple machine id must fit uint64")
    return parsed


def canonical_machine_id(value: Any) -> str:
    return str(parse_machine_id(value))


def machine_id_digest(value: Any) -> dict[str, Any]:
    normalized = canonical_machine_id(value)
    encoded = normalized.encode("ascii")
    return {
        "sha256": sha256_bytes(encoded),
        "normalized_bytes": len(encoded),
        "encoding": "uint64_decimal",
        "semantic": "vmapple_sdom_ecid",
        "raw_value_stored": False,
    }


def verify_generated_fingerprint(data: dict[str, Any], field: str, *, exclude: tuple[str, ...] = ("classification",)) -> str:
    observed = data.get(field)
    require(isinstance(observed, str) and SHA256_RE.fullmatch(observed) is not None,
            f"{field} is not a lowercase SHA-256")
    basis = dict(data)
    basis.pop(field, None)
    for name in exclude:
        basis.pop(name, None)
    expected = sha256_bytes(canonical(basis))
    require(observed == expected, f"{field} does not reproduce: expected {expected}, observed {observed}")
    return observed


def validate_p2_manifest(data: dict[str, Any]) -> str:
    require(data.get("classification") == "P2_06_INTEGRATION_PASS", "P2.06 classification mismatch")
    require(data.get("part_status") == "closed_implementation_complete", "P2.06 part is not closed")
    require(data.get("guest_execution") is False, "P2.06 unexpectedly records guest execution")
    prepared = data.get("prepared_source", {})
    require(prepared.get("inferno_revision") == EXPECTED_INFERNO, "P2.06 Inferno revision drift")
    require(prepared.get("live_sysreg_policy_count") == 0, "P2.06 live Apple sysreg policy count must remain zero")
    return verify_generated_fingerprint(data, "integration_fingerprint")


def validate_p3_manifest(data: dict[str, Any], p2_data: dict[str, Any] | None = None) -> str:
    require(data.get("classification") == "P3_06_INTEGRATION_PASS", "P3.06 classification mismatch")
    require(data.get("part_status") == "closed_implementation_complete", "P3.06 part is not closed")
    require(data.get("guest_execution") is False, "P3.06 unexpectedly records guest execution")
    require(data.get("next_part") == "Part 04" and data.get("next_objective") == "P4.01",
            "P3.06 Part 04 transition drift")
    observed = verify_generated_fingerprint(data, "platform_integration_fingerprint")
    if p2_data is not None:
        p2_fp = validate_p2_manifest(p2_data)
        embedded = data.get("p2_06", {})
        require(embedded.get("integration_fingerprint") == p2_fp,
                "P3.06 embedded P2.06 fingerprint differs from supplied P2.06 manifest")
    return observed


def validate_compiled_identity(data: dict[str, Any], *, expected_machine_id: Any | None = None,
                               allow_example: bool = False) -> list[str]:
    require(data.get("schema") == 1, "compiled identity schema mismatch")
    require(data.get("classification") == "P3_02_IDENTITY_PROFILE_COMPILED",
            "machine identity must be a compiled P3.02 identity artifact")
    require(data.get("project_version") == EXPECTED_P302_VERSION, "compiled identity version mismatch")
    require(data.get("objective") == "P3.02", "compiled identity objective mismatch")
    require(data.get("guest_execution") is False, "compiled identity unexpectedly records guest execution")
    require(data.get("machine") == "vmapple", "compiled identity machine mismatch")
    require(isinstance(data.get("synthetic"), bool), "compiled identity synthetic flag invalid")
    require(isinstance(data.get("example_only"), bool), "compiled identity example_only flag invalid")
    if not allow_example:
        require(data.get("example_only") is False, "example-only P3.02 identity cannot be used for a real runtime session")

    machine_id = parse_machine_id(data.get("machine_uuid_decimal"))
    if expected_machine_id is not None:
        require(machine_id == parse_machine_id(expected_machine_id),
                "compiled identity machine id differs from runtime VMApple machine id")

    observed = data.get("compiled_fingerprint")
    require(isinstance(observed, str) and SHA256_RE.fullmatch(observed) is not None,
            "compiled identity fingerprint invalid")
    basis = dict(data)
    basis.pop("compiled_fingerprint", None)
    expected = sha256_bytes(canonical(basis))
    require(observed == expected, "compiled identity fingerprint does not reproduce")

    require(data.get("machine_derived_fields_not_overridden") == ["nr-cpus", "ram-size", "rnd", "cpu_ids"],
            "compiled identity overrides protected machine-derived fields")
    argv = data.get("qemu_argv")
    require(isinstance(argv, list) and all(isinstance(x, str) for x in argv), "compiled identity qemu_argv invalid")
    require(len(argv) >= 2 and argv[:2] == ["-M", f"vmapple,uuid={machine_id}"],
            "compiled identity machine argument does not match its machine id")
    rest = argv[2:]
    require(len(rest) % 2 == 0, "compiled identity global argument list is malformed")
    globals_out: list[str] = []
    seen: set[str] = set()
    for index in range(0, len(rest), 2):
        require(rest[index] == "-global", "compiled identity may only append -global vmapple-cfg properties")
        spec = rest[index + 1]
        match = SAFE_GLOBAL_RE.fullmatch(spec)
        require(match is not None, f"compiled identity contains unsupported global: {spec}")
        prop, value = match.groups()
        require(prop not in seen, f"compiled identity duplicates property: {prop}")
        seen.add(prop)
        require("\n" not in value and "\r" not in value and "\x00" not in value,
                f"compiled identity property contains control characters: {prop}")
        globals_out.extend(["-global", spec])

    recorded = data.get("overridden_device_properties")
    require(isinstance(recorded, list) and all(isinstance(x, str) for x in recorded),
            "compiled identity overridden_device_properties invalid")
    require(sorted(recorded) == sorted(seen),
            "compiled identity overridden_device_properties does not match qemu_argv")
    require("run_installer1" in seen and "run_installer2" in seen,
            "compiled identity must explicitly lock both installer flags")
    return globals_out


def validate_compiled_identity_file(path: Path, *, expected_machine_id: Any | None = None,
                                    allow_example: bool = False) -> tuple[dict[str, Any], list[str]]:
    data = load_json(path)
    globals_out = validate_compiled_identity(data, expected_machine_id=expected_machine_id, allow_example=allow_example)
    return data, globals_out


def main() -> int:
    parser = argparse.ArgumentParser(description="AppleSilicon shared runtime integrity checks")
    sub = parser.add_subparsers(dest="command", required=True)

    mid = sub.add_parser("machine-id")
    mid.add_argument("value")

    identity = sub.add_parser("identity")
    identity.add_argument("--compiled", required=True, type=Path)
    identity.add_argument("--machine-id")
    identity.add_argument("--allow-example", action="store_true")
    identity.add_argument("--emit-globals", action="store_true")

    p2 = sub.add_parser("verify-p2")
    p2.add_argument("manifest", type=Path)

    p3 = sub.add_parser("verify-p3")
    p3.add_argument("manifest", type=Path)
    p3.add_argument("--p2", type=Path)

    args = parser.parse_args()
    try:
        if args.command == "machine-id":
            print(canonical_machine_id(args.value))
        elif args.command == "identity":
            data, globals_out = validate_compiled_identity_file(
                args.compiled, expected_machine_id=args.machine_id, allow_example=args.allow_example)
            if args.emit_globals:
                for item in globals_out:
                    print(item)
            else:
                print(json.dumps({
                    "classification": "RUNTIME_IDENTITY_VALID",
                    "machine_id_decimal": data["machine_uuid_decimal"],
                    "compiled_fingerprint": data["compiled_fingerprint"],
                    "global_argument_count": len(globals_out),
                }, sort_keys=True))
        elif args.command == "verify-p2":
            print(validate_p2_manifest(load_json(args.manifest)))
        elif args.command == "verify-p3":
            p2_data = load_json(args.p2) if args.p2 else None
            print(validate_p3_manifest(load_json(args.manifest), p2_data))
        return 0
    except IntegrityError as exc:
        print(f"runtime integrity failure: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

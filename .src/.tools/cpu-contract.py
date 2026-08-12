#!/usr/bin/env python3

from __future__ import annotations

import argparse
import copy
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

VERSION = "2.0.0.0.0.0"
ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_CONTRACT = ROOT_DIR / ".src" / ".configs" / "p2.01-cpu-contract.json"
INPUT_ERROR = 2

REQUIRED_SOURCES = {
    "xnu_proc_reg": {
        "repository": "apple-oss-distributions/xnu",
        "revision": "f6217f891ac0bb64f3d375211650a4c1ff8ca1ea",
        "path": "osfmk/arm64/proc_reg.h",
        "blob_sha": "2b6d7231cb1db4ee4f1a26e4775b5284de332acf",
    },
    "qemu_cpregs": {
        "repository": "qemu/qemu",
        "revision": "3e3ccab106f879b1512f8e0d51a827dd4de30e22",
        "path": "target/arm/cpregs.h",
        "blob_sha": "391c0e322b7097ccf05b9fc2edc04b0e5cc821e7",
    },
    "m1n1_cpu_regs": {
        "repository": "AsahiLinux/m1n1",
        "revision": "06a4601a351ebfd1abb6abba9a44c34e40d94776",
        "path": "src/cpu_regs.h",
        "blob_sha": "f40cc8a9e507418e204522be121ac262b314ca41",
    },
    "inferno": {
        "repository": "ChefKissInc/Inferno",
        "revision": "cc4302a99167abec69b714cfd00c38caece7e7de",
    },
}

ALLOWED_GROUPS = {
    "hid_ehid",
    "timer",
    "amx",
    "gxf_sprr",
    "pauth_control",
    "control_hypervisor",
}
ALLOWED_CLASSES = {"apple_implementation_defined"}
ALLOWED_ACCESS = {"read", "write"}


class ContractError(Exception):
    pass


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ContractError(f"contract not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ContractError(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ContractError("contract root must be a JSON object")
    return value


def canonical_name(encoding: dict[str, Any]) -> str:
    return (
        f"S{encoding['op0']}_{encoding['op1']}_"
        f"C{encoding['crn']}_C{encoding['crm']}_{encoding['op2']}"
    )


def require_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise ContractError(f"{field} must be a non-empty string")
    return value


def validate_source_locks(contract: dict[str, Any]) -> None:
    sources = contract.get("sources")
    if not isinstance(sources, dict):
        raise ContractError("sources must be an object")

    for source_name, required in REQUIRED_SOURCES.items():
        actual = sources.get(source_name)
        if not isinstance(actual, dict):
            raise ContractError(f"missing source lock: {source_name}")
        for key, expected in required.items():
            if actual.get(key) != expected:
                raise ContractError(
                    f"source lock mismatch: {source_name}.{key}: "
                    f"expected {expected!r}, observed {actual.get(key)!r}"
                )


def validate_encoding(encoding: Any, field: str) -> tuple[int, int, int, int, int]:
    if not isinstance(encoding, dict):
        raise ContractError(f"{field} must be an object")

    ranges = {
        "op0": (0, 3),
        "op1": (0, 7),
        "crn": (0, 15),
        "crm": (0, 15),
        "op2": (0, 7),
    }
    values: list[int] = []
    for key in ("op0", "op1", "crn", "crm", "op2"):
        value = encoding.get(key)
        low, high = ranges[key]
        if not isinstance(value, int) or isinstance(value, bool):
            raise ContractError(f"{field}.{key} must be an integer")
        if not low <= value <= high:
            raise ContractError(
                f"{field}.{key} out of range: {value}; expected {low}..{high}"
            )
        values.append(value)
    return tuple(values)  # type: ignore[return-value]


def validate_contract(contract: dict[str, Any]) -> None:
    if contract.get("schema") != 1:
        raise ContractError(f"unsupported schema: {contract.get('schema')!r}")
    if contract.get("project_version") != VERSION:
        raise ContractError(
            f"project_version must be {VERSION}, observed {contract.get('project_version')!r}"
        )
    if contract.get("part") != "Part 02":
        raise ContractError("part must be 'Part 02'")
    if contract.get("objective") != "P2.01":
        raise ContractError("objective must be P2.01")
    if contract.get("status") != "inventory_only":
        raise ContractError("P2.01 status must be inventory_only")
    if contract.get("next_objective") != "P2.02":
        raise ContractError("P2.01 next_objective must be P2.02")

    validate_source_locks(contract)
    source_names = set(contract["sources"])

    rules = contract.get("rules")
    if not isinstance(rules, dict):
        raise ContractError("rules must be an object")
    if rules.get("runtime_priority_values") != ["unknown"]:
        raise ContractError("P2.01 allows only runtime_priority=unknown")
    if rules.get("implementation_state_values") != ["inventory_only"]:
        raise ContractError("P2.01 allows only implementation_state=inventory_only")
    if rules.get("no_register_is_required_until_evidence_promotes_it") is not True:
        raise ContractError("contract must prohibit unproven register requirements")
    if rules.get("no_default_values_are_invented") is not True:
        raise ContractError("contract must prohibit invented register defaults")

    features = contract.get("features")
    if not isinstance(features, list) or not features:
        raise ContractError("features must be a non-empty list")
    feature_names: set[str] = set()
    for index, feature in enumerate(features):
        if not isinstance(feature, dict):
            raise ContractError(f"features[{index}] must be an object")
        name = require_string(feature.get("name"), f"features[{index}].name")
        require_string(feature.get("class"), f"features[{index}].class")
        if name in feature_names:
            raise ContractError(f"duplicate feature name: {name}")
        feature_names.add(name)
        if feature.get("runtime_priority") != "unknown":
            raise ContractError(f"feature {name} runtime_priority must remain unknown")
        if feature.get("implementation_state") != "inventory_only":
            raise ContractError(f"feature {name} implementation_state must be inventory_only")
        evidence = feature.get("source_evidence")
        if not isinstance(evidence, list) or not evidence:
            raise ContractError(f"feature {name} must have source_evidence")
        for evidence_index, source in enumerate(evidence):
            require_string(source, f"feature {name}.source_evidence[{evidence_index}]")
        unknown_sources = sorted(set(evidence) - source_names)
        if unknown_sources:
            raise ContractError(
                f"feature {name} references unknown source(s): {', '.join(unknown_sources)}"
            )

    registers = contract.get("registers")
    if not isinstance(registers, list) or not registers:
        raise ContractError("registers must be a non-empty list")

    names: set[str] = set()
    encodings: dict[tuple[int, int, int, int, int], str] = {}
    for index, entry in enumerate(registers):
        if not isinstance(entry, dict):
            raise ContractError(f"registers[{index}] must be an object")
        prefix = f"registers[{index}]"
        name = require_string(entry.get("name"), f"{prefix}.name")
        if name in names:
            raise ContractError(f"duplicate register name: {name}")
        names.add(name)

        encoding = entry.get("encoding")
        encoded = validate_encoding(encoding, f"{prefix}.encoding")
        if encoded in encodings:
            raise ContractError(
                f"duplicate register encoding {encoded}: {encodings[encoded]} and {name}"
            )
        encodings[encoded] = name

        expected_name = canonical_name(encoding)
        if entry.get("architectural_name") != expected_name:
            raise ContractError(
                f"{name} architectural_name mismatch: expected {expected_name}, "
                f"observed {entry.get('architectural_name')!r}"
            )

        if entry.get("class") not in ALLOWED_CLASSES:
            raise ContractError(f"{name} has unsupported class: {entry.get('class')!r}")
        if entry.get("group") not in ALLOWED_GROUPS:
            raise ContractError(f"{name} has unsupported group: {entry.get('group')!r}")
        if entry.get("runtime_priority") != "unknown":
            raise ContractError(f"{name} runtime_priority must remain unknown in P2.01")
        if entry.get("implementation_state") != "inventory_only":
            raise ContractError(f"{name} implementation_state must be inventory_only")
        if entry.get("xnu_relevance") not in {"unknown"}:
            raise ContractError(f"{name} xnu_relevance must remain unknown in P2.01")

        access = entry.get("observed_access")
        if not isinstance(access, list) or any(item not in ALLOWED_ACCESS for item in access):
            raise ContractError(f"{name} observed_access contains unsupported values")
        if len(access) != len(set(access)):
            raise ContractError(f"{name} observed_access contains duplicates")

        evidence = entry.get("source_evidence")
        if not isinstance(evidence, list) or not evidence:
            raise ContractError(f"{name} must have source_evidence")
        for evidence_index, item in enumerate(evidence):
            if not isinstance(item, dict):
                raise ContractError(
                    f"{name} source_evidence[{evidence_index}] must be an object"
                )
            source = item.get("source")
            if source not in source_names:
                raise ContractError(f"{name} references unknown evidence source: {source!r}")
            require_string(item.get("scope"), f"{name}.source_evidence[{evidence_index}].scope")

    deferred = contract.get("deferred_families")
    if not isinstance(deferred, list):
        raise ContractError("deferred_families must be a list")
    deferred_names: set[str] = set()
    for index, item in enumerate(deferred):
        if not isinstance(item, dict):
            raise ContractError(f"deferred_families[{index}] must be an object")
        name = require_string(item.get("name"), f"deferred_families[{index}].name")
        require_string(item.get("reason"), f"deferred_families[{index}].reason")
        if name in deferred_names:
            raise ContractError(f"duplicate deferred family: {name}")
        deferred_names.add(name)


def summary(contract: dict[str, Any]) -> dict[str, Any]:
    validate_contract(contract)
    group_counts = Counter(item["group"] for item in contract["registers"])
    feature_counts = Counter(item["class"] for item in contract["features"])
    return {
        "project_version": contract["project_version"],
        "objective": contract["objective"],
        "register_count": len(contract["registers"]),
        "register_groups": dict(sorted(group_counts.items())),
        "feature_count": len(contract["features"]),
        "feature_classes": dict(sorted(feature_counts.items())),
        "deferred_family_count": len(contract["deferred_families"]),
        "next_objective": contract["next_objective"],
    }


def lookup(contract: dict[str, Any], name: str) -> dict[str, Any]:
    validate_contract(contract)
    wanted = name.upper()
    for entry in contract["registers"]:
        if entry["name"].upper() == wanted:
            return entry
    raise ContractError(f"register not found: {name}")


def expect_rejected(contract: dict[str, Any], label: str) -> None:
    try:
        validate_contract(contract)
    except ContractError:
        return
    raise ContractError(f"self-check failed: validator accepted {label}")


def self_check(contract: dict[str, Any]) -> None:
    validate_contract(contract)

    duplicate_name = copy.deepcopy(contract)
    duplicate_name["registers"][1]["name"] = duplicate_name["registers"][0]["name"]
    expect_rejected(duplicate_name, "duplicate register name")

    duplicate_encoding = copy.deepcopy(contract)
    duplicate_encoding["registers"][1]["encoding"] = copy.deepcopy(
        duplicate_encoding["registers"][0]["encoding"]
    )
    duplicate_encoding["registers"][1]["architectural_name"] = duplicate_encoding["registers"][0][
        "architectural_name"
    ]
    expect_rejected(duplicate_encoding, "duplicate register encoding")

    bad_range = copy.deepcopy(contract)
    bad_range["registers"][0]["encoding"]["op2"] = 8
    expect_rejected(bad_range, "out-of-range op2")

    bad_priority = copy.deepcopy(contract)
    bad_priority["registers"][0]["runtime_priority"] = "required"
    expect_rejected(bad_priority, "fabricated runtime priority")

    premature = copy.deepcopy(contract)
    premature["registers"][0]["implementation_state"] = "implemented"
    expect_rejected(premature, "premature implementation state")

    bad_name = copy.deepcopy(contract)
    bad_name["registers"][0]["architectural_name"] = "S0_0_C0_C0_0"
    expect_rejected(bad_name, "architectural name mismatch")

    bad_source = copy.deepcopy(contract)
    bad_source["registers"][0]["source_evidence"][0]["source"] = "forum_post"
    expect_rejected(bad_source, "unknown evidence source")

    missing_feature_class = copy.deepcopy(contract)
    missing_feature_class["features"][0].pop("class", None)
    expect_rejected(missing_feature_class, "missing feature class")

    invalid_feature_evidence = copy.deepcopy(contract)
    invalid_feature_evidence["features"][0]["source_evidence"][0] = {"source": "xnu_proc_reg"}
    expect_rejected(invalid_feature_evidence, "non-string feature evidence")


def run_validate(args: argparse.Namespace) -> int:
    contract = load_json(args.contract)
    validate_contract(contract)
    print("valid=true")
    print(f"version={contract['project_version']}")
    print(f"objective={contract['objective']}")
    print(f"registers={len(contract['registers'])}")
    return 0


def run_summary(args: argparse.Namespace) -> int:
    contract = load_json(args.contract)
    print(json.dumps(summary(contract), indent=2, sort_keys=True))
    return 0


def run_lookup(args: argparse.Namespace) -> int:
    contract = load_json(args.contract)
    print(json.dumps(lookup(contract, args.name), indent=2, sort_keys=True))
    return 0


def run_self_check(args: argparse.Namespace) -> int:
    contract = load_json(args.contract)
    self_check(contract)
    print("P2.01 self-check: PASS")
    print(
        "checks=source-locks,encoding-ranges,unique-names,unique-encodings,"
        "unknown-priority,inventory-state,evidence-resolution,feature-shape"
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="AppleSilicon P2.01 Apple CPU contract inventory validator"
    )
    parser.add_argument("--version", action="version", version=f"AppleSilicon CPU contract {VERSION}")
    sub = parser.add_subparsers(dest="command", required=True)

    for name, func, help_text in (
        ("validate", run_validate, "validate the P2.01 machine-readable CPU contract"),
        ("summary", run_summary, "print a deterministic contract summary"),
        ("self-check", run_self_check, "run in-memory negative/positive validation checks"),
    ):
        command = sub.add_parser(name, help=help_text)
        command.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
        command.set_defaults(func=func)

    lookup_parser = sub.add_parser("lookup", help="print one register contract entry")
    lookup_parser.add_argument("name")
    lookup_parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    lookup_parser.set_defaults(func=run_lookup)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return args.func(args)
    except ContractError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return INPUT_ERROR
    except OSError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return INPUT_ERROR


if __name__ == "__main__":
    raise SystemExit(main())

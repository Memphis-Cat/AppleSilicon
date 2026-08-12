#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONTRACT = ROOT / ".src" / ".configs" / "p3.01-platform-contract.json"
EXPECTED_VERSION = "3.0.0.0.0.0"
EXPECTED_INFERNO = "cc4302a99167abec69b714cfd00c38caece7e7de"
EXPECTED_XNU = "f6217f891ac0bb64f3d375211650a4c1ff8ca1ea"
EXPECTED_XNU_BLOB = "08b35780a1dcf187af2ced7839d7045afb433de7"

class ContractError(RuntimeError):
    pass

def require(value: bool, message: str) -> None:
    if not value:
        raise ContractError(message)

def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))

def validate(data: dict[str, Any]) -> None:
    require(data.get("schema") == 1, "schema must be 1")
    require(data.get("project_version") == EXPECTED_VERSION, "project version mismatch")
    require(data.get("part") == "Part 03", "part mismatch")
    require(data.get("objective") == "P3.01", "objective mismatch")
    require(data.get("next_objective") == "P3.02", "next objective must be P3.02")

    scope = data.get("scope", {})
    require(scope.get("machine") == "vmapple", "machine must be vmapple")
    require(scope.get("accelerator_focus") == "tcg", "accelerator focus must be tcg")
    require(scope.get("cpu_contract_owner") == "Part 02", "CPU contract must remain owned by Part 02")
    require(scope.get("guest_runtime_deferred") is True, "guest runtime must remain deferred")

    locks = data.get("source_locks", {})
    inferno = locks.get("inferno", {})
    require(inferno.get("revision") == EXPECTED_INFERNO, "Inferno revision lock drift")
    require(len(inferno.get("files", {})) >= 7, "Inferno file lock set incomplete")
    xnu = locks.get("xnu_vmapple", {})
    require(xnu.get("revision") == EXPECTED_XNU, "XNU revision lock drift")
    require(xnu.get("blob_sha") == EXPECTED_XNU_BLOB, "XNU VMAPPLE blob lock drift")

    ownership = data.get("ownership_classes", [])
    require(ownership == [
        "generic_qemu",
        "vmapple_specific",
        "host_framework_dependent",
        "unknown_requires_evidence",
    ], "ownership class set/order drift")

    runtime_values = set(data.get("runtime_requirement_values", []))
    actions = set(data.get("action_values", []))
    require("implement" not in actions, "P3.01 must not expose an automatic implement action")
    require(actions == {"preserve", "validate", "investigate", "defer"}, "action set drift")

    objectives = data.get("part_03_objectives", [])
    require(len(objectives) == 6, "Part 03 must contain exactly six objectives")
    require(objectives[0].startswith("P3.01 "), "Part 03 must start at P3.01")
    require(objectives[-1].startswith("P3.06 "), "Part 03 must end at P3.06")
    require(not any(item.startswith("P3.07") for item in objectives), "P3.07 is forbidden")

    components = data.get("components", [])
    require(len(components) >= 15, "platform inventory is unexpectedly small")
    ids: set[str] = set()
    owner_counts: dict[str, int] = {}
    for item in components:
        cid = item.get("id")
        require(isinstance(cid, str) and cid, "component id missing")
        require(cid not in ids, f"duplicate component id: {cid}")
        ids.add(cid)
        category = item.get("category")
        require(isinstance(category, str) and category, f"category missing for {cid}")
        own = item.get("ownership")
        require(own in ownership, f"invalid ownership for {cid}: {own}")
        owner_counts[own] = owner_counts.get(own, 0) + 1
        project_owner = item.get("project_owner")
        require(project_owner in {"P3.02", "P3.03", "P3.04", "P3.05", "P3.06"},
                f"invalid project owner for {cid}: {project_owner}")
        require(item.get("runtime_requirement") in runtime_values,
                f"invalid runtime requirement for {cid}")
        require(item.get("action") in actions, f"invalid action for {cid}")
        evidence = item.get("evidence")
        require(isinstance(evidence, list) and evidence, f"evidence missing for {cid}")
        require(item.get("baseline_state"), f"baseline state missing for {cid}")
        require(item.get("notes"), f"notes missing for {cid}")

        if own == "generic_qemu":
            require(item["action"] in {"preserve", "validate"},
                    f"generic QEMU component {cid} cannot be pre-classified for replacement")
        if own == "host_framework_dependent":
            require(item["action"] in {"investigate", "defer"},
                    f"host-framework component {cid} must remain deferred/investigative")
        if own == "unknown_requires_evidence":
            require(item["action"] in {"investigate", "defer"},
                    f"unknown component {cid} must remain evidence-gated")

    for required in (
        "configuration_region", "gicv3", "architectural_virtual_timer",
        "pl011_uart", "bdif_boot_backdoor", "vmapple_virtio_block",
        "pcie_gpex", "apple_pvg_graphics",
    ):
        require(required in ids, f"required platform component missing: {required}")

    rules = data.get("rules", {})
    for key in (
        "apple_specific_does_not_imply_missing",
        "generic_qemu_is_preserved_until_evidence_disproves_compatibility",
        "implementation_work_requires_evidence_or_explicit_contract_gap",
        "cpu_contract_remains_owned_by_part_02",
        "no_proprietary_guest_or_firmware_material_in_repo",
        "guest_runtime_deferred",
    ):
        require(rules.get(key) is True, f"required rule disabled: {key}")

    require(owner_counts.get("generic_qemu", 0) > 0, "generic QEMU ownership class unused")
    require(owner_counts.get("vmapple_specific", 0) > 0, "VMApple-specific ownership class unused")
    require(owner_counts.get("host_framework_dependent", 0) > 0,
            "host-framework-dependent ownership class unused")
    require(owner_counts.get("unknown_requires_evidence", 0) > 0,
            "unknown/evidence ownership class unused")

def summary(data: dict[str, Any]) -> dict[str, Any]:
    validate(data)
    ownership: dict[str, int] = {}
    project: dict[str, int] = {}
    categories: dict[str, int] = {}
    for item in data["components"]:
        ownership[item["ownership"]] = ownership.get(item["ownership"], 0) + 1
        project[item["project_owner"]] = project.get(item["project_owner"], 0) + 1
        categories[item["category"]] = categories.get(item["category"], 0) + 1
    return {
        "classification": "P3_01_PLATFORM_CONTRACT_VALID",
        "project_version": data["project_version"],
        "component_count": len(data["components"]),
        "ownership_counts": dict(sorted(ownership.items())),
        "project_owner_counts": dict(sorted(project.items())),
        "category_counts": dict(sorted(categories.items())),
        "next_objective": data["next_objective"],
        "guest_execution": False,
    }

def expect_failure(data: dict[str, Any], mutate, label: str) -> None:
    broken = copy.deepcopy(data)
    mutate(broken)
    try:
        validate(broken)
    except ContractError:
        print(f"self-check reject: PASS: {label}")
        return
    raise ContractError(f"self-check mutation was accepted: {label}")

def self_check(data: dict[str, Any]) -> None:
    validate(data)
    expect_failure(data, lambda d: d["components"].append(copy.deepcopy(d["components"][0])),
                   "duplicate component")
    expect_failure(data, lambda d: d["components"][0].pop("category", None),
                   "missing component category")
    expect_failure(data, lambda d: d["components"][0].__setitem__("ownership", "apple_magic"),
                   "unknown ownership class")
    expect_failure(data, lambda d: d["action_values"].append("implement"),
                   "automatic implementation action")
    expect_failure(data, lambda d: d["source_locks"]["inferno"].__setitem__("revision", "0" * 40),
                   "Inferno source-lock drift")
    expect_failure(data, lambda d: d["scope"].__setitem__("cpu_contract_owner", "Part 03"),
                   "CPU ownership theft")
    expect_failure(data, lambda d: d["part_03_objectives"].append("P3.07 Scope Creep"),
                   "P3.07 scope creep")
    expect_failure(data, lambda d: d["rules"].__setitem__(
        "implementation_work_requires_evidence_or_explicit_contract_gap", False),
        "evidence gate disabled")
    expect_failure(data, lambda d: d["components"][4].__setitem__("action", "defer"),
                   "generic QEMU replacement preclassification")
    print("P3.01 self-check: PASS")

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--contract", default=str(DEFAULT_CONTRACT))
    sub = ap.add_subparsers(dest="command", required=True)
    sub.add_parser("validate")
    s = sub.add_parser("summary")
    s.add_argument("--json", action="store_true")
    l = sub.add_parser("lookup")
    l.add_argument("component_id")
    sub.add_parser("self-check")
    args = ap.parse_args()

    data = load(Path(args.contract))
    if args.command == "validate":
        validate(data)
        print("P3.01 platform contract: PASS")
    elif args.command == "summary":
        result = summary(data)
        if args.json:
            print(json.dumps(result, indent=2, sort_keys=True))
        else:
            print(f"components: {result['component_count']}")
            for key, value in result["ownership_counts"].items():
                print(f"{key}: {value}")
            print(f"next objective: {result['next_objective']}")
    elif args.command == "lookup":
        validate(data)
        for item in data["components"]:
            if item["id"] == args.component_id:
                print(json.dumps(item, indent=2, sort_keys=True))
                return 0
        raise ContractError(f"unknown component: {args.component_id}")
    elif args.command == "self-check":
        self_check(data)
    return 0

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ContractError as exc:
        print(f"P3.01 contract failure: {exc}", file=sys.stderr)
        raise SystemExit(1)

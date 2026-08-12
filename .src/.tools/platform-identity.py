#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONTRACT = ROOT / ".src" / ".configs" / "p3.02-identity-contract.json"
DEFAULT_PROFILE = ROOT / ".src" / ".configs" / "p3.02-identity.example.json"
EXPECTED_VERSION = "3.1.0.0.0.0"
EXPECTED_INFERNO = "cc4302a99167abec69b714cfd00c38caece7e7de"
EXPECTED_QEMU = "84f07211cc5b4fc6a371559bf8a5de4fb068e648"
MAC_RE = re.compile(r"^(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$")
TEXT_RE = re.compile(r"^[A-Za-z0-9 ._()/+\-]*$")

class IdentityError(RuntimeError):
    pass

def require(value: bool, message: str) -> None:
    if not value:
        raise IdentityError(message)

def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))

def canonical(data: Any) -> bytes:
    return (json.dumps(data, sort_keys=True, separators=(",", ":")) + "\n").encode()

def parse_u64(value: Any) -> int:
    if isinstance(value, bool):
        raise IdentityError("machine_uuid cannot be boolean")
    if isinstance(value, int):
        parsed = value
    elif isinstance(value, str):
        raw = value.strip()
        require(raw != "", "machine_uuid cannot be empty")
        if re.fullmatch(r"0[xX][0-9a-fA-F]+", raw):
            parsed = int(raw, 16)
        elif re.fullmatch(r"[0-9]+", raw):
            parsed = int(raw, 10)
        else:
            raise IdentityError("machine_uuid must be decimal or a 0x-prefixed integer")
    else:
        raise IdentityError("machine_uuid must be an integer or string")
    require(0 <= parsed <= 0xFFFFFFFFFFFFFFFF, "machine_uuid must fit uint64")
    return parsed

def validate_contract(data: dict[str, Any]) -> None:
    require(data.get("schema") == 1, "contract schema must be 1")
    require(data.get("project_version") == EXPECTED_VERSION, "contract project version mismatch")
    require(data.get("part") == "Part 03", "contract part mismatch")
    require(data.get("objective") == "P3.02", "contract objective mismatch")
    require(data.get("next_objective") == "P3.03", "next objective must be P3.03")
    scope = data.get("scope", {})
    require(scope.get("machine") == "vmapple", "machine must be vmapple")
    require(scope.get("device_type") == "vmapple-cfg", "device type must be vmapple-cfg")
    require(scope.get("config_region_size") == 0x10000, "config region size drift")
    require(scope.get("guest_runtime_deferred") is True, "guest runtime must remain deferred")
    require(scope.get("source_patch_required") is False, "P3.02 must not claim a source patch is required")

    locks = data.get("source_locks", {})
    inferno = locks.get("inferno", {})
    require(inferno.get("revision") == EXPECTED_INFERNO, "Inferno revision lock drift")
    require(inferno.get("cfg_blob_sha") == "3d58a29f69d7b6090436afbe9609ee9370a6c115",
            "Inferno cfg blob drift")
    require(inferno.get("machine_blob_sha") == "89c04c09f705d987ee96c11c1f5f4fc79713bf2e",
            "Inferno machine blob drift")
    qemu = locks.get("qemu_upstream_reference", {})
    require(qemu.get("revision") == EXPECTED_QEMU, "QEMU reference revision drift")
    require(qemu.get("cfg_blob_sha") == "2a3204f0ec2615097a4198e42cbe8d185f526e9e",
            "QEMU cfg reference blob drift")
    require(qemu.get("machine_blob_sha") == "607181f5177b1c798a7504150ce29aa383b29993",
            "QEMU machine reference blob drift")

    fields = data.get("fields", [])
    require(len(fields) == 27, "expected exactly 27 named config fields")
    seen_names: set[str] = set()
    seen_offsets: set[int] = set()
    configurable: set[str] = set()
    for item in fields:
        name = item.get("name")
        require(isinstance(name, str) and name, "field name missing")
        require(name not in seen_names, f"duplicate field name: {name}")
        seen_names.add(name)
        offset = item.get("offset")
        require(isinstance(offset, int) and 0 <= offset < 0x10000, f"invalid offset for {name}")
        require(offset not in seen_offsets, f"duplicate field offset: {offset:#x}")
        seen_offsets.add(offset)
        size = item.get("size")
        require(isinstance(size, int) and size > 0 and offset + size <= 0x10000,
                f"invalid field size for {name}")
        require(item.get("class") in set(data["field_classes"]), f"invalid class for {name}")
        require(item.get("requirement") in set(data["requirement_states"]),
                f"invalid requirement state for {name}")
        require(item.get("layout_status") in {
            "comment_matches_c_declaration",
            "source_comment_disagrees_with_c_declaration",
        }, f"layout status missing for {name}")
        if item.get("configurable"):
            require(isinstance(item.get("profile_key"), str), f"profile key missing for {name}")
            configurable.add(item["profile_key"])

    require(configurable == {
        "machine_uuid", "run_installer1", "run_installer2",
        "mac_en0", "mac_en1", "mac_wifi0", "mac_bt0",
        "serial", "model", "soc_name",
    }, "configurable field set drift")

    by_name = {f["name"]: f for f in fields}
    require(by_name["cpu_ids"]["offset"] == 0x100 and by_name["cpu_ids"]["size"] == 0x200,
            "cpu_ids compiled-layout contract drift")
    require(by_name["scratch"]["offset"] == 0x300, "scratch compiled offset must be 0x300")
    require(by_name["scratch"]["source_comment_offset"] == 0x180,
            "scratch source-comment offset must remain recorded as 0x180")
    require(by_name["serial"]["offset"] == 0x500, "serial compiled offset must be 0x500")
    require(by_name["serial"]["source_comment_offset"] == 0x380,
            "serial source-comment offset must remain recorded as 0x380")

    finding = data.get("layout_findings", {})
    require(finding.get("classification") == "unresolved_source_layout_discrepancy",
            "layout discrepancy must remain unresolved")
    require(finding.get("action") == "preserve_and_measure_before_any_source_fix",
            "layout discrepancy must remain evidence-gated")
    require(finding.get("cpu_ids_declared_entries") == 128, "cpu_ids declaration count drift")
    require(finding.get("machine_max_cpus") == 32, "VMApple max CPU count drift")

    policy = data.get("profile_policy", {})
    require(policy.get("synthetic_examples_only_in_repo") is True, "synthetic repo policy disabled")
    require(policy.get("real_identifiers_must_remain_local") is True, "local identity policy disabled")
    require(policy.get("qemu_global_driver") == "vmapple-cfg", "QEMU global driver drift")
    require(policy.get("do_not_override_machine_derived_nr_cpus_ram_or_rnd") is True,
            "machine-derived field protection disabled")

    rules = data.get("rules", {})
    for key in (
        "ecid_is_fed_from_machine_uuid_property",
        "uuid_label_does_not_prove_apple_semantic_uuid_format",
        "cpu_ids_are_derived_from_cpu_count",
        "rnd_remains_machine_generated",
        "reference_identity_strings_are_not_promoted_to_requirements",
        "zero_mac_defaults_are_not_promoted_to_requirements",
        "unknown_fields_are_not_repurposed",
        "no_real_identity_material_in_repo",
        "guest_runtime_deferred",
        "no_inferno_source_patch_required",
        "layout_comments_are_not_treated_as_abi_truth",
        "cpu_id_array_layout_discrepancy_remains_unfixed",
    ):
        require(rules.get(key) is True, f"required rule disabled: {key}")

def validate_text(name: str, value: Any, max_bytes: int = 31) -> None:
    if value is None:
        return
    require(isinstance(value, str), f"{name} must be a string or null")
    encoded = value.encode("utf-8")
    require(0 < len(encoded) <= max_bytes, f"{name} must be 1..{max_bytes} UTF-8 bytes")
    require("\x00" not in value and "\n" not in value and "\r" not in value,
            f"{name} contains forbidden control characters")
    require("," not in value and "=" not in value, f"{name} cannot contain ',' or '='")
    require(TEXT_RE.fullmatch(value) is not None, f"{name} contains unsupported characters")

def validate_mac(name: str, value: Any, synthetic: bool) -> None:
    if value is None:
        return
    require(isinstance(value, str) and MAC_RE.fullmatch(value) is not None,
            f"{name} must be xx:xx:xx:xx:xx:xx or null")
    first = int(value.split(":")[0], 16)
    require((first & 1) == 0, f"{name} cannot be multicast")
    if synthetic:
        require((first & 2) != 0, f"{name} synthetic MAC must be locally administered")

def validate_profile(profile: dict[str, Any], contract: dict[str, Any]) -> dict[str, Any]:
    validate_contract(contract)
    require(profile.get("schema") == 1, "profile schema must be 1")
    require(profile.get("project_version") == EXPECTED_VERSION, "profile project version mismatch")
    require(profile.get("objective") == "P3.02", "profile objective mismatch")
    synthetic = profile.get("synthetic")
    require(isinstance(synthetic, bool), "profile synthetic flag must be boolean")
    example_only = profile.get("example_only", False)
    require(isinstance(example_only, bool), "example_only flag must be boolean")
    if example_only:
        require(synthetic is True, "example_only profile must be synthetic")

    uuid_value = parse_u64(profile.get("machine_uuid"))
    identity = profile.get("identity", {})
    require(isinstance(identity, dict), "identity must be an object")
    allowed_identity = {"serial", "model", "soc_name", "mac_en0", "mac_en1", "mac_wifi0", "mac_bt0"}
    require(set(identity) <= allowed_identity, "unknown identity profile key")
    for key in ("serial", "model", "soc_name"):
        validate_text(key, identity.get(key))
    for key in ("mac_en0", "mac_en1", "mac_wifi0", "mac_bt0"):
        validate_mac(key, identity.get(key), synthetic)

    installer = profile.get("installer", {})
    require(isinstance(installer, dict), "installer must be an object")
    require(set(installer) <= {"run_installer1", "run_installer2"}, "unknown installer profile key")
    for key in ("run_installer1", "run_installer2"):
        value = installer.get(key, 0)
        require(value in (0, 1) and not isinstance(value, bool), f"{key} must be integer 0 or 1")

    return {
        "machine_uuid": uuid_value,
        "synthetic": synthetic,
        "example_only": example_only,
        "identity": identity,
        "installer": {
            "run_installer1": installer.get("run_installer1", 0),
            "run_installer2": installer.get("run_installer2", 0),
        },
    }

def compile_profile(profile: dict[str, Any], contract: dict[str, Any]) -> dict[str, Any]:
    normalized = validate_profile(profile, contract)
    driver = contract["profile_policy"]["qemu_global_driver"]
    argv = ["-M", f"vmapple,uuid={normalized['machine_uuid']}"]
    properties: list[str] = []

    prop_map = {
        "serial": "serial",
        "model": "model",
        "soc_name": "soc_name",
        "mac_en0": "mac-en0",
        "mac_en1": "mac-en1",
        "mac_wifi0": "mac-wifi0",
        "mac_bt0": "mac-bt0",
    }
    for key, prop in prop_map.items():
        value = normalized["identity"].get(key)
        if value is None:
            continue
        argv += ["-global", f"{driver}.{prop}={value}"]
        properties.append(prop)

    for key in ("run_installer1", "run_installer2"):
        value = normalized["installer"][key]
        argv += ["-global", f"{driver}.{key}={value}"]
        properties.append(key)

    source_profile_fingerprint = hashlib.sha256(canonical(profile)).hexdigest()
    compiled = {
        "schema": 1,
        "classification": "P3_02_IDENTITY_PROFILE_COMPILED",
        "project_version": EXPECTED_VERSION,
        "objective": "P3.02",
        "guest_execution": False,
        "synthetic": normalized["synthetic"],
        "example_only": normalized["example_only"],
        "profile_fingerprint": source_profile_fingerprint,
        "machine": "vmapple",
        "machine_uuid_decimal": normalized["machine_uuid"],
        "qemu_argv": argv,
        "overridden_device_properties": sorted(properties),
        "preserved_upstream_defaults": sorted(
            prop for key, prop in prop_map.items()
            if normalized["identity"].get(key) is None
        ),
        "machine_derived_fields_not_overridden": ["nr-cpus", "ram-size", "rnd", "cpu_ids"],
        "layout_discrepancy_status": contract["layout_findings"]["classification"],
    }
    fp_basis = dict(compiled)
    compiled["compiled_fingerprint"] = hashlib.sha256(canonical(fp_basis)).hexdigest()
    return compiled

def expect_failure(contract: dict[str, Any], profile: dict[str, Any], mutate, label: str) -> None:
    broken = copy.deepcopy(profile)
    mutate(broken)
    try:
        validate_profile(broken, contract)
    except IdentityError:
        print(f"self-check reject: PASS: {label}")
        return
    raise IdentityError(f"self-check mutation was accepted: {label}")

def self_check(contract: dict[str, Any], profile: dict[str, Any]) -> None:
    validate_contract(contract)
    validate_profile(profile, contract)
    first = compile_profile(profile, contract)
    second = compile_profile(copy.deepcopy(profile), contract)
    require(canonical(first) == canonical(second), "profile compilation is not deterministic")
    require(parse_u64("0008") == 8 and parse_u64("0x8") == 8,
            "decimal/hex machine_uuid normalization drift")
    expect_failure(contract, profile, lambda p: p.__setitem__("machine_uuid", "0b1000"),
                   "binary machine_uuid format")
    expect_failure(contract, profile, lambda p: p.__setitem__("machine_uuid", "0x10000000000000000"),
                   "uint64 overflow")
    expect_failure(contract, profile, lambda p: p["identity"].__setitem__("serial", "x" * 32),
                   "oversized serial")
    expect_failure(contract, profile, lambda p: p["identity"].__setitem__("serial", "bad,value"),
                   "option-injection comma")
    expect_failure(contract, profile, lambda p: p["identity"].__setitem__("mac_en0", "01:00:00:00:00:01"),
                   "multicast MAC")
    expect_failure(contract, profile, lambda p: p["identity"].__setitem__("mac_en0", "00:00:00:00:00:01"),
                   "non-local synthetic MAC")
    expect_failure(contract, profile, lambda p: p["installer"].__setitem__("run_installer1", 2),
                   "installer flag outside 0/1")
    broken_contract = copy.deepcopy(contract)
    broken_contract["layout_findings"]["classification"] = "fixed_without_evidence"
    try:
        validate_contract(broken_contract)
    except IdentityError:
        print("self-check reject: PASS: layout fix without evidence")
    else:
        raise IdentityError("self-check accepted an unsupported layout fix")
    print("P3.02 self-check: PASS")

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--contract", default=str(DEFAULT_CONTRACT))
    sub = ap.add_subparsers(dest="command", required=True)
    sub.add_parser("validate-contract")
    vp = sub.add_parser("validate-profile")
    vp.add_argument("--profile", default=str(DEFAULT_PROFILE))
    cp = sub.add_parser("compile")
    cp.add_argument("--profile", default=str(DEFAULT_PROFILE))
    cp.add_argument("--output", required=True)
    sc = sub.add_parser("self-check")
    sc.add_argument("--profile", default=str(DEFAULT_PROFILE))
    args = ap.parse_args()

    contract = load_json(Path(args.contract))
    if args.command == "validate-contract":
        validate_contract(contract)
        print("P3.02 identity contract: PASS")
    elif args.command == "validate-profile":
        profile = load_json(Path(args.profile))
        normalized = validate_profile(profile, contract)
        print("P3.02 identity profile: PASS")
        print(f"synthetic={normalized['synthetic']} example_only={normalized['example_only']}")
    elif args.command == "compile":
        profile = load_json(Path(args.profile))
        result = compile_profile(profile, contract)
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(json.dumps(result, indent=2, sort_keys=True).encode() + b"\n")
        print("P3.02 identity profile compile: PASS")
        print(f"profile_fingerprint={result['profile_fingerprint']}")
        print(f"compiled_fingerprint={result['compiled_fingerprint']}")
        print("overridden_properties=" + ",".join(result["overridden_device_properties"]))
        print(f"output={out}")
    elif args.command == "self-check":
        profile = load_json(Path(args.profile))
        self_check(contract, profile)
    return 0

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except IdentityError as exc:
        print(f"P3.02 identity failure: {exc}", file=sys.stderr)
        raise SystemExit(1)

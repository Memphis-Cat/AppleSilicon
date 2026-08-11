#!/usr/bin/env python3

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

VERSION = "2.4.0.0.0.0"
ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_POLICY = ROOT_DIR / ".src" / ".configs" / "p2.05-regression-policy.json"
INPUT_ERROR = 2


class RegressionError(Exception):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RegressionError(message)


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RegressionError(f"file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise RegressionError(f"invalid JSON in {path}: {exc}") from exc
    require(isinstance(value, dict), f"JSON root must be an object: {path}")
    return value


def canonical_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(f"blob {len(data)}\0".encode("ascii") + data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def project_path(root: Path, relative: str) -> Path:
    root = root.resolve()
    path = (root / relative).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise RegressionError(f"path escapes project root: {relative}") from exc
    return path


def validate_policy(policy: dict[str, Any]) -> None:
    require(policy.get("schema") == 1, "P2.05 schema must be 1")
    require(policy.get("project_version") == VERSION, "P2.05 project_version mismatch")
    require(policy.get("part") == "Part 02", "P2.05 part mismatch")
    require(policy.get("objective") == "P2.05", "P2.05 objective mismatch")
    require(policy.get("next_objective") == "P2.06", "P2.05 must point to P2.06")
    require(policy.get("result_schema") == 1, "P2.05 result_schema must be 1")
    require(policy.get("promotion_behavior") == "none", "P2.05 must not promote evidence")
    require(
        policy.get("output") == ".build/p2.05/cpu-contract-regression.json",
        "P2.05 output path mismatch",
    )

    scope = policy.get("scope")
    require(isinstance(scope, dict), "P2.05 scope must be an object")
    expected_scope = {
        "cpu": "apple-gxf",
        "accelerator": "tcg",
        "control_cpu": "max",
        "guest_execution": False,
    }
    for key, expected in expected_scope.items():
        require(scope.get(key) == expected, f"P2.05 scope mismatch: {key}")

    artifacts = policy.get("locked_artifacts")
    require(isinstance(artifacts, list) and artifacts, "locked_artifacts must be non-empty")
    observed_paths = set()
    for index, item in enumerate(artifacts):
        require(isinstance(item, dict), f"locked_artifacts[{index}] must be an object")
        path = item.get("path")
        blob = item.get("git_blob_sha")
        role = item.get("role")
        require(isinstance(path, str) and path, f"locked_artifacts[{index}].path missing")
        require(isinstance(blob, str) and len(blob) == 40, f"locked_artifacts[{index}].git_blob_sha invalid")
        require(isinstance(role, str) and role, f"locked_artifacts[{index}].role missing")
        require(path not in observed_paths, f"duplicate locked artifact: {path}")
        observed_paths.add(path)

    expected_paths = {
        ".src/.configs/p2.01-cpu-contract.json",
        ".src/.configs/p2.02-framework-policy.json",
        ".src/.configs/p2.03-sysreg-policy.json",
        ".src/.configs/p2.04-feature-contract.json",
        ".src/.patches/0003-arm-apple-sysreg-framework.patch",
        ".src/.patches/0004-arm-apple-sysreg-policy-model.patch",
        ".src/.patches/0005-arm-vmapple-feature-contract.patch",
    }
    require(observed_paths == expected_paths, "P2.05 locked artifact set mismatch")

    invariants = policy.get("invariants")
    require(isinstance(invariants, dict), "P2.05 invariants must be an object")
    required_invariants = (
        "p2_02_representatives_match_p2_01",
        "p2_03_live_policy_count_zero",
        "p2_03_unknown_behavior_fail_closed",
        "p2_04_requirements_all_enforced",
        "p2_04_preserves_stronger_features",
        "max_control_cpu_untouched",
        "apple_gxf_profile_tcg_only",
        "inferno_source_lock_consistent",
        "deterministic_result_required",
    )
    for key in required_invariants:
        require(invariants.get(key) is True, f"P2.05 invariant must be true: {key}")


def verify_locked_artifacts(root: Path, policy: dict[str, Any]) -> list[dict[str, str]]:
    result = []
    for item in policy["locked_artifacts"]:
        path = project_path(root, item["path"])
        require(path.is_file(), f"locked artifact missing: {item['path']}")
        observed_blob = git_blob_sha(path)
        require(
            observed_blob == item["git_blob_sha"],
            f"locked artifact drift: {item['path']}: expected {item['git_blob_sha']}, observed {observed_blob}",
        )
        result.append(
            {
                "path": item["path"],
                "role": item["role"],
                "git_blob_sha": observed_blob,
                "sha256": sha256_file(path),
            }
        )
    return result


def load_contracts(root: Path) -> tuple[dict[str, Any], ...]:
    paths = (
        ".src/.configs/p2.01-cpu-contract.json",
        ".src/.configs/p2.02-framework-policy.json",
        ".src/.configs/p2.03-sysreg-policy.json",
        ".src/.configs/p2.04-feature-contract.json",
    )
    return tuple(load_json(project_path(root, path)) for path in paths)


def verify_cross_contracts(p1: dict[str, Any], p2: dict[str, Any], p3: dict[str, Any], p4: dict[str, Any]) -> dict[str, Any]:
    contracts = ((p1, "P2.01", "P2.02"), (p2, "P2.02", "P2.03"), (p3, "P2.03", "P2.04"), (p4, "P2.04", "P2.05"))
    for contract, objective, next_objective in contracts:
        require(contract.get("objective") == objective, f"{objective} objective mismatch")
        require(contract.get("next_objective") == next_objective, f"{objective} sequence drift")

    for label, contract in (("P2.02", p2), ("P2.03", p3)):
        scope = contract.get("cpu_scope")
        require(isinstance(scope, dict), f"{label} cpu_scope missing")
        require(scope.get("enabled_cpu") == "apple-gxf", f"{label} CPU scope drift")
        require(scope.get("accelerator") == "tcg", f"{label} accelerator drift")
        require(scope.get("control_cpu") == "max", f"{label} control CPU drift")
        require(scope.get("control_cpu_must_remain_untouched") is True, f"{label} max isolation drift")

    scope4 = p4.get("scope")
    require(isinstance(scope4, dict), "P2.04 scope missing")
    require(scope4.get("cpu") == "apple-gxf", "P2.04 CPU scope drift")
    require(scope4.get("accelerator") == "tcg", "P2.04 accelerator drift")
    require(scope4.get("base_cpu") == "max", "P2.04 base CPU drift")
    require(scope4.get("policy") == "minimum_required_preserve_stronger", "P2.04 feature policy drift")

    registers = p1.get("registers")
    require(isinstance(registers, list), "P2.01 registers missing")
    index = {entry.get("name"): entry for entry in registers if isinstance(entry, dict)}
    representatives = p2.get("representative_registers")
    require(isinstance(representatives, list) and representatives, "P2.02 representatives missing")
    for representative in representatives:
        require(isinstance(representative, dict), "P2.02 representative invalid")
        name = representative.get("name")
        require(name in index, f"P2.02 representative missing from P2.01: {name}")
        source = index[name]
        require(source.get("group") == representative.get("group"), f"representative group drift: {name}")
        require(source.get("architectural_name") == representative.get("architectural_name"), f"representative encoding drift: {name}")
        require(source.get("implementation_state") == "inventory_only", f"representative prematurely implemented: {name}")

    unresolved = p2.get("unresolved_policy")
    require(isinstance(unresolved, dict), "P2.02 unresolved policy missing")
    require(unresolved.get("qemu_access_result") == "CP_ACCESS_UNDEFINED", "P2.02 fail-closed result drift")
    for key in ("invent_read_values", "invent_write_side_effects", "invent_reset_values"):
        require(unresolved.get(key) is False, f"P2.02 unresolved behavior drift: {key}")

    require(p3.get("live_policy_count") == 0, "P2.03 live policy count must remain zero")
    require(p3.get("live_policies") == [], "P2.03 live policy table must remain empty")
    requirements3 = p3.get("policy_requirements")
    require(isinstance(requirements3, dict), "P2.03 policy requirements missing")
    for key in ("unknown_read_must_undef", "unknown_write_must_undef", "duplicate_encodings_forbidden"):
        require(requirements3.get(key) is True, f"P2.03 policy invariant drift: {key}")

    requirements4 = p4.get("requirements")
    require(isinstance(requirements4, list), "P2.04 requirements missing")
    expected_ids = ["pauth", "ssbs2", "sme", "sme2", "pan3", "tgran16", "tgran4", "tlbirange"]
    require([item.get("id") for item in requirements4] == expected_ids, "P2.04 requirement set/order drift")
    require(all(item.get("status") == "enforced" for item in requirements4), "P2.04 requirement not enforced")

    rules4 = p4.get("rules")
    require(isinstance(rules4, dict), "P2.04 rules missing")
    for key in ("do_not_modify_max_cpu", "do_not_modify_host_hvf_or_kvm", "do_not_mask_stronger_supported_features", "sysreg_semantics_remain_owned_by_p2_03", "guest_runtime_deferred"):
        require(rules4.get(key) is True, f"P2.04 rule drift: {key}")

    sources1 = p1.get("sources")
    locks4 = p4.get("source_locks")
    require(isinstance(sources1, dict) and isinstance(locks4, dict), "source locks missing")
    inferno1 = sources1.get("inferno", {}).get("revision")
    inferno4 = locks4.get("inferno", {}).get("revision")
    require(inferno1 == inferno4, "Inferno source lock differs between P2.01 and P2.04")

    return {
        "representative_count": len(representatives),
        "live_sysreg_policy_count": 0,
        "feature_requirement_ids": expected_ids,
        "inferno_revision": inferno1,
    }


def verify_prepared_source(source: Path) -> dict[str, Any]:
    cpu64 = source / "target/arm/cpu64.c"
    sysreg = source / "target/arm/apple-sysregs.c"
    feature = source / "target/arm/apple-cpu-features.c"
    meson = source / "target/arm/meson.build"
    for path in (cpu64, sysreg, feature, meson):
        require(path.is_file(), f"prepared source file missing: {path}")

    cpu_text = cpu64.read_text(encoding="utf-8")
    max_start = cpu_text.find("static void aarch64_max_initfn(Object *obj)")
    apple_start = cpu_text.find("static void aarch64_apple_gxf_initfn(Object *obj)")
    require(max_start >= 0 and apple_start > max_start, "CPU initializer boundaries missing")
    max_body = cpu_text[max_start:apple_start]
    apple_body = cpu_text[apple_start:]
    require("apple_cpu_feature_profile_init" not in max_body, "max CPU contaminated by Apple feature profile")
    require("apple_sysreg_framework_init" not in max_body, "max CPU contaminated by Apple sysreg framework")
    require("if (tcg_enabled())" in apple_body, "apple-gxf TCG gate missing")
    require("apple_cpu_feature_profile_init(cpu);" in apple_body, "apple-gxf feature wiring missing")
    require("apple_sysreg_framework_init(cpu);" in apple_body, "apple-gxf sysreg wiring missing")

    sysreg_text = sysreg.read_text(encoding="utf-8")
    require("live_policy_count = 0" in sysreg_text, "P2.03 empty live policy table missing")

    feature_text = feature.read_text(encoding="utf-8")
    for token in (
        "cpu_isar_feature(aa64_pauth, cpu)",
        "ID_AA64PFR1, SSBS, 2",
        "ID_AA64PFR1, SME, 2",
        "ID_AA64MMFR1, PAN, 3",
        "ID_AA64MMFR0, TGRAN16, 1",
        "ID_AA64ISAR0, TLB, 2",
    ):
        require(token in feature_text, f"P2.04 feature invariant missing: {token}")

    meson_text = meson.read_text(encoding="utf-8")
    require("'apple-sysregs.c'" in meson_text, "apple-sysregs.c Meson wiring missing")
    require("'apple-cpu-features.c'" in meson_text, "apple-cpu-features.c Meson wiring missing")

    return {
        "max_control_isolated": True,
        "apple_gxf_tcg_wiring": True,
        "live_sysreg_policy_count": 0,
        "feature_profile_present": True,
    }


def run_regression(root: Path, policy: dict[str, Any], prepared_source: Path | None) -> dict[str, Any]:
    validate_policy(policy)
    locked = verify_locked_artifacts(root, policy)
    p1, p2, p3, p4 = load_contracts(root)
    cross = verify_cross_contracts(p1, p2, p3, p4)
    prepared = verify_prepared_source(prepared_source) if prepared_source else None
    result = {
        "schema": policy["result_schema"],
        "project_version": VERSION,
        "objective": "P2.05",
        "classification": "P2_05_REGRESSION_PASS",
        "policy_sha256": canonical_hash(policy),
        "locked_artifacts": locked,
        "cross_contracts": cross,
        "prepared_source": prepared,
        "guest_execution": False,
    }
    result["suite_fingerprint"] = canonical_hash({
        "policy_sha256": result["policy_sha256"],
        "locked_artifacts": locked,
        "cross_contracts": cross,
        "prepared_source": prepared,
    })
    return result


def self_check(root: Path, policy: dict[str, Any]) -> None:
    validate_policy(policy)
    verify_locked_artifacts(root, policy)
    p1, p2, p3, p4 = load_contracts(root)
    verify_cross_contracts(p1, p2, p3, p4)

    mutations = (
        ("CPU scope drift", lambda p: p["scope"].__setitem__("cpu", "max")),
        ("disabled invariant", lambda p: p["invariants"].__setitem__("p2_03_live_policy_count_zero", False)),
        ("missing locked artifact", lambda p: p["locked_artifacts"].pop()),
    )
    for label, mutate in mutations:
        changed = copy.deepcopy(policy)
        mutate(changed)
        try:
            validate_policy(changed)
        except RegressionError:
            pass
        else:
            raise RegressionError(f"self-check accepted {label}")

    bad_blob = copy.deepcopy(policy)
    bad_blob["locked_artifacts"][0]["git_blob_sha"] = "0" * 40
    try:
        verify_locked_artifacts(root, bad_blob)
    except RegressionError:
        pass
    else:
        raise RegressionError("self-check accepted locked artifact drift")

    bad2 = copy.deepcopy(p2)
    bad2["representative_registers"][0]["architectural_name"] = "S0_0_C0_C0_0"
    try:
        verify_cross_contracts(p1, bad2, p3, p4)
    except RegressionError:
        pass
    else:
        raise RegressionError("self-check accepted representative encoding drift")

    bad3 = copy.deepcopy(p3)
    bad3["live_policy_count"] = 1
    bad3["live_policies"] = [{"name": "HID0"}]
    try:
        verify_cross_contracts(p1, p2, bad3, p4)
    except RegressionError:
        pass
    else:
        raise RegressionError("self-check accepted unapproved live sysreg policy")

    bad4 = copy.deepcopy(p4)
    bad4["requirements"][1]["status"] = "planned"
    try:
        verify_cross_contracts(p1, p2, p3, bad4)
    except RegressionError:
        pass
    else:
        raise RegressionError("self-check accepted unenforced P2.04 requirement")

    require(run_regression(root, policy, None) == run_regression(root, policy, None), "nondeterministic regression result")


def write_result(path: Path, result: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="AppleSilicon P2.05 deterministic CPU contract regression")
    parser.add_argument("--version", action="version", version=f"AppleSilicon P2.05 {VERSION}")
    parser.add_argument("--root", type=Path, default=ROOT_DIR)
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run")
    run.add_argument("--prepared-source", type=Path)
    run.add_argument("--output", type=Path)
    sub.add_parser("self-check")
    sub.add_parser("validate-policy")
    args = parser.parse_args()

    try:
        root = args.root.resolve()
        policy = load_json(args.policy)
        if args.command == "validate-policy":
            validate_policy(policy)
            print("P2.05 regression policy: PASS")
            return 0
        if args.command == "self-check":
            self_check(root, policy)
            print("P2.05 self-check: PASS")
            print("checks=scope,artifact-locks,representatives,live-policy,features,determinism")
            return 0
        prepared = args.prepared_source.resolve() if args.prepared_source else None
        result = run_regression(root, policy, prepared)
        if args.output:
            write_result(args.output, result)
        print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
        return 0
    except RegressionError as exc:
        print(f"P2.05 regression failure: {exc}", file=sys.stderr)
        return INPUT_ERROR


if __name__ == "__main__":
    raise SystemExit(main())

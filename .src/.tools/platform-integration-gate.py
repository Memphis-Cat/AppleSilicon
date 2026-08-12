#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
EXPECTED_VERSION = "3.5.0.0.0.0"
EXPECTED_P206_VERSION = "2.5.0.0.0.0"
EXPECTED_INFERNO = "cc4302a99167abec69b714cfd00c38caece7e7de"
EXPECTED_MACHINE = {
    "machine": "vmapple",
    "accelerator": "tcg",
    "cpu": "apple-gxf",
    "control_cpu": "max",
}


class GateError(RuntimeError):
    pass


def require(value: bool, message: str) -> None:
    if not value:
        raise GateError(message)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def canonical(data: dict[str, Any]) -> bytes:
    return (json.dumps(data, sort_keys=True, separators=(",", ":")) + "\n").encode()


def git_blob(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def find_component(data: dict[str, Any], component_id: str) -> dict[str, Any]:
    for item in data.get("components", []):
        if item.get("id") == component_id:
            return item
    raise GateError(f"component missing: {component_id}")


def inferno_revision(data: dict[str, Any]) -> str | None:
    locks = data.get("source_locks", {})
    inferno = locks.get("inferno", {})
    return inferno.get("revision")


def validate_policy(policy: dict[str, Any]) -> None:
    require(policy.get("schema") == 1, "P3.06 schema mismatch")
    require(policy.get("project_version") == EXPECTED_VERSION, "P3.06 version mismatch")
    require(policy.get("part") == "Part 03", "P3.06 part mismatch")
    require(policy.get("objective") == "P3.06", "P3.06 objective mismatch")
    require(policy.get("title") == "Part 03 Integration Gate", "P3.06 title mismatch")
    require(policy.get("source_lock", {}).get("inferno_revision") == EXPECTED_INFERNO,
            "P3.06 Inferno source lock drift")
    require(policy.get("integrated_machine") == EXPECTED_MACHINE,
            "P3.06 integrated machine contract drift")

    validators = policy.get("contract_validators", [])
    require([item.get("objective") for item in validators] ==
            ["P3.01", "P3.02", "P3.03", "P3.04", "P3.05"],
            "P3.06 validator objective order drift")

    patch_series = policy.get("patch_series", [])
    require(len(patch_series) == 5, "Part 03 integration patch series must contain exactly five patches")
    require(patch_series[-1].startswith(".src/.patches/0005-"),
            "Part 03 patch series must end at 0005")
    require(not any("0006-" in item for item in patch_series), "P3.06 forbids an unreviewed 0006 patch")

    required = policy.get("requirements", {})
    for key in (
        "p2_06_integration_manifest_must_pass",
        "all_p3_contracts_must_validate",
        "all_p3_contracts_must_share_pinned_inferno_revision",
        "part_03_adds_no_patch_after_0005",
        "p2_03_live_sysreg_policy_count_remains_zero",
        "p3_02_layout_discrepancy_remains_unresolved",
        "p3_03_power_semantics_remain_evidence_gated",
        "p3_04_bdif_writes_remain_unimplemented_without_evidence",
        "p3_04_barrier_remains_reference_noop_until_evidence",
        "p3_05_aes_unimplemented_commands_remain_evidence_gated",
        "p1_05_optional_pvg_behavior_is_preserved",
        "fake_gpu_is_forbidden",
        "modern_macos_graphics_compatibility_is_not_claimed",
        "p1_runtime_evidence_and_promotion_gates_remain_authoritative",
        "p2_06_runtime_probe_is_reused_not_forked",
        "runtime_integrity_fingerprint_recheck_required",
        "root_readme_remains_frozen",
        "guest_runtime_deferred",
    ):
        require(required.get(key) is True, f"P3.06 requirement disabled: {key}")

    require(policy.get("part_status_after_success") == "closed_implementation_complete",
            "P3.06 must close Part 03")
    require(policy.get("next_part") == "Part 04", "P3.06 next part mismatch")
    require(policy.get("next_objective") == "P4.01", "P3.06 next objective mismatch")


def validate_locked_artifacts(policy: dict[str, Any]) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in policy.get("locked_artifacts", []):
        rel = item.get("path")
        require(isinstance(rel, str) and rel not in seen, f"duplicate/invalid locked artifact: {rel}")
        seen.add(rel)
        path = ROOT / rel
        require(path.is_file(), f"locked artifact missing: {rel}")
        observed = git_blob(path)
        require(observed == item.get("git_blob_sha"), f"locked artifact drift: {rel}: {observed}")
        result.append({
            "path": rel,
            "role": item["role"],
            "git_blob_sha": observed,
            "sha256": sha256(path),
        })
    return result


def validate_p2_manifest(path: Path) -> dict[str, Any]:
    require(path.is_file(), f"P2.06 integration manifest missing: {path}")
    data = load_json(path)
    require(data.get("schema") == 1, "P2.06 integration manifest schema mismatch")
    require(data.get("project_version") == EXPECTED_P206_VERSION,
            "P2.06 integration manifest version mismatch")
    require(data.get("part") == "Part 02" and data.get("objective") == "P2.06",
            "P2.06 integration manifest identity drift")
    require(data.get("classification") == "P2_06_INTEGRATION_PASS",
            "P2.06 integration manifest did not pass")
    require(data.get("part_status") == "closed_implementation_complete",
            "Part 02 is not closed in its integration manifest")
    require(data.get("guest_execution") is False,
            "P2.06 integration manifest unexpectedly records guest execution")
    require(data.get("cpu_contract") == EXPECTED_MACHINE,
            "P2.06 integrated CPU/machine contract drift")
    prepared = data.get("prepared_source", {})
    require(prepared.get("inferno_revision") == EXPECTED_INFERNO,
            "P2.06 prepared-source Inferno revision drift")
    require(prepared.get("live_sysreg_policy_count") == 0,
            "live Apple sysreg policy count must remain zero")
    require(prepared.get("max_control_isolated") is True,
            "P2.06 max control isolation is not proven")
    require(prepared.get("apple_gxf_tcg_wiring") is True,
            "P2.06 apple-gxf TCG wiring is not proven")
    fp = data.get("integration_fingerprint")
    require(isinstance(fp, str) and len(fp) == 64, "P2.06 integration fingerprint invalid")
    basis = {k: v for k, v in data.items() if k not in ("classification", "integration_fingerprint")}
    expected_fp = hashlib.sha256(canonical(basis)).hexdigest()
    require(fp == expected_fp, "P2.06 integration fingerprint does not reproduce")
    return {
        "classification": data["classification"],
        "integration_fingerprint": fp,
        "sha256": sha256(path),
        "live_sysreg_policy_count": 0,
    }


def run_contract_validators(policy: dict[str, Any]) -> list[dict[str, str]]:
    results: list[dict[str, str]] = []
    for item in policy["contract_validators"]:
        tool = ROOT / item["tool"]
        contract = ROOT / item["contract"]
        require(tool.is_file(), f"validator missing: {item['tool']}")
        require(contract.is_file(), f"contract missing: {item['contract']}")
        cmd = [sys.executable, str(tool), "--contract", str(contract), item["command"]]
        proc = subprocess.run(cmd, text=True, capture_output=True)
        require(proc.returncode == 0,
                f"{item['objective']} validator failed: {(proc.stderr or proc.stdout).strip()}")
        results.append({
            "objective": item["objective"],
            "contract": item["contract"],
            "contract_git_blob_sha": git_blob(contract),
            "tool": item["tool"],
            "tool_git_blob_sha": git_blob(tool),
            "classification": "PASS",
        })
    return results


def validate_cross_contracts(policy: dict[str, Any]) -> dict[str, Any]:
    p301 = load_json(ROOT / ".src/.configs/p3.01-platform-contract.json")
    p302 = load_json(ROOT / ".src/.configs/p3.02-identity-contract.json")
    p303 = load_json(ROOT / ".src/.configs/p3.03-io-contract.json")
    p304 = load_json(ROOT / ".src/.configs/p3.04-storage-contract.json")
    p305 = load_json(ROOT / ".src/.configs/p3.05-peripheral-contract.json")
    contracts = [p301, p302, p303, p304, p305]

    require([d.get("objective") for d in contracts] ==
            ["P3.01", "P3.02", "P3.03", "P3.04", "P3.05"],
            "Part 03 contract objective order drift")
    for data in contracts:
        require(data.get("part") == "Part 03", f"{data.get('objective')}: part mismatch")
        require(data.get("scope", {}).get("machine") == "vmapple",
                f"{data.get('objective')}: machine scope drift")
        require(inferno_revision(data) == EXPECTED_INFERNO,
                f"{data.get('objective')}: Inferno source lock drift")

    objectives = p301.get("part_03_objectives", [])
    require(len(objectives) == 6 and objectives[-1].startswith("P3.06 "),
            "Part 03 objective count/final objective drift")
    require(not any(item.startswith("P3.07") for item in objectives), "P3.07 is forbidden")

    p302_rules = p302.get("rules", {})
    finding = p302.get("layout_findings", {})
    require(p302_rules.get("cpu_id_array_layout_discrepancy_remains_unfixed") is True,
            "P3.02 layout discrepancy was silently marked fixed")
    require(finding.get("classification") == "unresolved_source_layout_discrepancy",
            "P3.02 layout discrepancy classification drift")
    require(finding.get("action") == "preserve_and_measure_before_any_source_fix",
            "P3.02 layout discrepancy action drift")

    power = find_component(p303, "pl061_gpio_power")
    require(power.get("event_semantics") == "unknown_requires_runtime_evidence",
            "P3.03 power-button semantics were guessed")

    bdif = find_component(p304, "bdif_command_semantics")
    require(bdif.get("write_supported") is False,
            "P3.04 BDIF writes were enabled without evidence")
    require(bdif.get("runtime_write_requirement") == "unknown_requires_runtime_evidence",
            "P3.04 BDIF write requirement lost evidence gate")
    barrier = find_component(p304, "vmapple_virtio_blk_barrier")
    require(barrier.get("implementation") == "successful_no_op",
            "P3.04 Apple barrier reference behavior drift")
    require(barrier.get("flush_semantics") == "unknown_requires_runtime_evidence",
            "P3.04 barrier flush semantics were invented")

    aes = find_component(p305, "vmapple_aes_semantics")
    require(aes.get("declared_but_unimplemented_commands") == ["DSB", "SKG", "WRITE_REG"],
            "P3.05 AES unresolved command set drift")
    require(aes.get("runtime_requirement_of_unimplemented_commands") == "unknown_requires_runtime_evidence",
            "P3.05 AES unresolved commands lost evidence gate")
    pvg = find_component(p305, "apple_pvg_optionalization")
    require(pvg.get("construction") == "qdev_try_new",
            "P1.05 optional-PVG construction drift")
    require(pvg.get("when_unavailable") == "warn_and_continue_without_pvg",
            "P1.05 optional-PVG absence policy drift")
    require(pvg.get("fake_gpu_allowed") is False, "fake GPU substitution is forbidden")
    modern = find_component(p305, "modern_vmapple_graphics_status")
    require(modern.get("official_documented_guest_support") == "macOS_12_only",
            "P3.05 modern macOS graphics support boundary was overclaimed")

    machine_map = find_component(p301, "machine_memory_map")
    firmware = find_component(p301, "firmware_window_and_preboot_input")
    require(machine_map.get("project_owner") == "P3.06",
            "P3.06 no longer owns machine-wide map integration")
    require(firmware.get("project_owner") == "P3.06",
            "P3.06 no longer owns firmware-window integration")
    require(firmware.get("action") == "defer",
            "external firmware input must remain deferred/local")

    return {
        "inferno_revision": EXPECTED_INFERNO,
        "contract_count": 5,
        "layout_discrepancy": "unresolved",
        "power_semantics": "evidence_gated",
        "bdif_write_supported": False,
        "barrier_behavior": "successful_no_op",
        "aes_unimplemented_commands": ["DSB", "SKG", "WRITE_REG"],
        "pvg_absence_policy": "warn_and_continue_without_pvg",
        "fake_gpu_allowed": False,
        "modern_guest_support_claim": "macOS_12_only",
    }


def validate_patch_series(policy: dict[str, Any]) -> list[dict[str, str]]:
    expected = policy["patch_series"]
    actual_paths = sorted(
        ".src/.patches/" + path.name
        for path in (ROOT / ".src/.patches").glob("[0-9][0-9][0-9][0-9]-*.patch")
    )
    require(actual_paths == expected,
            f"patch series drift: expected {expected}; observed {actual_paths}")
    return [
        {"path": rel, "git_blob_sha": git_blob(ROOT / rel), "sha256": sha256(ROOT / rel)}
        for rel in expected
    ]


def main() -> int:
    ap = argparse.ArgumentParser(description="AppleSilicon P3.06 Part 03 integration gate")
    ap.add_argument("--policy", default=str(ROOT / ".src/.configs/p3.06-integration-policy.json"))
    ap.add_argument("--p2-06-manifest", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    policy = load_json(Path(args.policy))
    validate_policy(policy)
    locked = validate_locked_artifacts(policy)
    p2 = validate_p2_manifest(Path(args.p2_06_manifest))
    validators = run_contract_validators(policy)
    cross = validate_cross_contracts(policy)
    patches = validate_patch_series(policy)

    manifest: dict[str, Any] = {
        "schema": 1,
        "classification": "P3_06_INTEGRATION_PASS",
        "project_version": EXPECTED_VERSION,
        "part": "Part 03",
        "objective": "P3.06",
        "guest_execution": False,
        "integrated_machine": EXPECTED_MACHINE,
        "p2_06": p2,
        "platform_contract_validations": validators,
        "cross_contracts": cross,
        "patch_series": patches,
        "locked_artifacts": locked,
        "runtime_evidence_authority": {
            "manifest_policy": ".src/.configs/p1.09-manifest-policy.json",
            "promotion_policy": ".src/.configs/p1.10-promotion-policy.json",
            "runtime_delegate": ".src/.tools/run-p2.06-probe.sh",
        },
        "part_status": "closed_implementation_complete",
        "next_part": "Part 04",
        "next_objective": "P4.01",
    }
    basis = dict(manifest)
    basis.pop("classification", None)
    manifest["platform_integration_fingerprint"] = hashlib.sha256(canonical(basis)).hexdigest()

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(canonical(manifest))
    print(json.dumps(manifest, indent=2, sort_keys=True))
    print(f"P3.06 platform integration fingerprint: {manifest['platform_integration_fingerprint']}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, json.JSONDecodeError, GateError, KeyError, TypeError, ValueError) as exc:
        print(f"P3.06 integration failure: {exc}", file=sys.stderr)
        raise SystemExit(1)

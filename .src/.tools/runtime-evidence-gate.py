#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_POLICY = ROOT / ".src/.configs/p4.06-runtime-evidence-gate-policy.json"
P405_POLICY = ROOT / ".src/.configs/p4.05-divergence-promotion-policy.json"
P405_TOOL = ROOT / ".src/.tools/divergence-promotion.py"
P1_POLICY = ROOT / ".src/.configs/p1.10-promotion-policy.json"
P1_TOOL = ROOT / ".src/.tools/evidence-bundle.py"

EXPECTED_VERSION = "4.5.0.0.0.0"
EXPECTED_P405_VERSION = "4.4.0.0.0.0"
EXPECTED_INFERNO = "cc4302a99167abec69b714cfd00c38caece7e7de"
EXPECTED_ROOT_README = "5f056dadbac5d814b9ffb287ec786a559774f953"
SHA256_LEN = 64


class GateError(RuntimeError):
    pass


def require(value: bool, message: str) -> None:
    if not value:
        raise GateError(message)


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise GateError(f"could not read JSON {path}: {exc}") from exc
    require(isinstance(value, dict), f"top-level JSON must be an object: {path}")
    return value


def canonical(data: Any) -> bytes:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def canonical_line(data: Any) -> bytes:
    return canonical(data) + b"\n"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                h.update(chunk)
    except OSError as exc:
        raise GateError(f"could not hash {path}: {exc}") from exc
    return h.hexdigest()


def git_blob(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def is_sha256(value: Any) -> bool:
    return isinstance(value, str) and len(value) == SHA256_LEN and all(c in "0123456789abcdef" for c in value)


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise GateError(f"could not load module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def validate_policy(policy: dict[str, Any]) -> None:
    require(policy.get("schema") == 1, "P4.06 schema mismatch")
    require(policy.get("project_version") == EXPECTED_VERSION, "P4.06 version mismatch")
    require(policy.get("part") == "Part 04", "P4.06 part mismatch")
    require(policy.get("objective") == "P4.06", "P4.06 objective mismatch")
    require(policy.get("title") == "Part 04 Runtime Evidence Gate", "P4.06 title mismatch")
    require(policy.get("source_lock", {}).get("inferno_revision") == EXPECTED_INFERNO,
            "P4.06 Inferno source lock drift")

    expected_objectives = [
        "P4.01 — Runtime Session Provenance and Input Lock",
        "P4.02 — Integrated TCG Probe Capture",
        "P4.03 — Apple Silicon HVF Reference Capture",
        "P4.04 — Comparable A/B Session Assembly",
        "P4.05 — Reproducible Divergence Promotion",
        "P4.06 — Part 04 Runtime Evidence Gate",
    ]
    require(policy.get("part_04_objectives") == expected_objectives,
            "Part 04 objective list/count drift")
    require(not any(str(item).startswith("P4.07") for item in policy.get("part_04_objectives", [])),
            "P4.07 is forbidden")

    validators = policy.get("implementation_validators", [])
    require([item.get("objective") for item in validators] ==
            ["P4.01", "P4.02", "P4.03", "P4.04", "P4.05"],
            "P4.06 implementation-validator order drift")
    for item in validators:
        require(item.get("command") == "validate-policy", f"{item.get('objective')}: validator command drift")

    runtime = policy.get("runtime_contract", {})
    require(runtime.get("minimum_independent_reproductions") == 2,
            "P4.06 runtime minimum must remain two independent reproductions")
    require(runtime.get("reference") == {"machine": "vmapple", "accelerator": "hvf", "cpu": "host"},
            "P4.06 reference runtime contract drift")
    require(runtime.get("probe") == {"machine": "vmapple", "accelerator": "tcg", "cpu": "apple-gxf"},
            "P4.06 probe runtime contract drift")
    require(runtime.get("ram_mib") == 4096 and runtime.get("smp") == 4,
            "P4.06 RAM/SMP contract drift")
    require(runtime.get("accepted_outcomes") == [
        "equivalent_observations",
        "reproducible_divergence_promoted",
    ], "P4.06 accepted runtime outcomes drift")

    requirements = policy.get("requirements", {})
    for key in (
        "all_p4_implementation_policies_must_validate",
        "part_04_stays_fixed_at_six_objectives",
        "no_p4_07",
        "patch_series_must_end_at_0005",
        "root_readme_remains_frozen",
        "missing_runtime_evidence_must_not_be_fabricated",
        "runtime_pass_requires_two_independent_p4_04_sessions",
        "runtime_pass_requires_runtime_origin_candidates",
        "equivalent_outcome_is_scoped_to_trace_contract_and_capture_window",
        "divergence_outcome_requires_p4_05_promotion",
        "p1_10_remains_promotion_authority",
        "p1_10_auto_commit_remains_disabled",
        "promoted_divergence_is_not_automatically_a_hardware_requirement",
        "full_macos_boot_is_not_inferred_from_trace_equivalence",
        "future_implementation_work_must_be_evidence_driven",
        "no_new_inferno_patch_for_p4_06",
    ):
        require(requirements.get(key) is True, f"P4.06 requirement disabled: {key}")

    require(policy.get("part_status_after_implementation") ==
            "closed_implementation_complete_runtime_validation_pending",
            "P4.06 implementation-close state drift")
    require(policy.get("part_status_after_runtime_pass") == "closed_runtime_evidence_validated",
            "P4.06 runtime-close state drift")
    require(policy.get("roadmap_status_after_implementation") == "planned_implementation_complete",
            "P4.06 roadmap status drift")
    require(policy.get("next_objective") is None, "P4.06 must not create another planned objective")
    require(policy.get("next_part") is None, "P4.06 must not create another planned part")


def validate_locked_artifacts(policy: dict[str, Any]) -> list[dict[str, str]]:
    results: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in policy.get("locked_project_artifacts", []):
        rel = item.get("path")
        require(isinstance(rel, str) and rel and rel not in seen, f"invalid/duplicate locked artifact: {rel}")
        seen.add(rel)
        path = ROOT / rel
        require(path.is_file(), f"locked artifact missing: {rel}")
        observed = git_blob(path)
        require(observed == item.get("git_blob_sha"), f"locked artifact drift: {rel}: {observed}")
        results.append({
            "path": rel,
            "role": item.get("role", "locked_artifact"),
            "git_blob_sha": observed,
            "sha256": sha256_file(path),
        })
    require(any(item["path"] == "README.md" and item["git_blob_sha"] == EXPECTED_ROOT_README for item in results),
            "frozen root README lock missing")
    return results


def run_child_validators(policy: dict[str, Any]) -> list[dict[str, str]]:
    results: list[dict[str, str]] = []
    for item in policy["implementation_validators"]:
        tool = ROOT / item["tool"]
        child_policy = ROOT / item["policy"]
        require(tool.is_file(), f"{item['objective']}: tool missing")
        require(child_policy.is_file(), f"{item['objective']}: policy missing")
        proc = subprocess.run(
            [sys.executable, str(tool), "--policy", str(child_policy), item["command"]],
            text=True, capture_output=True, timeout=60,
        )
        require(proc.returncode == 0,
                f"{item['objective']} policy validator failed: {((proc.stdout or '') + (proc.stderr or '')).strip()}")
        results.append({
            "objective": item["objective"],
            "classification": "PASS",
            "tool_git_blob_sha": git_blob(tool),
            "policy_git_blob_sha": git_blob(child_policy),
        })
    return results


def repository_integrity() -> dict[str, Any]:
    patches = sorted(path.name for path in (ROOT / ".src/.patches").glob("*.patch"))
    expected = [
        "0001-vmapple-decouple-build-from-hvf.patch",
        "0002-vmapple-optional-apple-pvg.patch",
        "0003-arm-apple-sysreg-framework.patch",
        "0004-arm-apple-sysreg-policy-model.patch",
        "0005-arm-vmapple-feature-contract.patch",
    ]
    require(patches == expected, f"compatibility patch series drift: {patches}")
    require(git_blob(ROOT / "README.md") == EXPECTED_ROOT_README, "root README blob drift")

    proc = subprocess.run(
        ["git", "-C", str(ROOT), "ls-files", "-s", ".src/.upstream/.inferno"],
        text=True, capture_output=True, timeout=15,
    )
    require(proc.returncode == 0, f"could not inspect Inferno gitlink: {(proc.stderr or '').strip()}")
    fields = proc.stdout.strip().split()
    require(len(fields) >= 2 and fields[0] == "160000" and fields[1] == EXPECTED_INFERNO,
            f"Inferno gitlink drift: {proc.stdout.strip()}")
    return {
        "patch_count": 5,
        "last_patch": expected[-1],
        "inferno_revision": EXPECTED_INFERNO,
        "inferno_mode": "160000",
        "root_readme_git_blob_sha": EXPECTED_ROOT_README,
    }


def implementation_state(policy: dict[str, Any]) -> dict[str, Any]:
    validate_policy(policy)
    locked = validate_locked_artifacts(policy)
    validators = run_child_validators(policy)
    integrity = repository_integrity()
    result = {
        "schema": 1,
        "classification": "P4_06_IMPLEMENTATION_COMPLETE_RUNTIME_EVIDENCE_PENDING",
        "project_version": EXPECTED_VERSION,
        "part": "Part 04",
        "objective": "P4.06",
        "planned_implementation_complete": True,
        "runtime_evidence_validated": False,
        "runtime_gate_passed": False,
        "part_status": policy["part_status_after_implementation"],
        "roadmap_status": policy["roadmap_status_after_implementation"],
        "implementation_validators": validators,
        "locked_artifacts": locked,
        "repository_integrity": integrity,
        "runtime_requirement": {
            "minimum_independent_reproductions": policy["runtime_contract"]["minimum_independent_reproductions"],
            "accepted_outcomes": list(policy["runtime_contract"]["accepted_outcomes"]),
            "real_p4_02_probe_required": True,
            "real_p4_03_apple_silicon_hvf_reference_required": True,
            "missing_evidence_is_a_pending_state_not_a_pass": True,
        },
        "claims": {
            "macos_boot_success_proven": False,
            "apple_gxf_runtime_sufficiency_proven": False,
            "modern_macos_compatibility_proven": False,
        },
        "next_objective": None,
        "next_part": None,
        "future_work": "runtime_evidence_or_explicit_scope_change_only",
    }
    basis = {k: v for k, v in result.items() if k != "classification"}
    result["implementation_fingerprint"] = sha256_bytes(canonical_line(basis))
    return result


def verify_p405_promotion_fingerprint(data: dict[str, Any]) -> None:
    observed = data.get("promotion_fingerprint")
    require(is_sha256(observed), "P4.05 promotion fingerprint invalid")
    payload = {k: v for k, v in data.items() if k not in ("classification", "promotion_fingerprint")}
    expected = sha256_bytes(canonical_line(payload))
    require(observed == expected, "P4.05 promotion fingerprint does not reproduce")


def validate_p405_promotion(data: dict[str, Any], policy: dict[str, Any]) -> None:
    require(data.get("schema") == 1, "P4.05 promotion schema mismatch")
    require(data.get("classification") == "P4_05_REPRODUCIBLE_DIVERGENCE_PROMOTED",
            "P4.05 record is not a reproducible promoted divergence")
    require(data.get("project_version") == EXPECTED_P405_VERSION, "P4.05 promotion version mismatch")
    require(data.get("part") == "Part 04" and data.get("objective") == "P4.05",
            "P4.05 promotion identity drift")
    require(data.get("guest_execution") is False, "P4.05 wrapper unexpectedly claims guest execution")
    require(data.get("runtime_evidence_consumed") is True, "P4.05 did not consume runtime evidence")
    require(data.get("divergence_promoted") is True, "P4.05 record did not promote a divergence")
    require(data.get("next_objective") == "P4.06", "P4.05 promotion next-objective drift")
    verify_p405_promotion_fingerprint(data)

    shared = data.get("shared_contract", {})
    require(shared.get("source_revision") == EXPECTED_INFERNO, "P4.05 shared Inferno revision drift")
    require(shared.get("machine") == "vmapple", "P4.05 shared machine drift")
    require(shared.get("ram_mib") == policy["runtime_contract"]["ram_mib"]
            and shared.get("smp") == policy["runtime_contract"]["smp"], "P4.05 shared RAM/SMP drift")
    require(is_sha256(shared.get("platform_integration_fingerprint")),
            "P4.05 platform integration fingerprint invalid")

    authority = data.get("promotion_authority", {})
    require(authority.get("stage") == "P1.10", "P4.05 promotion authority drift")
    require(authority.get("id") == "P01-DIVERGENCE-0001", "P1.10 promotion id drift")
    require(authority.get("status") == "promoted", "P1.10 promotion status drift")
    require(authority.get("auto_committed") is False, "P1.10 auto-commit unexpectedly enabled")
    minimum = policy["runtime_contract"]["minimum_independent_reproductions"]
    require(isinstance(authority.get("reproduction_count"), int)
            and authority["reproduction_count"] >= minimum, "P1.10 reproduction count too small")
    require(is_sha256(authority.get("divergence_signature")), "P1.10 divergence signature invalid")
    require(is_sha256(authority.get("contract_fingerprint")), "P1.10 contract fingerprint invalid")

    reproductions = data.get("reproductions", [])
    require(isinstance(reproductions, list) and len(reproductions) == authority["reproduction_count"],
            "P4.05 reproduction list/count mismatch")
    unique_keys = (
        "ab_fingerprint", "reference_run_id", "probe_run_id",
        "reference_capture_fingerprint", "probe_capture_fingerprint",
    )
    for key in unique_keys:
        values = [item.get(key) for item in reproductions]
        require(all(values) and len(values) == len(set(values)), f"P4.05 reproductions are not independent at {key}")
    require({item.get("divergence_signature") for item in reproductions} == {authority["divergence_signature"]},
            "P4.05 reproduction divergence signatures disagree with P1.10")
    require({item.get("contract_fingerprint") for item in reproductions} == {authority["contract_fingerprint"]},
            "P4.05 reproduction contract fingerprints disagree with P1.10")
    sanitization = data.get("sanitization", {})
    require(sanitization.get("raw_local_paths_stored") is False
            and sanitization.get("raw_uuid_stored") is False
            and sanitization.get("guest_input_contents_stored") is False,
            "P4.05 sanitization contract drift")


def run_p1_candidate(
    ab_bundle: dict[str, Any],
    reference_manifest_path: Path,
    probe_manifest_path: Path,
    reference_trace_path: Path,
    probe_trace_path: Path,
    output_dir: Path,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(
        [
            sys.executable, str(P1_TOOL), "candidate",
            "--reference-manifest", str(reference_manifest_path),
            "--probe-manifest", str(probe_manifest_path),
            "--reference-trace", str(reference_trace_path),
            "--probe-trace", str(probe_trace_path),
            "--output-dir", str(output_dir),
            "--policy", str(P1_POLICY),
        ],
        text=True, capture_output=True, timeout=120,
    )
    require(proc.returncode == 0,
            f"P1.10 candidate evaluation failed: {((proc.stdout or '') + (proc.stderr or '')).strip()}")
    candidate_path = output_dir / "candidate.json"
    require(candidate_path.is_file(), "P1.10 candidate output missing")
    candidate = load_json(candidate_path)
    require(candidate.get("evidence_origin") == "runtime", "P4.06 candidate is not runtime-origin evidence")
    require(candidate.get("reference_run_id") == ab_bundle["reference"]["run_id"],
            "candidate reference run does not bind P4.04 session")
    require(candidate.get("probe_run_id") == ab_bundle["probe"]["run_id"],
            "candidate probe run does not bind P4.04 session")
    require(candidate.get("status") in ("no_divergence", "divergence_candidate"),
            "unexpected P1.10 candidate status")
    if candidate["status"] == "divergence_candidate":
        require(candidate.get("promotion_eligible") is True and is_sha256(candidate.get("divergence_signature")),
                "runtime divergence candidate is not promotion-eligible")
    else:
        require(candidate.get("promotion_eligible") is False and candidate.get("divergence_signature") is None,
                "no-divergence candidate has inconsistent promotion state")
    return candidate


def evaluate_runtime(args: argparse.Namespace, policy: dict[str, Any]) -> dict[str, Any]:
    validate_policy(policy)
    validate_locked_artifacts(policy)
    run_child_validators(policy)
    repository_integrity()
    require(P405_TOOL.is_file() and P405_POLICY.is_file(), "P4.05 tool/policy missing")

    p405 = load_module("applesilicon_p405_for_p406", P405_TOOL)
    p405_policy = p405.load_json(P405_POLICY)
    p405.validate_policy(p405_policy)
    p405.validate_locked_artifacts(p405_policy)
    p1_policy = p405.load_p1_policy()

    items: list[dict[str, Any]] = []
    for group in args.reproduction:
        ab_path, ref_manifest_path, probe_manifest_path, ref_trace_path, probe_trace_path = map(Path, group)
        for label, path in (
            ("P4.04 A/B session", ab_path),
            ("reference manifest", ref_manifest_path),
            ("probe manifest", probe_manifest_path),
            ("reference trace", ref_trace_path),
            ("probe trace", probe_trace_path),
        ):
            require(path.is_file(), f"{label} missing: {path}")
        bundle = load_json(ab_path)
        ref_manifest = load_json(ref_manifest_path)
        probe_manifest = load_json(probe_manifest_path)
        p405.validate_ab_bundle(
            bundle, ref_manifest, probe_manifest,
            ref_manifest_path, probe_manifest_path, p405_policy,
        )
        items.append({
            "ab_path": ab_path,
            "bundle": bundle,
            "reference_manifest_path": ref_manifest_path,
            "probe_manifest_path": probe_manifest_path,
            "reference_trace_path": ref_trace_path,
            "probe_trace_path": probe_trace_path,
        })

    items.sort(key=lambda item: item["bundle"]["ab_fingerprint"])
    p405.validate_reproduction_set(items, p405_policy, p1_policy)
    minimum = policy["runtime_contract"]["minimum_independent_reproductions"]
    require(len(items) >= minimum, f"P4.06 requires at least {minimum} independent P4.04 sessions")

    work_dir = Path(args.work_dir)
    candidate_root = work_dir / "candidates"
    candidates: list[dict[str, Any]] = []
    for index, item in enumerate(items, start=1):
        candidate = run_p1_candidate(
            item["bundle"],
            item["reference_manifest_path"],
            item["probe_manifest_path"],
            item["reference_trace_path"],
            item["probe_trace_path"],
            candidate_root / f"{index:02d}",
        )
        item["candidate"] = candidate
        candidates.append(candidate)

    statuses = {item["status"] for item in candidates}
    require(len(statuses) == 1, f"runtime reproductions do not agree on outcome: {sorted(statuses)}")
    status = next(iter(statuses))

    observations = [{
        "index": index,
        "ab_fingerprint": item["bundle"]["ab_fingerprint"],
        "reference_run_id": item["bundle"]["reference"]["run_id"],
        "probe_run_id": item["bundle"]["probe"]["run_id"],
        "reference_capture_fingerprint": item["bundle"]["reference"]["capture_fingerprint"],
        "probe_capture_fingerprint": item["bundle"]["probe"]["capture_fingerprint"],
        "candidate_id": item["candidate"]["candidate_id"],
        "candidate_status": item["candidate"]["status"],
        "contract_fingerprint": item["candidate"]["contract_fingerprint"],
        "divergence_signature": item["candidate"]["divergence_signature"],
    } for index, item in enumerate(items, start=1)]

    base = {
        "schema": 1,
        "project_version": EXPECTED_VERSION,
        "part": "Part 04",
        "objective": "P4.06",
        "planned_implementation_complete": True,
        "runtime_evidence_validated": True,
        "runtime_gate_passed": True,
        "part_status": policy["part_status_after_runtime_pass"],
        "roadmap_status": "planned_roadmap_complete_runtime_evidence_validated",
        "shared_contract": copy.deepcopy(items[0]["bundle"]["shared_contract"]),
        "observations": observations,
        "claims": {
            "macos_boot_success_proven": False,
            "full_modern_macos_compatibility_proven": False,
            "trace_scope_only": True,
        },
        "next_objective": None,
        "next_part": None,
    }

    contracts = {item["contract_fingerprint"] for item in candidates}
    require(len(contracts) == 1, "runtime candidates do not share one P1.09 contract fingerprint")

    if status == "no_divergence":
        require(args.promotion is None, "a P4.05 promotion record cannot accompany a no-divergence outcome")
        base["classification"] = "P4_06_RUNTIME_EVIDENCE_PASS_EQUIVALENT_OBSERVATIONS"
        base["runtime_outcome"] = "equivalent_observations"
        base["evidence_interpretation"] = (
            "No canonical divergence was observed across the reproduced P1.08 trace contract and capture window. "
            "This is not proof of a full macOS boot or complete hardware equivalence."
        )
        base["future_work"] = "broaden_runtime_scope_only_if_new_evidence_or_explicit_scope_change_requires_it"
    else:
        signatures = {item["divergence_signature"] for item in candidates}
        require(len(signatures) == 1, "runtime divergence candidates do not reproduce one signature")
        require(args.promotion is not None, "reproducible divergence requires the P4.05 promotion record")
        promotion_path = Path(args.promotion)
        require(promotion_path.is_file(), f"P4.05 promotion record missing: {promotion_path}")
        promotion = load_json(promotion_path)
        validate_p405_promotion(promotion, policy)
        authority = promotion["promotion_authority"]
        require(authority["divergence_signature"] == next(iter(signatures)),
                "P4.05 promotion signature differs from P4.06 observations")
        require(authority["contract_fingerprint"] == next(iter(contracts)),
                "P4.05 promotion contract differs from P4.06 observations")
        promoted_ab = {item["ab_fingerprint"] for item in promotion["reproductions"]}
        observed_ab = {item["bundle"]["ab_fingerprint"] for item in items}
        require(promoted_ab == observed_ab, "P4.05 promotion does not bind the exact P4.06 A/B reproduction set")

        base["classification"] = "P4_06_RUNTIME_EVIDENCE_PASS_PROMOTED_DIVERGENCE"
        base["runtime_outcome"] = "reproducible_divergence_promoted"
        base["promotion"] = {
            "sha256": sha256_file(promotion_path),
            "promotion_fingerprint": promotion["promotion_fingerprint"],
            "authority_id": authority["id"],
            "divergence_signature": authority["divergence_signature"],
            "contract_fingerprint": authority["contract_fingerprint"],
            "reproduction_count": authority["reproduction_count"],
            "auto_committed": False,
        }
        base["evidence_interpretation"] = (
            "A reproducible runtime divergence was promoted by P1.10. "
            "The divergence is evidence for investigation, not an automatically inferred hardware requirement."
        )
        base["future_work"] = "evidence_driven_fix_or_new_part_only_after_interpreting_promoted_divergence"

    fingerprint_basis = {k: v for k, v in base.items() if k != "classification"}
    base["runtime_gate_fingerprint"] = sha256_bytes(canonical_line(fingerprint_basis))
    return base


def synthetic_p405_record(policy: dict[str, Any]) -> dict[str, Any]:
    shared = {
        "source_revision": EXPECTED_INFERNO,
        "machine": "vmapple",
        "ram_mib": policy["runtime_contract"]["ram_mib"],
        "smp": policy["runtime_contract"]["smp"],
        "platform_integration_fingerprint": "1" * 64,
    }
    sig = "2" * 64
    contract = "3" * 64
    reps = []
    for idx in range(2):
        suffix = str(idx + 1)
        reps.append({
            "index": idx + 1,
            "ab_fingerprint": suffix * 64,
            "ab_session_sha256": "a" * 64,
            "reference_run_id": f"ref-{suffix}",
            "probe_run_id": f"probe-{suffix}",
            "reference_capture_fingerprint": ("4" if idx == 0 else "5") * 64,
            "probe_capture_fingerprint": ("6" if idx == 0 else "7") * 64,
            "candidate_id": f"candidate-{suffix}",
            "candidate_sha256": "b" * 64,
            "divergence_signature": sig,
            "contract_fingerprint": contract,
        })
    record = {
        "schema": 1,
        "classification": "P4_05_REPRODUCIBLE_DIVERGENCE_PROMOTED",
        "project_version": EXPECTED_P405_VERSION,
        "part": "Part 04",
        "objective": "P4.05",
        "guest_execution": False,
        "runtime_evidence_consumed": True,
        "divergence_promoted": True,
        "shared_contract": shared,
        "promotion_authority": {
            "stage": "P1.10",
            "id": "P01-DIVERGENCE-0001",
            "status": "promoted",
            "record_sha256": "c" * 64,
            "reproduction_count": 2,
            "divergence_signature": sig,
            "contract_fingerprint": contract,
            "classification": "value_mismatch",
            "auto_committed": False,
        },
        "reproductions": reps,
        "sanitization": {
            "raw_local_paths_stored": False,
            "raw_uuid_stored": False,
            "guest_input_contents_stored": False,
        },
        "next_objective": "P4.06",
    }
    payload = {k: v for k, v in record.items() if k != "classification"}
    record["promotion_fingerprint"] = sha256_bytes(canonical_line(payload))
    return record


def expect_policy_failure(policy: dict[str, Any], mutate, label: str) -> None:
    broken = copy.deepcopy(policy)
    mutate(broken)
    try:
        validate_policy(broken)
    except GateError:
        print(f"self-check reject: PASS: {label}")
        return
    raise GateError(f"self-check mutation was accepted: {label}")


def expect_promotion_failure(policy: dict[str, Any], mutate, label: str) -> None:
    broken = synthetic_p405_record(policy)
    mutate(broken)
    if "promotion_fingerprint" in broken:
        payload = {k: v for k, v in broken.items() if k not in ("classification", "promotion_fingerprint")}
        broken["promotion_fingerprint"] = sha256_bytes(canonical_line(payload))
    try:
        validate_p405_promotion(broken, policy)
    except GateError:
        print(f"self-check reject: PASS: {label}")
        return
    raise GateError(f"self-check promotion mutation was accepted: {label}")


def self_check(policy: dict[str, Any]) -> None:
    validate_policy(policy)
    validate_locked_artifacts(policy)
    validate_p405_promotion(synthetic_p405_record(policy), policy)
    expect_policy_failure(policy, lambda d: d["runtime_contract"].__setitem__("minimum_independent_reproductions", 1),
                          "single-reproduction runtime pass")
    expect_policy_failure(policy, lambda d: d["requirements"].__setitem__("missing_runtime_evidence_must_not_be_fabricated", False),
                          "fabricated runtime pass")
    expect_policy_failure(policy, lambda d: d["part_04_objectives"].append("P4.07 — Scope Creep"), "P4.07 scope creep")
    expect_policy_failure(policy, lambda d: d.__setitem__("next_part", "Part 05"), "automatic Part 05 creation")
    expect_promotion_failure(policy, lambda d: d["promotion_authority"].__setitem__("auto_committed", True),
                             "P1.10 auto-commit")
    expect_promotion_failure(policy, lambda d: d["promotion_authority"].__setitem__("reproduction_count", 1),
                             "promotion with one reproduction")
    expect_promotion_failure(policy, lambda d: d["reproductions"][1].__setitem__("reference_run_id", "ref-1"),
                             "reused reference run")
    print("P4.06 self-check: PASS")


def write_result(path: str | None, data: dict[str, Any]) -> None:
    raw = canonical_line(data)
    if path:
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(raw)
    sys.stdout.buffer.write(raw)


def main() -> int:
    parser = argparse.ArgumentParser(description="AppleSilicon P4.06 final runtime evidence gate")
    parser.add_argument("--policy", default=str(DEFAULT_POLICY))
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("validate-policy")
    sub.add_parser("self-check")
    impl = sub.add_parser("implementation")
    impl.add_argument("--output")
    ev = sub.add_parser("evaluate")
    ev.add_argument("--reproduction", action="append", nargs=5, required=True,
                    metavar=("AB_SESSION", "REFERENCE_MANIFEST", "PROBE_MANIFEST", "REFERENCE_TRACE", "PROBE_TRACE"))
    ev.add_argument("--promotion")
    ev.add_argument("--work-dir", required=True)
    ev.add_argument("--output")
    args = parser.parse_args()

    try:
        policy = load_json(Path(args.policy))
        validate_policy(policy)
        if args.command == "validate-policy":
            validate_locked_artifacts(policy)
            print("P4.06 policy: PASS")
            return 0
        if args.command == "self-check":
            self_check(policy)
            return 0
        if args.command == "implementation":
            write_result(args.output, implementation_state(policy))
            return 0
        write_result(args.output, evaluate_runtime(args, policy))
        return 0
    except (GateError, OSError, subprocess.TimeoutExpired) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

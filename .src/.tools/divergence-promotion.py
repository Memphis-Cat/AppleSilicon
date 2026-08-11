#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_POLICY = ROOT / ".src/.configs/p4.05-divergence-promotion-policy.json"
P1_POLICY = ROOT / ".src/.configs/p1.10-promotion-policy.json"
P1_TOOL = ROOT / ".src/.tools/evidence-bundle.py"
EXPECTED_VERSION = "4.4.0.0.0.0"
EXPECTED_AB_VERSION = "4.3.0.0.0.0"
EXPECTED_INFERNO = "cc4302a99167abec69b714cfd00c38caece7e7de"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class PromotionError(RuntimeError):
    pass


def require(value: bool, message: str) -> None:
    if not value:
        raise PromotionError(message)


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PromotionError(f"could not read JSON {path}: {exc}") from exc
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
        raise PromotionError(f"could not hash {path}: {exc}") from exc
    return h.hexdigest()


def git_blob(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def object_digest(value: Any) -> str:
    return sha256_bytes(canonical(value))


def get_path(data: dict[str, Any], dotted: str) -> Any:
    value: Any = data
    for part in dotted.split("."):
        require(isinstance(value, dict) and part in value, f"missing required field: {dotted}")
        value = value[part]
    return value


def validate_policy(policy: dict[str, Any]) -> None:
    require(policy.get("schema") == 1, "P4.05 schema mismatch")
    require(policy.get("project_version") == EXPECTED_VERSION, "P4.05 version mismatch")
    require(policy.get("part") == "Part 04", "P4.05 part mismatch")
    require(policy.get("objective") == "P4.05", "P4.05 objective mismatch")
    require(policy.get("title") == "Reproducible Divergence Promotion", "P4.05 title mismatch")
    require(policy.get("source_lock", {}).get("inferno_revision") == EXPECTED_INFERNO,
            "P4.05 Inferno source lock drift")
    contract = policy.get("input_contract", {})
    require(contract.get("ab_classification") == "P4_04_AB_SESSION_READY", "P4.05 A/B classification drift")
    require(contract.get("ab_project_version") == EXPECTED_AB_VERSION, "P4.05 A/B version drift")
    require(contract.get("minimum_reproductions") == 2, "P4.05 minimum reproduction count must remain 2")
    require(contract.get("reference_accelerator") == "hvf" and contract.get("reference_cpu") == "host",
            "P4.05 reference role drift")
    require(contract.get("probe_accelerator") == "tcg" and contract.get("probe_cpu") == "apple-gxf",
            "P4.05 probe role drift")
    for path in ("shared_contract", "reference.qemu", "probe.qemu", "reference.machine", "probe.machine"):
        require(path in policy.get("reproduction_equal_paths", []), f"P4.05 equality path missing: {path}")
    for path in ("ab_fingerprint", "reference.run_id", "probe.run_id",
                 "reference.capture_fingerprint", "probe.capture_fingerprint"):
        require(path in policy.get("reproduction_unique_paths", []), f"P4.05 uniqueness path missing: {path}")
    for key, value in policy.get("requirements", {}).items():
        require(value is True, f"P4.05 requirement disabled: {key}")
    require(policy.get("next_objective") == "P4.06", "P4.05 next objective must be P4.06")


def validate_locked_artifacts(policy: dict[str, Any]) -> None:
    seen: set[str] = set()
    for item in policy.get("locked_project_artifacts", []):
        rel = item.get("path")
        require(isinstance(rel, str) and rel and rel not in seen, f"invalid/duplicate locked artifact: {rel}")
        seen.add(rel)
        path = ROOT / rel
        require(path.is_file(), f"locked artifact missing: {rel}")
        observed = git_blob(path)
        require(observed == item.get("git_blob_sha"), f"locked artifact drift: {rel}: {observed}")


def load_p1_policy() -> dict[str, Any]:
    policy = load_json(P1_POLICY)
    require(policy.get("schema") == 1, "P1.10 policy schema mismatch")
    require(isinstance(policy.get("minimum_reproductions"), int) and policy["minimum_reproductions"] >= 2,
            "P1.10 minimum reproduction count weakened")
    require(policy.get("require_unique_run_pairs") is True, "P1.10 unique run-pair gate disabled")
    require(policy.get("require_same_contract_fingerprint") is True, "P1.10 contract gate disabled")
    require(policy.get("require_same_divergence_signature") is True, "P1.10 signature gate disabled")
    require(policy.get("auto_commit_promotion") is False, "P1.10 auto-commit must remain disabled")
    return policy


def verify_ab_fingerprint(bundle: dict[str, Any]) -> None:
    observed = bundle.get("ab_fingerprint")
    require(isinstance(observed, str) and SHA256_RE.fullmatch(observed) is not None,
            "P4.04 A/B fingerprint invalid")
    payload = {k: v for k, v in bundle.items() if k not in ("classification", "ab_fingerprint")}
    require(observed == sha256_bytes(canonical_line(payload)), "P4.04 A/B fingerprint does not reproduce")


def validate_ab_bundle(bundle: dict[str, Any], reference_manifest: dict[str, Any], probe_manifest: dict[str, Any],
                       reference_manifest_path: Path, probe_manifest_path: Path, policy: dict[str, Any]) -> None:
    contract = policy["input_contract"]
    require(bundle.get("schema") == 1, "P4.04 bundle schema mismatch")
    require(bundle.get("classification") == contract["ab_classification"], "P4.04 bundle is not admitted")
    require(bundle.get("project_version") == contract["ab_project_version"], "P4.04 bundle version mismatch")
    require(bundle.get("part") == "Part 04" and bundle.get("objective") == "P4.04", "P4.04 bundle identity drift")
    require(bundle.get("runtime_observation") is True, "P4.04 bundle is not runtime-derived")
    require(bundle.get("divergence_promoted") is False, "P4.04 bundle already claims a promoted divergence")
    verify_ab_fingerprint(bundle)
    shared = bundle.get("shared_contract", {})
    require(shared.get("source_revision") == EXPECTED_INFERNO, "P4.04 shared source revision drift")
    require(shared.get("machine") == "vmapple", "P4.04 shared machine drift")
    require(shared.get("ram_mib") == 4096 and shared.get("smp") == 4, "P4.04 RAM/SMP drift")
    require(bundle.get("p1_09_pairing", {}).get("comparable") is True, "P4.04 P1.09 pair is not comparable")
    require(bundle.get("p1_09_pairing", {}).get("contract_mismatches") == [], "P4.04 P1.09 pair contains mismatches")

    ref = bundle.get("reference", {})
    probe = bundle.get("probe", {})
    require(ref.get("machine") == {"type": "vmapple", "accelerator": contract["reference_accelerator"],
                                   "cpu_model": contract["reference_cpu"]}, "P4.04 reference machine drift")
    require(probe.get("machine") == {"type": "vmapple", "accelerator": contract["probe_accelerator"],
                                     "cpu_model": contract["probe_cpu"]}, "P4.04 probe machine drift")
    require(ref.get("manifest_sha256") == sha256_file(reference_manifest_path),
            "P4.04 reference manifest binding mismatch")
    require(probe.get("manifest_sha256") == sha256_file(probe_manifest_path),
            "P4.04 probe manifest binding mismatch")
    require(reference_manifest.get("role") == "reference" and probe_manifest.get("role") == "probe",
            "P1.09 manifest roles are invalid")
    require(ref.get("run_id") == reference_manifest.get("run", {}).get("id"), "reference run id binding mismatch")
    require(probe.get("run_id") == probe_manifest.get("run", {}).get("id"), "probe run id binding mismatch")
    require(ref.get("result") == reference_manifest.get("run", {}).get("result"), "reference result binding mismatch")
    require(probe.get("result") == probe_manifest.get("run", {}).get("result"), "probe result binding mismatch")
    require(reference_manifest.get("source", {}).get("revision") == EXPECTED_INFERNO,
            "reference manifest source revision drift")
    require(probe_manifest.get("source", {}).get("revision") == EXPECTED_INFERNO,
            "probe manifest source revision drift")


def validate_reproduction_set(items: list[dict[str, Any]], policy: dict[str, Any], p1_policy: dict[str, Any]) -> None:
    minimum = max(policy["input_contract"]["minimum_reproductions"], p1_policy["minimum_reproductions"])
    require(len(items) >= minimum, f"P4.05 requires at least {minimum} independent P4.04 reproductions")
    first = items[0]["bundle"]
    for path in policy["reproduction_equal_paths"]:
        expected = get_path(first, path)
        for index, item in enumerate(items[1:], start=2):
            require(get_path(item["bundle"], path) == expected,
                    f"reproduction {index} differs at required-equal path: {path}")
    for path in policy["reproduction_unique_paths"]:
        values = [json.dumps(get_path(item["bundle"], path), sort_keys=True) for item in items]
        require(len(values) == len(set(values)), f"reproductions are not independent at path: {path}")


def run_p1_candidate(item: dict[str, Any], output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run([
        sys.executable, str(P1_TOOL), "candidate",
        "--reference-manifest", str(item["reference_manifest_path"]),
        "--probe-manifest", str(item["probe_manifest_path"]),
        "--reference-trace", str(item["reference_trace_path"]),
        "--probe-trace", str(item["probe_trace_path"]),
        "--output-dir", str(output_dir),
        "--policy", str(P1_POLICY),
    ], text=True, capture_output=True, timeout=120)
    if proc.returncode != 0:
        detail = ((proc.stdout or "") + (proc.stderr or "")).strip()
        raise PromotionError(f"P1.10 candidate generation rejected reproduction: {detail}")
    candidate_path = output_dir / "candidate.json"
    require(candidate_path.is_file(), "P1.10 candidate output missing")
    candidate = load_json(candidate_path)
    require(candidate.get("status") == "divergence_candidate", "P1.10 found no divergence in an admitted reproduction")
    require(candidate.get("evidence_origin") == "runtime", "P1.10 candidate is not runtime evidence")
    require(candidate.get("promotion_eligible") is True, "P1.10 candidate is not promotion eligible")
    require(isinstance(candidate.get("divergence_signature"), str)
            and SHA256_RE.fullmatch(candidate["divergence_signature"]) is not None,
            "P1.10 candidate divergence signature invalid")
    require(candidate.get("reference_run_id") == item["bundle"]["reference"]["run_id"],
            "P1.10 candidate reference run differs from P4.04 bundle")
    require(candidate.get("probe_run_id") == item["bundle"]["probe"]["run_id"],
            "P1.10 candidate probe run differs from P4.04 bundle")
    require(candidate.get("reference_manifest_sha256") == object_digest(item["reference_manifest"]),
            "P1.10 candidate reference manifest digest mismatch")
    require(candidate.get("probe_manifest_sha256") == object_digest(item["probe_manifest"]),
            "P1.10 candidate probe manifest digest mismatch")
    item["candidate_path"] = candidate_path
    item["candidate"] = candidate
    return candidate


def run_p1_promote(items: list[dict[str, Any]], output_dir: Path) -> tuple[Path, dict[str, Any]]:
    args = [sys.executable, str(P1_TOOL), "promote", "--output-dir", str(output_dir), "--policy", str(P1_POLICY)]
    for item in items:
        args.extend(["--candidate", str(item["candidate_path"])])
    proc = subprocess.run(args, text=True, capture_output=True, timeout=60)
    if proc.returncode != 0:
        detail = ((proc.stdout or "") + (proc.stderr or "")).strip()
        raise PromotionError(f"P1.10 promotion gate rejected reproduced candidates: {detail}")
    record_path = output_dir / "P01-DIVERGENCE-0001.json"
    require(record_path.is_file(), "P1.10 promotion record missing")
    record = load_json(record_path)
    require(record.get("id") == "P01-DIVERGENCE-0001", "unexpected P1.10 promotion id")
    require(record.get("status") == "promoted", "P1.10 record was not promoted")
    require(record.get("auto_committed") is False, "P1.10 unexpectedly auto-committed promotion")
    require(record.get("reproduction_count") == len(items), "P1.10 reproduction count mismatch")
    return record_path, record


def build_output(items: list[dict[str, Any]], p1_record_path: Path, p1_record: dict[str, Any]) -> dict[str, Any]:
    reproductions = []
    for index, item in enumerate(items, start=1):
        candidate = item["candidate"]
        reproductions.append({
            "index": index,
            "ab_fingerprint": item["bundle"]["ab_fingerprint"],
            "ab_session_sha256": sha256_file(item["ab_path"]),
            "reference_run_id": candidate["reference_run_id"],
            "probe_run_id": candidate["probe_run_id"],
            "reference_capture_fingerprint": item["bundle"]["reference"]["capture_fingerprint"],
            "probe_capture_fingerprint": item["bundle"]["probe"]["capture_fingerprint"],
            "candidate_id": candidate["candidate_id"],
            "candidate_sha256": sha256_file(item["candidate_path"]),
            "divergence_signature": candidate["divergence_signature"],
            "contract_fingerprint": candidate["contract_fingerprint"],
        })
    result = {
        "schema": 1,
        "classification": "P4_05_REPRODUCIBLE_DIVERGENCE_PROMOTED",
        "project_version": EXPECTED_VERSION,
        "part": "Part 04",
        "objective": "P4.05",
        "guest_execution": False,
        "runtime_evidence_consumed": True,
        "divergence_promoted": True,
        "shared_contract": copy.deepcopy(items[0]["bundle"]["shared_contract"]),
        "promotion_authority": {
            "stage": "P1.10",
            "id": p1_record["id"],
            "status": p1_record["status"],
            "record_sha256": sha256_file(p1_record_path),
            "reproduction_count": p1_record["reproduction_count"],
            "divergence_signature": p1_record["divergence_signature"],
            "contract_fingerprint": p1_record["contract_fingerprint"],
            "classification": p1_record["classification"],
            "auto_committed": p1_record["auto_committed"],
        },
        "reproductions": reproductions,
        "sanitization": {
            "raw_local_paths_stored": False,
            "raw_uuid_stored": False,
            "guest_input_contents_stored": False,
        },
        "next_objective": "P4.06",
    }
    result["promotion_fingerprint"] = sha256_bytes(canonical_line({k: v for k, v in result.items() if k != "classification"}))
    return result


def promote(args: argparse.Namespace, policy: dict[str, Any]) -> dict[str, Any]:
    validate_policy(policy)
    validate_locked_artifacts(policy)
    p1_policy = load_p1_policy()
    require(policy["input_contract"]["minimum_reproductions"] >= p1_policy["minimum_reproductions"],
            "P4.05 reproduction threshold is weaker than P1.10")
    require(P1_TOOL.is_file(), "P1.10 evidence tool missing")

    items: list[dict[str, Any]] = []
    for group in args.reproduction:
        ab_path, ref_manifest_path, probe_manifest_path, ref_trace_path, probe_trace_path = map(Path, group)
        for label, path in (("P4.04 A/B session", ab_path), ("reference manifest", ref_manifest_path),
                            ("probe manifest", probe_manifest_path), ("reference trace", ref_trace_path),
                            ("probe trace", probe_trace_path)):
            require(path.is_file() and path.is_file(), f"{label} missing: {path}")
        bundle = load_json(ab_path)
        reference_manifest = load_json(ref_manifest_path)
        probe_manifest = load_json(probe_manifest_path)
        validate_ab_bundle(bundle, reference_manifest, probe_manifest, ref_manifest_path, probe_manifest_path, policy)
        items.append({
            "ab_path": ab_path,
            "reference_manifest_path": ref_manifest_path,
            "probe_manifest_path": probe_manifest_path,
            "reference_trace_path": ref_trace_path,
            "probe_trace_path": probe_trace_path,
            "bundle": bundle,
            "reference_manifest": reference_manifest,
            "probe_manifest": probe_manifest,
        })

    items.sort(key=lambda item: item["bundle"]["ab_fingerprint"])
    validate_reproduction_set(items, policy, p1_policy)

    work_dir = Path(args.work_dir)
    candidate_root = work_dir / "candidates"
    p1_output = work_dir / "p1.10"
    candidate_root.mkdir(parents=True, exist_ok=True)
    p1_output.mkdir(parents=True, exist_ok=True)
    for index, item in enumerate(items, start=1):
        run_p1_candidate(item, candidate_root / f"{index:02d}")

    signatures = {item["candidate"]["divergence_signature"] for item in items}
    contracts = {item["candidate"]["contract_fingerprint"] for item in items}
    require(len(signatures) == 1, "P4.05 candidates do not reproduce the same divergence signature")
    require(len(contracts) == 1, "P4.05 candidates do not share the same P1.09 contract fingerprint")

    p1_record_path, p1_record = run_p1_promote(items, p1_output)
    require(p1_record["divergence_signature"] == next(iter(signatures)), "P1.10 promoted a different divergence signature")
    require(p1_record["contract_fingerprint"] == next(iter(contracts)), "P1.10 promoted a different contract fingerprint")
    return build_output(items, p1_record_path, p1_record)


def expect_policy_failure(policy: dict[str, Any], mutate, label: str) -> None:
    broken = copy.deepcopy(policy)
    mutate(broken)
    try:
        validate_policy(broken)
    except PromotionError:
        print(f"self-check reject: PASS: {label}")
        return
    raise PromotionError(f"self-check mutation was accepted: {label}")


def self_check(policy: dict[str, Any]) -> None:
    validate_policy(policy)
    validate_locked_artifacts(policy)
    p1_policy = load_p1_policy()
    require(policy["input_contract"]["minimum_reproductions"] >= p1_policy["minimum_reproductions"],
            "P4.05 threshold is weaker than P1.10")
    expect_policy_failure(policy, lambda d: d["input_contract"].__setitem__("minimum_reproductions", 1),
                          "single-pair promotion")
    expect_policy_failure(policy, lambda d: d["reproduction_unique_paths"].remove("reference.run_id"),
                          "reference-run reuse")
    expect_policy_failure(policy, lambda d: d["reproduction_unique_paths"].remove("probe.run_id"),
                          "probe-run reuse")
    expect_policy_failure(policy, lambda d: d["reproduction_equal_paths"].remove("shared_contract"),
                          "shared-contract drift")
    expect_policy_failure(policy, lambda d: d["requirements"].__setitem__("p1_10_promotion_command_must_be_reused", False),
                          "P1.10 authority weakening")
    expect_policy_failure(policy, lambda d: d["requirements"].__setitem__("p1_10_auto_commit_must_remain_disabled", False),
                          "auto-commit allowance")
    expect_policy_failure(policy, lambda d: d.__setitem__("next_objective", "P4.07"), "P4.07 creation")
    print("P4.05 self-check: PASS")


def write_result(path: str | None, data: dict[str, Any]) -> None:
    raw = canonical_line(data)
    if path:
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(raw)
    sys.stdout.buffer.write(raw)


def main() -> int:
    parser = argparse.ArgumentParser(description="AppleSilicon P4.05 reproducible divergence promotion wrapper")
    parser.add_argument("--policy", default=str(DEFAULT_POLICY))
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("validate-policy")
    sub.add_parser("self-check")
    pr = sub.add_parser("promote")
    pr.add_argument("--reproduction", action="append", nargs=5, required=True,
                    metavar=("AB_SESSION", "REFERENCE_MANIFEST", "PROBE_MANIFEST", "REFERENCE_TRACE", "PROBE_TRACE"))
    pr.add_argument("--work-dir", required=True)
    pr.add_argument("--output")
    args = parser.parse_args()
    try:
        policy = load_json(Path(args.policy))
        validate_policy(policy)
        validate_locked_artifacts(policy)
        if args.command == "validate-policy":
            print("P4.05 policy: PASS")
            return 0
        if args.command == "self-check":
            self_check(policy)
            return 0
        result = promote(args, policy)
        write_result(args.output, result)
        return 0
    except (PromotionError, OSError, subprocess.TimeoutExpired) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

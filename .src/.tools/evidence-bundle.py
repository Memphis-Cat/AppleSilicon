#!/usr/bin/env python3

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import sys
import tempfile
from pathlib import Path
from typing import Any

VERSION = "1.0.0.0.0.0"
ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_POLICY = ROOT_DIR / ".src" / ".configs" / "p1.10-promotion-policy.json"
DEFAULT_MANIFEST_POLICY = ROOT_DIR / ".src" / ".configs" / "p1.09-manifest-policy.json"
DEFAULT_TRACE_CONFIG = ROOT_DIR / ".src" / ".configs" / "p1.08-compare.json"
MANIFEST_TOOL = ROOT_DIR / ".src" / ".tools" / "reference-manifest.py"
TRACE_TOOL = ROOT_DIR / ".src" / ".tools" / "compare-boot-traces.py"
INPUT_ERROR = 2
GATE_REJECTED = 10


class BundleError(Exception):
    pass


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise BundleError(f"could not load module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise BundleError(f"file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise BundleError(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise BundleError(f"top-level JSON must be an object: {path}")
    return value


def save_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def digest_object(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


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
        raise BundleError(f"could not hash {path}: {exc}") from exc
    return {"sha256": digest.hexdigest(), "bytes": size}


def load_policy(path: Path) -> dict[str, Any]:
    policy = load_json(path)
    if policy.get("schema") != 1:
        raise BundleError(f"unsupported P1.10 policy schema: {policy.get('schema')!r}")
    if policy.get("project_version") != VERSION:
        raise BundleError(f"P1.10 policy project_version must be {VERSION}")
    if not isinstance(policy.get("minimum_reproductions"), int) or policy["minimum_reproductions"] < 2:
        raise BundleError("minimum_reproductions must be at least 2")
    return policy


def result_is_runtime(role: str, result: str, policy: dict[str, Any]) -> bool:
    lowered = result.lower()
    if any(fragment.lower() in lowered for fragment in policy["blocked_result_fragments"]):
        return False
    prefixes = policy["reference_result_prefixes"] if role == "reference" else policy["probe_result_prefixes"]
    return any(result.startswith(prefix) for prefix in prefixes)


def verify_trace_artifact(manifest: dict[str, Any], trace_path: Path, policy: dict[str, Any]) -> dict[str, Any]:
    observed = sha256_file(trace_path)
    allowed = set(policy["allowed_trace_artifact_kinds"])
    matches = [
        artifact
        for artifact in manifest.get("artifacts", [])
        if artifact.get("kind") in allowed
        and artifact.get("sha256") == observed["sha256"]
        and artifact.get("bytes") == observed["bytes"]
    ]
    if not matches:
        raise BundleError(
            f"trace evidence {trace_path.name} does not match an allowed artifact recorded by {manifest.get('role')} manifest"
        )
    return {
        "label": trace_path.name,
        "sha256": observed["sha256"],
        "bytes": observed["bytes"],
        "manifest_artifact_kinds": sorted({item["kind"] for item in matches}),
    }


def contract_fingerprint(reference: dict[str, Any], manifest_policy: dict[str, Any], manifest_module) -> str:
    contract = {
        path: manifest_module.get_path(reference, path)
        for path in manifest_policy["pair_equal_paths"]
    }
    return digest_object(contract)


def mismatch_signature(comparison: dict[str, Any]) -> tuple[str | None, dict[str, Any] | None]:
    if comparison["identical"]:
        return None, None
    mismatch = comparison["first_mismatch"]
    ref = mismatch.get("reference")
    probe = mismatch.get("probe")
    resync = mismatch.get("resynchronization")
    signature_material = {
        "classification": mismatch["classification"],
        "reference": ref.get("canonical") if ref else None,
        "probe": probe.get("canonical") if probe else None,
        "resynchronization_anchor": resync.get("anchor") if resync else None,
    }
    return digest_object(signature_material), signature_material


def build_candidate(
    reference: dict[str, Any],
    probe: dict[str, Any],
    reference_trace: Path,
    probe_trace: Path,
    policy: dict[str, Any],
    manifest_policy: dict[str, Any],
    trace_config: dict[str, Any],
    manifest_module,
    trace_module,
) -> tuple[dict[str, Any], Any, Any, dict[str, Any]]:
    pair_report = manifest_module.compare_manifests(reference, probe, manifest_policy)
    if not pair_report["comparable"]:
        paths = ", ".join(item["path"] for item in pair_report["contract_mismatches"])
        raise BundleError(f"P1.09 pairing contract rejected the A/B pair: {paths}")

    reference_evidence = verify_trace_artifact(reference, reference_trace, policy)
    probe_evidence = verify_trace_artifact(probe, probe_trace, policy)

    reference_stream = trace_module.parse_file(reference_trace, trace_config)
    probe_stream = trace_module.parse_file(probe_trace, trace_config)
    comparison = trace_module.compare_streams(reference_stream, probe_stream, trace_config)
    signature, signature_material = mismatch_signature(comparison)

    ref_runtime = result_is_runtime("reference", reference["run"]["result"], policy)
    probe_runtime = result_is_runtime("probe", probe["run"]["result"], policy)
    runtime_origin = ref_runtime and probe_runtime
    status = "no_divergence" if comparison["identical"] else "divergence_candidate"
    promotable = status == "divergence_candidate" and runtime_origin

    candidate_material = {
        "reference_run_id": reference["run"]["id"],
        "probe_run_id": probe["run"]["id"],
        "reference_manifest_sha256": digest_object(reference),
        "probe_manifest_sha256": digest_object(probe),
        "divergence_signature": signature,
    }
    candidate_id = "p01-candidate-" + digest_object(candidate_material)[:20]

    candidate = {
        "schema": 1,
        "project_version": VERSION,
        "candidate_id": candidate_id,
        "status": status,
        "promotion_eligible": promotable,
        "evidence_origin": "runtime" if runtime_origin else "non-runtime",
        "reference_run_id": reference["run"]["id"],
        "probe_run_id": probe["run"]["id"],
        "reference_result": reference["run"]["result"],
        "probe_result": probe["run"]["result"],
        "reference_manifest_sha256": digest_object(reference),
        "probe_manifest_sha256": digest_object(probe),
        "contract_fingerprint": contract_fingerprint(reference, manifest_policy, manifest_module),
        "reference_trace": reference_evidence,
        "probe_trace": probe_evidence,
        "comparison": {
            "identical": comparison["identical"],
            "reference_event_count": comparison["reference"]["event_count"],
            "probe_event_count": comparison["probe"]["event_count"],
            "first_mismatch": comparison["first_mismatch"],
        },
        "divergence_signature": signature,
        "signature_material": signature_material,
        "gate": {
            "minimum_reproductions": policy["minimum_reproductions"],
            "auto_commit": bool(policy.get("auto_commit_promotion", False)),
        },
    }
    return candidate, reference_stream, probe_stream, pair_report


def write_candidate_markdown(candidate: dict[str, Any], path: Path) -> None:
    lines = [
        "# P01-DIVERGENCE-CANDIDATE",
        "",
        f"Candidate: `{candidate['candidate_id']}`",
        f"Status: **{candidate['status']}**",
        f"Evidence origin: **{candidate['evidence_origin']}**",
        f"Promotion eligible: **{str(candidate['promotion_eligible']).lower()}**",
        "",
        f"Reference run: `{candidate['reference_run_id']}`",
        f"Probe run: `{candidate['probe_run_id']}`",
        f"Contract fingerprint: `{candidate['contract_fingerprint']}`",
    ]
    if candidate["status"] == "divergence_candidate":
        mismatch = candidate["comparison"]["first_mismatch"]
        ref = mismatch.get("reference")
        probe = mismatch.get("probe")
        lines.extend([
            f"Divergence signature: `{candidate['divergence_signature']}`",
            "",
            f"Classification: **`{mismatch['classification']}`**",
            "",
            "## Reference event",
            "",
            "```text",
            ref.get("canonical") if ref else "<end-of-trace>",
            "```",
            "",
            "## Probe event",
            "",
            "```text",
            probe.get("canonical") if probe else "<end-of-trace>",
            "```",
        ])
    else:
        lines.extend(["", "No canonical trace divergence was found in this A/B pair."])
    lines.extend([
        "",
        "This candidate is not `P01-DIVERGENCE-0001`. Promotion requires the P1.10 reproduction gate.",
        "",
    ])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def evaluate_promotion(candidates: list[dict[str, Any]], policy: dict[str, Any], *, strict_runtime: bool = True) -> dict[str, Any]:
    minimum = policy["minimum_reproductions"]
    if len(candidates) < minimum:
        raise BundleError(f"promotion requires at least {minimum} reproduced candidate bundles")

    for candidate in candidates:
        if candidate.get("schema") != 1 or candidate.get("project_version") != VERSION:
            raise BundleError("candidate schema/version mismatch")
        if candidate.get("status") != "divergence_candidate":
            raise BundleError(f"candidate {candidate.get('candidate_id')} does not contain a divergence")
        if strict_runtime and (candidate.get("evidence_origin") != "runtime" or candidate.get("promotion_eligible") is not True):
            raise BundleError(f"candidate {candidate.get('candidate_id')} is not eligible runtime evidence")
        if not candidate.get("divergence_signature"):
            raise BundleError(f"candidate {candidate.get('candidate_id')} has no divergence signature")

    run_pairs = [(item["reference_run_id"], item["probe_run_id"]) for item in candidates]
    if policy.get("require_unique_run_pairs", True) and len(run_pairs) != len(set(run_pairs)):
        raise BundleError("promotion cannot reuse the same reference/probe run pair")

    signatures = {item["divergence_signature"] for item in candidates}
    if policy.get("require_same_divergence_signature", True) and len(signatures) != 1:
        raise BundleError("candidate reproductions do not share the same divergence signature")

    contracts = {item["contract_fingerprint"] for item in candidates}
    if policy.get("require_same_contract_fingerprint", True) and len(contracts) != 1:
        raise BundleError("candidate reproductions do not share the same P1.09 contract fingerprint")

    first = candidates[0]
    return {
        "schema": 1,
        "project_version": VERSION,
        "id": policy["promotion_id"],
        "status": "promoted",
        "reproduction_count": len(candidates),
        "divergence_signature": first["divergence_signature"],
        "contract_fingerprint": first["contract_fingerprint"],
        "classification": first["comparison"]["first_mismatch"]["classification"],
        "signature_material": first["signature_material"],
        "reproductions": [
            {
                "candidate_id": item["candidate_id"],
                "reference_run_id": item["reference_run_id"],
                "probe_run_id": item["probe_run_id"],
                "reference_manifest_sha256": item["reference_manifest_sha256"],
                "probe_manifest_sha256": item["probe_manifest_sha256"],
                "reference_trace_sha256": item["reference_trace"]["sha256"],
                "probe_trace_sha256": item["probe_trace"]["sha256"],
            }
            for item in candidates
        ],
        "auto_committed": False,
    }


def write_promotion_markdown(record: dict[str, Any], path: Path) -> None:
    material = record["signature_material"]
    lines = [
        f"# {record['id']}",
        "",
        f"Status: **{record['status']}**",
        f"Reproductions: **{record['reproduction_count']}**",
        f"Classification: **`{record['classification']}`**",
        f"Divergence signature: `{record['divergence_signature']}`",
        f"Contract fingerprint: `{record['contract_fingerprint']}`",
        "",
        "Stage: `earliest normalized VMApple trace divergence`",
        "PC: `unknown from current MMIO trace contract`",
        "",
        "## Expected/reference behavior",
        "",
        "```text",
        material.get("reference") or "<end-of-trace>",
        "```",
        "",
        "## Observed/probe behavior",
        "",
        "```text",
        material.get("probe") or "<end-of-trace>",
        "```",
        "",
        "## Reproductions",
        "",
    ]
    for item in record["reproductions"]:
        lines.append(f"- `{item['candidate_id']}` — reference `{item['reference_run_id']}`, probe `{item['probe_run_id']}`")
    lines.extend([
        "",
        "This record was created only after the P1.10 pairing, artifact-integrity, runtime-origin, uniqueness, contract, and reproduction gates passed.",
        "",
        "It is intentionally not auto-committed. A later engineering part must explain and implement the hardware contract behind this divergence rather than patching around it blindly.",
        "",
    ])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def run_candidate(args: argparse.Namespace) -> int:
    policy = load_policy(args.policy)
    manifest_module = load_module("applesilicon_p109_manifest", MANIFEST_TOOL)
    trace_module = load_module("applesilicon_p108_trace", TRACE_TOOL)
    manifest_policy = manifest_module.load_policy(args.manifest_policy)
    trace_config = trace_module.load_config(args.trace_config)
    reference = manifest_module.load_json(args.reference_manifest)
    probe = manifest_module.load_json(args.probe_manifest)

    candidate, reference_stream, probe_stream, pair_report = build_candidate(
        reference,
        probe,
        args.reference_trace,
        args.probe_trace,
        policy,
        manifest_policy,
        trace_config,
        manifest_module,
        trace_module,
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    trace_module.write_normalized(reference_stream, args.output_dir / "normalized-reference.log")
    trace_module.write_normalized(probe_stream, args.output_dir / "normalized-probe.log")
    save_json(args.output_dir / "pair-report.json", pair_report)
    save_json(args.output_dir / "candidate.json", candidate)
    write_candidate_markdown(candidate, args.output_dir / "P01-divergence-candidate.md")

    print(f"candidate_id={candidate['candidate_id']}")
    print(f"status={candidate['status']}")
    print(f"evidence_origin={candidate['evidence_origin']}")
    print(f"promotion_eligible={str(candidate['promotion_eligible']).lower()}")
    if candidate["divergence_signature"]:
        print(f"divergence_signature={candidate['divergence_signature']}")
    print(f"output_dir={args.output_dir}")
    return 0


def run_promote(args: argparse.Namespace) -> int:
    policy = load_policy(args.policy)
    candidates = [load_json(path) for path in args.candidate]
    record = evaluate_promotion(candidates, policy, strict_runtime=True)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    save_json(args.output_dir / f"{record['id']}.json", record)
    write_promotion_markdown(record, args.output_dir / f"{record['id']}.md")
    print(f"promoted={record['id']}")
    print(f"reproduction_count={record['reproduction_count']}")
    print(f"divergence_signature={record['divergence_signature']}")
    print("auto_committed=false")
    return 0


def run_self_check(args: argparse.Namespace) -> int:
    policy = load_policy(args.policy)
    manifest_module = load_module("applesilicon_p109_manifest_selfcheck", MANIFEST_TOOL)
    trace_module = load_module("applesilicon_p108_trace_selfcheck", TRACE_TOOL)
    manifest_policy = manifest_module.load_policy(args.manifest_policy)
    trace_config = trace_module.load_config(args.trace_config)

    reference = manifest_module.load_json(ROOT_DIR / ".src" / ".configs" / "p1.09-reference.example.json")
    probe = manifest_module.load_json(ROOT_DIR / ".src" / ".configs" / "p1.09-probe.example.json")
    reference_trace = ROOT_DIR / ".src" / ".fixtures" / ".p1.08" / "reference.trace"
    changed_trace = ROOT_DIR / ".src" / ".fixtures" / ".p1.08" / "value-divergence.trace"
    equivalent_trace = ROOT_DIR / ".src" / ".fixtures" / ".p1.08" / "equivalent.trace"

    reference = copy.deepcopy(reference)
    probe = copy.deepcopy(probe)
    reference["run"]["id"] = "p1.10-self-reference"
    probe["run"]["id"] = "p1.10-self-probe"
    reference["run"]["result"] = "synthetic-self-check"
    probe["run"]["result"] = "synthetic-self-check"
    reference["artifacts"] = [{"kind": "serial_log", "label": reference_trace.name, **sha256_file(reference_trace)}]
    probe["artifacts"] = [{"kind": "serial_log", "label": changed_trace.name, **sha256_file(changed_trace)}]

    candidate, _, _, _ = build_candidate(
        reference,
        probe,
        reference_trace,
        changed_trace,
        policy,
        manifest_policy,
        trace_config,
        manifest_module,
        trace_module,
    )
    if candidate["status"] != "divergence_candidate":
        raise BundleError("self-check failed to produce a divergence candidate")
    if candidate["promotion_eligible"] or candidate["evidence_origin"] == "runtime":
        raise BundleError("self-check synthetic candidate was incorrectly promotion eligible")

    equivalent_probe = copy.deepcopy(probe)
    equivalent_probe["artifacts"] = [{"kind": "serial_log", "label": equivalent_trace.name, **sha256_file(equivalent_trace)}]
    equal_candidate, _, _, _ = build_candidate(
        reference,
        equivalent_probe,
        reference_trace,
        equivalent_trace,
        policy,
        manifest_policy,
        trace_config,
        manifest_module,
        trace_module,
    )
    if equal_candidate["status"] != "no_divergence":
        raise BundleError("self-check equivalent traces were incorrectly reported as divergent")

    first = copy.deepcopy(candidate)
    second = copy.deepcopy(candidate)
    first["candidate_id"] = "p01-self-runtime-a"
    second["candidate_id"] = "p01-self-runtime-b"
    first["reference_run_id"], first["probe_run_id"] = "ref-a", "probe-a"
    second["reference_run_id"], second["probe_run_id"] = "ref-b", "probe-b"
    for item in (first, second):
        item["evidence_origin"] = "runtime"
        item["promotion_eligible"] = True
    positive = evaluate_promotion([first, second], policy, strict_runtime=True)
    if positive["id"] != policy["promotion_id"] or positive["reproduction_count"] != 2:
        raise BundleError("self-check positive promotion logic failed")

    bad = copy.deepcopy(second)
    bad["divergence_signature"] = "f" * 64
    try:
        evaluate_promotion([first, bad], policy, strict_runtime=True)
    except BundleError:
        pass
    else:
        raise BundleError("self-check accepted mismatched divergence signatures")

    try:
        evaluate_promotion([first], policy, strict_runtime=True)
    except BundleError:
        pass
    else:
        raise BundleError("self-check accepted fewer than minimum reproductions")

    print("P1.10 self-check: PASS")
    print("checks=pairing,artifact-integrity,trace-comparison,synthetic-block,reproduction-count,signature-match")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="AppleSilicon P1.10 A/B evidence bundler and divergence promotion gate")
    parser.add_argument("--version", action="version", version=f"AppleSilicon evidence bundle {VERSION}")
    sub = parser.add_subparsers(dest="command", required=True)

    candidate = sub.add_parser("candidate", help="validate one A/B pair and create a local candidate bundle")
    candidate.add_argument("--reference-manifest", required=True, type=Path)
    candidate.add_argument("--probe-manifest", required=True, type=Path)
    candidate.add_argument("--reference-trace", required=True, type=Path)
    candidate.add_argument("--probe-trace", required=True, type=Path)
    candidate.add_argument("--output-dir", required=True, type=Path)
    candidate.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    candidate.add_argument("--manifest-policy", type=Path, default=DEFAULT_MANIFEST_POLICY)
    candidate.add_argument("--trace-config", type=Path, default=DEFAULT_TRACE_CONFIG)
    candidate.set_defaults(func=run_candidate)

    promote = sub.add_parser("promote", help="promote reproduced runtime candidates to P01-DIVERGENCE-0001")
    promote.add_argument("--candidate", required=True, action="append", type=Path)
    promote.add_argument("--output-dir", required=True, type=Path)
    promote.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    promote.set_defaults(func=run_promote)

    selfcheck = sub.add_parser("self-check", help="run deterministic non-runtime P1.10 validation")
    selfcheck.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    selfcheck.add_argument("--manifest-policy", type=Path, default=DEFAULT_MANIFEST_POLICY)
    selfcheck.add_argument("--trace-config", type=Path, default=DEFAULT_TRACE_CONFIG)
    selfcheck.set_defaults(func=run_self_check)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return args.func(args)
    except BundleError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return GATE_REJECTED
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return INPUT_ERROR


if __name__ == "__main__":
    raise SystemExit(main())

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
EXPECTED_INFERNO = "cc4302a99167abec69b714cfd00c38caece7e7de"
EXPECTED_P205_VERSION = "2.4.0.0.0.0"
P205_POLICY = ROOT / ".src/.configs/p2.05-regression-policy.json"

class GateError(RuntimeError):
    pass

def require(value: bool, message: str) -> None:
    if not value:
        raise GateError(message)

def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))

def git_blob(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()

def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def canonical_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()

def git_output(cwd: Path, *args: str) -> str:
    p = subprocess.run(["git", *args], cwd=cwd, text=True, capture_output=True)
    if p.returncode:
        raise GateError(f"git {' '.join(args)} failed: {p.stderr.strip()}")
    return p.stdout.strip()

def validate_policy(policy: dict[str, Any]) -> None:
    require(policy.get("schema") == 1, "P2.06 schema mismatch")
    require(policy.get("project_version") == "2.5.0.0.0.0", "P2.06 version mismatch")
    require(policy.get("objective") == "P2.06", "P2.06 objective mismatch")
    require(policy.get("source_lock", {}).get("inferno_revision") == EXPECTED_INFERNO,
            "P2.06 Inferno source lock drift")
    cpu = policy.get("cpu_contract", {})
    require(cpu == {
        "accelerator": "tcg",
        "cpu": "apple-gxf",
        "control_cpu": "max",
        "machine": "vmapple",
    }, "P2.06 CPU integration contract drift")
    req = policy.get("requirements", {})
    for key in (
        "p2_05_must_pass", "prepared_source_must_be_pinned",
        "patch_series_must_apply_cleanly", "max_control_must_remain_isolated",
        "apple_gxf_tcg_wiring_required", "live_sysreg_policy_count_must_remain_zero",
        "p1_07_probe_must_be_reused_not_forked", "p1_09_evidence_contract_required",
        "p1_10_promotion_gate_required", "runtime_integrity_fingerprint_recheck_required",
        "guest_runtime_deferred",
    ):
        require(req.get(key) is True, f"P2.06 requirement disabled: {key}")
    require(policy.get("part_status_after_success") == "closed_implementation_complete",
            "P2.06 must close Part 02 after success")
    require(policy.get("next_part") == "Part 03", "P2.06 next part mismatch")
    require(policy.get("next_objective") == "P3.01", "P2.06 next objective mismatch")

def validate_locked_artifacts(policy: dict[str, Any]) -> list[dict[str, str]]:
    result = []
    for item in policy.get("locked_artifacts", []):
        path = ROOT / item["path"]
        require(path.is_file(), f"locked artifact missing: {item['path']}")
        observed = git_blob(path)
        require(observed == item["git_blob_sha"],
                f"locked artifact drift: {item['path']}: {observed}")
        result.append({
            "path": item["path"],
            "role": item["role"],
            "git_blob_sha": observed,
            "sha256": sha256(path),
        })
    return result

def validate_regression(path: Path) -> dict[str, Any]:
    require(path.is_file(), f"P2.05 regression result missing: {path}")
    data = load_json(path)
    require(data.get("schema") == 1, "P2.05 regression schema mismatch")
    require(data.get("project_version") == EXPECTED_P205_VERSION, "P2.05 regression version mismatch")
    require(data.get("objective") == "P2.05", "P2.05 regression objective mismatch")
    require(data.get("classification") == "P2_05_REGRESSION_PASS",
            "P2.05 regression did not pass")
    require(data.get("guest_execution") is False,
            "P2.05 regression unexpectedly records guest execution")
    require(data.get("cross_contracts", {}).get("live_sysreg_policy_count") == 0,
            "P2.05 live sysreg policy count drift")
    require(data.get("prepared_source", {}).get("max_control_isolated") is True,
            "P2.05 max control isolation failed")
    require(data.get("prepared_source", {}).get("apple_gxf_tcg_wiring") is True,
            "P2.05 apple-gxf TCG wiring failed")

    require(P205_POLICY.is_file(), f"P2.05 regression policy missing: {P205_POLICY}")
    expected_policy_sha256 = canonical_hash(load_json(P205_POLICY))
    require(data.get("policy_sha256") == expected_policy_sha256,
            "P2.05 policy fingerprint does not reproduce")

    fp = data.get("suite_fingerprint")
    require(isinstance(fp, str) and len(fp) == 64, "P2.05 suite fingerprint invalid")
    expected_fp = canonical_hash({
        "policy_sha256": data["policy_sha256"],
        "locked_artifacts": data.get("locked_artifacts"),
        "cross_contracts": data.get("cross_contracts"),
        "prepared_source": data.get("prepared_source"),
    })
    require(fp == expected_fp, "P2.05 suite fingerprint does not reproduce")
    return {"suite_fingerprint": fp, "sha256": sha256(path)}

def validate_prepared_source(source: Path, policy: dict[str, Any]) -> dict[str, Any]:
    require(source.is_dir(), f"prepared source missing: {source}")
    head = git_output(source, "rev-parse", "HEAD")
    require(head == EXPECTED_INFERNO, f"prepared source revision drift: {head}")

    cpu64 = source / "target/arm/cpu64.c"
    sysreg = source / "target/arm/apple-sysregs.c"
    feature = source / "target/arm/apple-cpu-features.c"
    meson = source / "target/arm/meson.build"
    for p in (cpu64, sysreg, feature, meson):
        require(p.is_file(), f"prepared source integration file missing: {p}")

    cputext = cpu64.read_text(encoding="utf-8")
    max_start = cputext.index("static void aarch64_max_initfn(Object *obj)")
    apple_start = cputext.index("static void aarch64_apple_gxf_initfn(Object *obj)")
    max_body = cputext[max_start:apple_start]
    apple_body = cputext[apple_start:]
    require("apple_cpu_feature_profile_init" not in max_body,
            "max CPU contaminated by Apple feature hook")
    require("apple_sysreg_framework_init" not in max_body,
            "max CPU contaminated by Apple sysreg hook")
    require("apple_cpu_feature_profile_init(cpu);" in apple_body,
            "apple-gxf feature hook missing")
    require("apple_sysreg_framework_init(cpu);" in apple_body,
            "apple-gxf sysreg hook missing")
    require('live_policy_count = 0' in sysreg.read_text(encoding="utf-8"),
            "live Apple sysreg policy count is not zero")
    mtext = meson.read_text(encoding="utf-8")
    require("'apple-cpu-features.c'" in mtext and "'apple-sysregs.c'" in mtext,
            "project-owned CPU sources are not in Meson build wiring")

    patch_blobs = []
    for rel in policy["patch_series"]:
        path = ROOT / rel
        require(path.is_file(), f"integration patch missing: {rel}")
        patch_blobs.append({"path": rel, "git_blob_sha": git_blob(path), "sha256": sha256(path)})

    return {
        "inferno_revision": head,
        "patches": patch_blobs,
        "max_control_isolated": True,
        "apple_gxf_tcg_wiring": True,
        "live_sysreg_policy_count": 0,
        "build_wiring_present": True,
    }

def canonical(data: dict[str, Any]) -> bytes:
    return (json.dumps(data, sort_keys=True, separators=(",", ":")) + "\n").encode()

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--policy", default=str(ROOT / ".src/.configs/p2.06-integration-policy.json"))
    ap.add_argument("--p2-05-result", required=True)
    ap.add_argument("--prepared-source", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    policy = load_json(Path(args.policy))
    validate_policy(policy)
    artifacts = validate_locked_artifacts(policy)
    regression = validate_regression(Path(args.p2_05_result))
    prepared = validate_prepared_source(Path(args.prepared_source), policy)

    manifest = {
        "schema": 1,
        "classification": "P2_06_INTEGRATION_PASS",
        "project_version": "2.5.0.0.0.0",
        "part": "Part 02",
        "objective": "P2.06",
        "guest_execution": False,
        "cpu_contract": policy["cpu_contract"],
        "p2_05": regression,
        "prepared_source": prepared,
        "locked_artifacts": artifacts,
        "part_status": "closed_implementation_complete",
        "next_part": "Part 03",
        "next_objective": "P3.01",
    }
    fp_basis = dict(manifest)
    fp_basis.pop("classification", None)
    manifest["integration_fingerprint"] = hashlib.sha256(canonical(fp_basis)).hexdigest()

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(canonical(manifest))
    print(json.dumps(manifest, indent=2, sort_keys=True))
    print(f"P2.06 integration fingerprint: {manifest['integration_fingerprint']}")
    return 0

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (GateError, KeyError, TypeError, ValueError) as exc:
        print(f"P2.06 integration failure: {exc}", file=sys.stderr)
        raise SystemExit(1)

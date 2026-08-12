#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_POLICY = ROOT / ".src/.configs/final-stability-policy.json"
EXPECTED_VERSION = "4.6.0.0.0.0"
EXPECTED_INFERNO = "cc4302a99167abec69b714cfd00c38caece7e7de"
EXPECTED_ROOT_README = "5f056dadbac5d814b9ffb287ec786a559774f953"
SHA1_RE = re.compile(r"^[0-9a-f]{40}$")


class AuditError(RuntimeError):
    pass


def require(value: bool, message: str) -> None:
    if not value:
        raise AuditError(message)


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AuditError(f"could not parse JSON {path}: {exc}") from exc
    require(isinstance(value, dict), f"top-level JSON must be an object: {path}")
    return value


def canonical(data: Any) -> bytes:
    return (json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def git_blob(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def run(cmd: list[str], *, cwd: Path = ROOT, timeout: int = 60) -> subprocess.CompletedProcess[str]:
    try:
        proc = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, timeout=timeout, errors="replace")
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise AuditError(f"command failed to execute: {' '.join(cmd)}: {exc}") from exc
    if proc.returncode != 0:
        detail = ((proc.stdout or "") + (proc.stderr or "")).strip()
        raise AuditError(f"command rejected ({proc.returncode}): {' '.join(cmd)}\n{detail}")
    return proc


def validate_policy(policy: dict[str, Any]) -> None:
    require(policy.get("schema") == 1, "final stability policy schema mismatch")
    require(policy.get("project_version") == EXPECTED_VERSION, "final stability version mismatch")
    require(policy.get("classification") == "FINAL_STABILITY_HARDENING", "final stability classification drift")
    require(policy.get("roadmap_extension") is False, "hardening must not create a new roadmap part/objective")
    require(policy.get("next_part") is None and policy.get("next_objective") is None,
            "hardening must not create Part 05 or P4.07")
    require(policy.get("source_lock", {}).get("inferno_revision") == EXPECTED_INFERNO,
            "Inferno source lock drift")
    require(policy.get("source_lock", {}).get("root_readme_git_blob") == EXPECTED_ROOT_README,
            "frozen root README lock drift")

    patches = policy.get("patch_series", [])
    require([item.get("name") for item in patches] == [
        "0001-vmapple-decouple-build-from-hvf.patch",
        "0002-vmapple-optional-apple-pvg.patch",
        "0003-arm-apple-sysreg-framework.patch",
        "0004-arm-apple-sysreg-policy-model.patch",
        "0005-arm-vmapple-feature-contract.patch",
    ], "final patch series must remain exactly 0001 through 0005")
    for item in patches:
        require(SHA1_RE.fullmatch(str(item.get("git_blob_sha", ""))) is not None,
                f"invalid patch blob lock: {item.get('name')}")

    scan = policy.get("repository_scan", {})
    require(scan.get("json_root") == ".src/.configs", "JSON scan root drift")
    require(scan.get("tool_root") == ".src/.tools", "tool scan root drift")
    require(scan.get("compile_all_python") is True, "all Python must be compiled")
    require(scan.get("bash_syntax_all_shell") is True, "all shell tools must get bash -n")
    require(scan.get("all_python_and_shell_tools_executable") is True,
            "all project-owned Python/shell tools must remain executable")

    requirements = policy.get("requirements", {})
    for key in (
        "vmapple_machine_id_is_uint64_not_rfc_uuid",
        "compiled_p3_02_identity_is_applied_to_runtime",
        "runtime_machine_id_matches_compiled_identity",
        "generated_fingerprints_are_recomputed_before_use",
        "runtime_run_id_originates_at_qemu_launch",
        "same_runtime_run_cannot_be_repackaged_as_independent",
        "qemu_process_cleanup_on_signal_required",
        "empty_trace_is_insufficient_evidence",
        "unstructured_trace_is_not_promotable_runtime_evidence",
        "p1_10_remains_only_promotion_authority",
        "no_new_apple_behavior_without_runtime_evidence",
        "no_new_inferno_patch",
        "root_readme_remains_frozen",
        "runtime_validation_remains_pending",
    ):
        require(requirements.get(key) is True, f"hardening requirement disabled: {key}")


def git_index_entries() -> dict[str, tuple[str, str]]:
    proc = run(["git", "ls-files", "-s"])
    entries: dict[str, tuple[str, str]] = {}
    for line in proc.stdout.splitlines():
        if not line.strip():
            continue
        meta, path = line.split("\t", 1)
        mode, sha, _stage = meta.split()
        entries[path] = (mode, sha)
    return entries


def validate_repository_identity(policy: dict[str, Any], index: dict[str, tuple[str, str]]) -> dict[str, Any]:
    root_readme = ROOT / "README.md"
    require(root_readme.is_file(), "root README missing")
    require(git_blob(root_readme) == EXPECTED_ROOT_README, "root README content changed")

    inferno = index.get(".src/.upstream/.inferno")
    require(inferno == ("160000", EXPECTED_INFERNO),
            f"Inferno gitlink drift: {inferno}")

    patch_dir = ROOT / ".src/.patches"
    observed = sorted(p.name for p in patch_dir.glob("[0-9][0-9][0-9][0-9]-*.patch"))
    expected = [item["name"] for item in policy["patch_series"]]
    require(observed == expected, f"patch series drift: {observed}")
    patch_result = []
    for item in policy["patch_series"]:
        path = patch_dir / item["name"]
        blob = git_blob(path)
        require(blob == item["git_blob_sha"], f"patch blob drift: {item['name']}: {blob}")
        patch_result.append({"name": item["name"], "git_blob_sha": blob})
    return {"root_readme_git_blob": EXPECTED_ROOT_README, "inferno_gitlink": EXPECTED_INFERNO,
            "patches": patch_result}


def validate_locked_artifacts(policy: dict[str, Any]) -> list[dict[str, str]]:
    result = []
    seen: set[str] = set()
    for item in policy.get("locked_artifacts", []):
        rel = item.get("path")
        require(isinstance(rel, str) and rel and rel not in seen, f"invalid/duplicate lock: {rel}")
        seen.add(rel)
        path = ROOT / rel
        require(path.is_file(), f"locked artifact missing: {rel}")
        observed = git_blob(path)
        require(observed == item.get("git_blob_sha"), f"locked artifact drift: {rel}: {observed}")
        result.append({"path": rel, "role": item.get("role", "locked"), "git_blob_sha": observed})
    return result


def scan_json(policy: dict[str, Any]) -> dict[str, Any]:
    root = ROOT / policy["repository_scan"]["json_root"]
    paths = sorted(root.rglob("*.json"))
    require(paths, "no JSON contracts/configurations found")
    for path in paths:
        load_json(path)
    return {"count": len(paths), "status": "PASS"}


def scan_python(policy: dict[str, Any], index: dict[str, tuple[str, str]]) -> dict[str, Any]:
    root = ROOT / policy["repository_scan"]["tool_root"]
    paths = sorted(root.rglob("*.py"))
    require(paths, "no Python tools found")
    for path in paths:
        try:
            compile(path.read_text(encoding="utf-8"), str(path), "exec")
        except (OSError, SyntaxError) as exc:
            raise AuditError(f"Python compile failed: {path}: {exc}") from exc
        rel = path.relative_to(ROOT).as_posix()
        require(index.get(rel, (None, None))[0] == "100755", f"Python tool is not Git mode 100755: {rel}")
    return {"count": len(paths), "status": "PASS"}


def scan_shell(policy: dict[str, Any], index: dict[str, tuple[str, str]]) -> dict[str, Any]:
    root = ROOT / policy["repository_scan"]["tool_root"]
    paths = sorted(root.rglob("*.sh"))
    require(paths, "no shell tools found")
    for path in paths:
        run(["bash", "-n", str(path)])
        rel = path.relative_to(ROOT).as_posix()
        require(index.get(rel, (None, None))[0] == "100755", f"shell tool is not Git mode 100755: {rel}")
    return {"count": len(paths), "status": "PASS"}


def read_source(rel: str) -> str:
    path = ROOT / rel
    require(path.is_file(), f"runtime source missing: {rel}")
    return path.read_text(encoding="utf-8", errors="replace")


def validate_runtime_source_contract(policy: dict[str, Any]) -> dict[str, Any]:
    paths = policy["runtime_source_contract"]
    sources = [(rel, read_source(rel)) for rel in paths["uuid_forbidden_paths"]]
    combined = "\n".join(text for _rel, text in sources)
    require("uuid.UUID" not in combined, "obsolete RFC UUID parser remains in runtime path")
    obsolete_normalization_lines = [
        f"{rel}:{line_no}:{line.strip()}"
        for rel, text in sources
        for line_no, line in enumerate(text.splitlines(), 1)
        if "lowercase_canonical_uuid" in line and "expect_failure(" not in line
    ]
    require(not obsolete_normalization_lines,
            "obsolete RFC UUID normalization remains in runtime path: " +
            "; ".join(obsolete_normalization_lines[:5]))

    p107 = read_source(".src/.tools/run-p1.07-probe.sh")
    p109 = read_source(".src/.tools/run-p1.09-reference.sh")
    collector = read_source(".src/.tools/collect-p1.10-probe.sh")
    for name, text in (("P1.07", p107), ("P1.09", p109)):
        for token in (
            "runtime_integrity.py", "identity --compiled", "vmapple,uuid=${MACHINE_ID}",
            "cleanup_qemu", "trap on_signal INT TERM HUP", "Run ID:", "Machine ID SHA-256:",
        ):
            require(token in text, f"{name} runtime hardening token missing: {token}")
    require('RUN_ID="$(extract_first "Run ID"' in collector,
            "probe collector does not reuse launcher-created run ID")
    require("Re-collecting this launcher log preserves the same run ID" in collector,
            "probe collector independence invariant not documented/enforced")

    p1policy = load_json(ROOT / ".src/.configs/p1.10-promotion-policy.json")
    require(p1policy.get("minimum_canonical_events_per_trace", 0) >= 1,
            "P1.10 permits empty canonical trace evidence")
    require(p1policy.get("require_structured_trace_events") is True,
            "P1.10 permits unstructured fallback runtime evidence")
    bundle = read_source(".src/.tools/evidence-bundle.py")
    require("trace_quality" in bundle and "minimum_canonical_events_per_trace" in bundle,
            "P1.10 evidence-bundle trace-sufficiency gate missing")
    require("empty traces were incorrectly accepted as evidence" in bundle,
            "P1.10 empty-trace negative self-check missing")

    build = read_source(".src/.tools/build-inferno.sh")
    require("Parallel job count must be a positive integer" in build,
            "Inferno build job-count validation missing")
    return {"status": "PASS", "checked_sources": len(set(paths["uuid_forbidden_paths"])) + 5}


def run_validator(rel_tool: str, args: list[str], label: str) -> None:
    tool = ROOT / rel_tool
    require(tool.is_file(), f"validator missing: {rel_tool}")
    run([sys.executable, str(tool), *args], timeout=120)


def validate_static_gates(policy: dict[str, Any]) -> dict[str, Any]:
    completed: list[str] = []
    for item in policy.get("static_validators", []):
        command = item["command"]
        if command[0] == "python":
            run_validator(item["tool"], command[1:], item["label"])
        else:
            raise AuditError(f"unsupported static validator command kind: {command[0]}")
        completed.append(item["label"])

    with tempfile.TemporaryDirectory(prefix="applesilicon-final-stability-") as td:
        compiled = Path(td) / "identity.json"
        run_validator(".src/.tools/platform-identity.py", [
            "--contract", str(ROOT / ".src/.configs/p3.02-identity-contract.json"),
            "compile", "--profile", str(ROOT / ".src/.configs/p3.02-identity.example.json"),
            "--output", str(compiled),
        ], "P3.02 example compiler")
        data = load_json(compiled)
        run_validator(".src/.tools/runtime_integrity.py", [
            "identity", "--compiled", str(compiled), "--machine-id", str(data["machine_uuid_decimal"]), "--allow-example",
        ], "runtime identity validator")
        completed.extend(["P3.02 example compiler", "runtime identity validator"])

    return {"status": "PASS", "validators": completed, "count": len(completed)}


def build_result(policy: dict[str, Any]) -> dict[str, Any]:
    index = git_index_entries()
    result: dict[str, Any] = {
        "schema": 1,
        "classification": "FINAL_STABILITY_AUDIT_PASS",
        "project_version": EXPECTED_VERSION,
        "planned_implementation_complete": True,
        "runtime_validation_pending": True,
        "guest_execution": False,
        "roadmap_extended": False,
        "repository_identity": validate_repository_identity(policy, index),
        "locked_artifacts": validate_locked_artifacts(policy),
        "json_scan": scan_json(policy),
        "python_scan": scan_python(policy, index),
        "shell_scan": scan_shell(policy, index),
        "runtime_source_contract": validate_runtime_source_contract(policy),
        "static_gates": validate_static_gates(policy),
        "stability_fixes": policy["stability_fixes"],
        "next_action": "integrated_runtime_testing",
    }
    basis = dict(result)
    basis.pop("classification", None)
    result["audit_fingerprint"] = sha256_bytes(canonical(basis))
    return result


def self_check(policy: dict[str, Any]) -> None:
    validate_policy(policy)
    require(policy["requirements"]["runtime_validation_remains_pending"] is True,
            "runtime-pending boundary weakened")
    require(len(policy["patch_series"]) == 5, "patch count self-check failed")
    require(policy["next_part"] is None and policy["next_objective"] is None,
            "hardening accidentally extended roadmap")
    print("Final stability policy self-check: PASS")


def main() -> int:
    parser = argparse.ArgumentParser(description="AppleSilicon final whole-repository stability audit")
    parser.add_argument("--policy", default=str(DEFAULT_POLICY))
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("validate-policy")
    sub.add_parser("self-check")
    audit = sub.add_parser("audit")
    audit.add_argument("--output")
    args = parser.parse_args()
    try:
        policy = load_json(Path(args.policy))
        validate_policy(policy)
        if args.command == "validate-policy":
            validate_locked_artifacts(policy)
            print("Final stability policy: PASS")
            return 0
        if args.command == "self-check":
            self_check(policy)
            return 0
        result = build_result(policy)
        raw = canonical(result)
        if args.output:
            out = Path(args.output)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(raw)
        sys.stdout.buffer.write(raw)
        return 0
    except AuditError as exc:
        print(f"final stability audit failure: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

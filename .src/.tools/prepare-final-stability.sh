#!/usr/bin/env bash
set -Eeuo pipefail

VERSION="4.6.0.0.0.0"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
POLICY="${ROOT_DIR}/.src/.configs/final-stability-policy.json"
TOOL="${ROOT_DIR}/.src/.tools/final-stability-audit.py"
WORK_ROOT="${APPLESILICON_FINAL_STABILITY_WORK_ROOT:-${ROOT_DIR}/.build/final-stability}"
LOG_DIR="${APPLESILICON_LOG_DIR:-${ROOT_DIR}/.logs}"
OUTPUT="${WORK_ROOT}/audit.json"
OUTPUT_SECOND="${WORK_ROOT}/audit.second.json"
CLASSIFICATION="UNCLASSIFIED"
FINAL_STAGE="startup"

mkdir -p "${LOG_DIR}" "${WORK_ROOT}"
TIMESTAMP="$(date -u +"%Y%m%d-%H%M%S")"
LOG_FILE="${LOG_DIR}/AppleSilicon-final-stability-${TIMESTAMP}-$$.log"
exec > >(tee "${LOG_FILE}") 2>&1

on_exit() {
    local status=$?
    trap - EXIT
    rm -f "${OUTPUT_SECOND}"
    echo "Classification: ${CLASSIFICATION}"
    echo "Final stage: ${FINAL_STAGE}"
    echo "Exit code: ${status}"
    echo "Finished UTC: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
    echo "Log: ${LOG_FILE}"
    echo "Audit output: ${OUTPUT}"
    exit "${status}"
}
trap on_exit EXIT

fail() {
    CLASSIFICATION="$1"
    shift
    printf '%s\n' "$@" >&2
    exit 1
}

for command in python3 bash git cmp tee; do
    command -v "${command}" >/dev/null 2>&1 || fail "FINAL_STABILITY_TOOL_MISSING" "Missing command: ${command}"
done
[[ -f "${POLICY}" ]] || fail "FINAL_STABILITY_POLICY_MISSING" "Final stability policy is missing"
[[ -x "${TOOL}" ]] || fail "FINAL_STABILITY_AUDITOR_NOT_EXECUTABLE" "Final stability auditor is not executable"

echo "AppleSilicon version: ${VERSION}"
echo "Scope: final post-roadmap stability hardening"
echo "Started UTC: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
echo "Guest execution: NONE"
echo "This harness performs static/source/repository validation only."

FINAL_STAGE="policy-validation"
python3 "${TOOL}" --policy "${POLICY}" validate-policy || fail "FINAL_STABILITY_POLICY_INVALID" "Final stability policy rejected"

FINAL_STAGE="negative-self-checks"
python3 "${TOOL}" --policy "${POLICY}" self-check || fail "FINAL_STABILITY_SELF_CHECK_FAILED" "Final stability self-check failed"

FINAL_STAGE="first-whole-repository-audit"
python3 "${TOOL}" --policy "${POLICY}" audit --output "${OUTPUT}" >/dev/null || fail "FINAL_STABILITY_AUDIT_FAILED" "First whole-repository audit failed"

FINAL_STAGE="second-whole-repository-audit"
python3 "${TOOL}" --policy "${POLICY}" audit --output "${OUTPUT_SECOND}" >/dev/null || fail "FINAL_STABILITY_AUDIT_FAILED" "Second whole-repository audit failed"

FINAL_STAGE="determinism-check"
cmp -s "${OUTPUT}" "${OUTPUT_SECOND}" || fail "FINAL_STABILITY_NONDETERMINISTIC" "Repeated final stability audit outputs differ"

FINAL_STAGE="result-validation"
python3 - "${OUTPUT}" <<'PY'
import json, re, sys
from pathlib import Path
p=Path(sys.argv[1]); data=json.loads(p.read_text(encoding="utf-8"))
if data.get("classification") != "FINAL_STABILITY_AUDIT_PASS": raise SystemExit("final classification mismatch")
if data.get("project_version") != "4.6.0.0.0.0": raise SystemExit("final version mismatch")
if data.get("planned_implementation_complete") is not True: raise SystemExit("implementation completion missing")
if data.get("runtime_validation_pending") is not True: raise SystemExit("runtime-pending boundary was lost")
if data.get("guest_execution") is not False: raise SystemExit("static audit unexpectedly claims guest execution")
if data.get("roadmap_extended") is not False: raise SystemExit("hardening unexpectedly extends roadmap")
if re.fullmatch(r"[0-9a-f]{64}", str(data.get("audit_fingerprint", ""))) is None: raise SystemExit("audit fingerprint invalid")
print("Final audit fingerprint:", data["audit_fingerprint"])
PY

CLASSIFICATION="FINAL_STABILITY_AUDIT_PASS"
FINAL_STAGE="complete"
echo "Final whole-repository stability audit: PASS"
echo "Planned implementation: COMPLETE"
echo "Runtime validation: PENDING"
echo "Next action: integrated runtime testing"

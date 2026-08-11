#!/usr/bin/env bash

set -Eeuo pipefail

VERSION="1.0.0.0.0.0"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
POLICY="${ROOT_DIR}/.src/.configs/p1.10-promotion-policy.json"
MANIFEST_POLICY="${ROOT_DIR}/.src/.configs/p1.09-manifest-policy.json"
TRACE_CONFIG="${ROOT_DIR}/.src/.configs/p1.08-compare.json"
BUNDLE_TOOL="${ROOT_DIR}/.src/.tools/evidence-bundle.py"
MANIFEST_TOOL="${ROOT_DIR}/.src/.tools/reference-manifest.py"
TRACE_TOOL="${ROOT_DIR}/.src/.tools/compare-boot-traces.py"
PROBE_COLLECTOR="${ROOT_DIR}/.src/.tools/collect-p1.10-probe.sh"
REFERENCE_RUNNER="${ROOT_DIR}/.src/.tools/run-p1.09-reference.sh"
PROBE_RUNNER="${ROOT_DIR}/.src/.tools/run-p1.07-probe.sh"
LOG_DIR="${APPLESILICON_LOG_DIR:-${ROOT_DIR}/.logs}"
WORK_ROOT="${APPLESILICON_P1_10_WORK_ROOT:-${ROOT_DIR}/.build/.p1.10}"
CLASSIFICATION="UNCLASSIFIED"
FINAL_STAGE="startup"

mkdir -p "${LOG_DIR}" "${WORK_ROOT}"
TIMESTAMP="$(date -u +"%Y%m%d-%H%M%S")"
LOG_FILE="${LOG_DIR}/AppleSilicon-p1.10-prepare-${TIMESTAMP}-$$.log"
exec > >(tee "${LOG_FILE}") 2>&1

on_exit() {
    local status=$?
    trap - EXIT
    echo "------------------------------------------------------------"
    echo "Classification: ${CLASSIFICATION}"
    echo "Final stage: ${FINAL_STAGE}"
    echo "Exit code: ${status}"
    echo "Finished UTC: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
    echo "Log file: ${LOG_FILE}"
    echo "============================================================"
    exit "${status}"
}
trap on_exit EXIT

fail() {
    CLASSIFICATION="$1"
    shift
    printf '%s\n' "$@" >&2
    exit 1
}

for cmd in python3 bash tee; do
    command -v "${cmd}" >/dev/null 2>&1 || fail "TOOL_MISSING" "Missing required command: ${cmd}"
done

for path in \
    "${POLICY}" \
    "${MANIFEST_POLICY}" \
    "${TRACE_CONFIG}" \
    "${BUNDLE_TOOL}" \
    "${MANIFEST_TOOL}" \
    "${TRACE_TOOL}" \
    "${PROBE_COLLECTOR}" \
    "${REFERENCE_RUNNER}" \
    "${PROBE_RUNNER}"; do
    [[ -f "${path}" ]] || fail "P1_10_INPUT_MISSING" "Required P1.10 dependency is missing: ${path}"
done

case "${WORK_ROOT}" in
    ""|"/"|"${HOME}"|"${ROOT_DIR}"|"${ROOT_DIR}/.build")
        fail "UNSAFE_WORK_ROOT" "Unsafe P1.10 work root: ${WORK_ROOT}"
        ;;
esac
[[ "${WORK_ROOT}" == "${ROOT_DIR}/.build/"* ]] || fail "UNSAFE_WORK_ROOT" "P1.10 work root must remain under ${ROOT_DIR}/.build/."

printf '%s\n' "============================================================"
printf '%s\n' "AppleSilicon P1.10 final Part 01 validation"
printf '%s\n' "============================================================"
printf '%s\n' "AppleSilicon version: ${VERSION}"
printf '%s\n' "Started UTC: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
printf '%s\n' "Host OS: $(uname -s 2>/dev/null || echo unknown)"
printf '%s\n' "Host architecture: $(uname -m 2>/dev/null || echo unknown)"
printf '%s\n' "Work root: ${WORK_ROOT}"
printf '%s\n' "Log file: ${LOG_FILE}"

FINAL_STAGE="json-validation"
python3 -m json.tool "${POLICY}" >/dev/null || fail "P1_10_POLICY_INVALID" "P1.10 promotion policy is invalid JSON."
python3 -m json.tool "${MANIFEST_POLICY}" >/dev/null || fail "P1_09_POLICY_INVALID" "P1.09 manifest policy is invalid JSON."
python3 -m json.tool "${TRACE_CONFIG}" >/dev/null || fail "P1_08_CONFIG_INVALID" "P1.08 trace configuration is invalid JSON."

FINAL_STAGE="python-syntax"
for source in "${BUNDLE_TOOL}" "${MANIFEST_TOOL}" "${TRACE_TOOL}"; do
    python3 - "${source}" <<'PY' || fail "PYTHON_SYNTAX_FAILED" "Python syntax validation failed: ${source}"
import sys
from pathlib import Path
path = Path(sys.argv[1])
compile(path.read_text(encoding="utf-8"), str(path), "exec")
PY
done

FINAL_STAGE="shell-syntax"
for source in "${PROBE_COLLECTOR}" "${REFERENCE_RUNNER}" "${PROBE_RUNNER}"; do
    bash -n "${source}" || fail "SHELL_SYNTAX_FAILED" "Shell syntax validation failed: ${source}"
done

FINAL_STAGE="p1.08-regression"
python3 "${TRACE_TOOL}" self-check --config "${TRACE_CONFIG}" \
    || fail "P1_08_REGRESSION_FAILED" "P1.08 trace comparator self-check failed."

FINAL_STAGE="p1.09-regression"
python3 "${MANIFEST_TOOL}" self-check --policy "${MANIFEST_POLICY}" \
    || fail "P1_09_REGRESSION_FAILED" "P1.09 manifest self-check failed."

FINAL_STAGE="p1.10-gate-self-check"
python3 "${BUNDLE_TOOL}" self-check \
    --policy "${POLICY}" \
    --manifest-policy "${MANIFEST_POLICY}" \
    --trace-config "${TRACE_CONFIG}" \
    || fail "P1_10_GATE_SELF_CHECK_FAILED" "P1.10 promotion-gate self-check failed."

FINAL_STAGE="source-contract"
grep -Fq '"minimum_reproductions": 2' "${POLICY}" \
    || fail "P1_10_REPRODUCTION_POLICY_INVALID" "P1.10 must require at least two reproductions."
grep -Fq '"auto_commit_promotion": false' "${POLICY}" \
    || fail "P1_10_AUTOCOMMIT_POLICY_INVALID" "P1.10 must not auto-commit promoted evidence."
grep -Fq 'P1_09_REFERENCE_' "${POLICY}" \
    || fail "P1_10_REFERENCE_RESULT_POLICY_MISSING" "Reference runtime result policy is missing."
grep -Fq 'P1_07_PROBE_' "${POLICY}" \
    || fail "P1_10_PROBE_RESULT_POLICY_MISSING" "Probe runtime result policy is missing."

CLASSIFICATION="P1_10_VALIDATION_PASS"
FINAL_STAGE="complete"
printf '%s\n' "------------------------------------------------------------"
printf '%s\n' "P1.10 development-side validation passed."
printf '%s\n' "No QEMU, macOS, HVF, TCG guest, or m1n1 session was launched."
printf '%s\n' "Part 01 implementation objective sequence is now closed at P1.10."

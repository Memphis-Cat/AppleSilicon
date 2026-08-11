#!/usr/bin/env bash

set -Eeuo pipefail

VERSION="0.8.0.0.0.0"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TOOL="${ROOT_DIR}/.src/.tools/compare-boot-traces.py"
CONFIG="${ROOT_DIR}/.src/.configs/p1.08-compare.json"
FIXTURES="${ROOT_DIR}/.src/.fixtures/.p1.08"
WORK_ROOT="${APPLESILICON_P1_08_WORK_ROOT:-${ROOT_DIR}/.build/.p1.08}"
CHECK_ROOT="${WORK_ROOT}/.self-check"
LOG_DIR="${APPLESILICON_LOG_DIR:-${ROOT_DIR}/.logs}"
CLASSIFICATION="UNCLASSIFIED"
FINAL_STAGE="startup"

mkdir -p "${LOG_DIR}"
TIMESTAMP="$(date -u +"%Y%m%d-%H%M%S")"
LOG_FILE="${LOG_DIR}/AppleSilicon-p1.08-prepare-${TIMESTAMP}-$$.log"
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

expect_json_value() {
    local json_file="$1"
    local expression="$2"
    local expected="$3"
    python3 - "${json_file}" "${expression}" "${expected}" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
expression = sys.argv[2].split(".")
expected = sys.argv[3]
data = json.loads(path.read_text(encoding="utf-8"))
value = data
for key in expression:
    value = value[key]
actual = str(value).lower() if isinstance(value, bool) else str(value)
if actual != expected:
    raise SystemExit(f"{path}: expected {'.'.join(expression)}={expected!r}, observed {actual!r}")
PY
}

for cmd in python3 cmp mkdir rm tee; do
    command -v "${cmd}" >/dev/null 2>&1 || fail "TOOL_MISSING" "Missing required command: ${cmd}"
done

[[ -f "${TOOL}" ]] || fail "COMPARATOR_MISSING" "Comparator is missing: ${TOOL}"
[[ -f "${CONFIG}" ]] || fail "CONFIG_MISSING" "Comparison config is missing: ${CONFIG}"
for fixture in reference.trace equivalent.trace value-divergence.trace insertion.trace; do
    [[ -f "${FIXTURES}/${fixture}" ]] || fail "FIXTURE_MISSING" "Fixture is missing: ${FIXTURES}/${fixture}"
done

case "${WORK_ROOT}" in
    ""|"/"|"${HOME}"|"${ROOT_DIR}"|"${ROOT_DIR}/.build")
        fail "UNSAFE_WORK_ROOT" "Unsafe P1.08 work root: ${WORK_ROOT}"
        ;;
esac
[[ "${WORK_ROOT}" == "${ROOT_DIR}/.build/"* ]] || fail "UNSAFE_WORK_ROOT" "P1.08 work root must remain under ${ROOT_DIR}/.build/."

rm -rf "${WORK_ROOT}"
mkdir -p "${CHECK_ROOT}"

echo "============================================================"
echo "AppleSilicon P1.08 trace-analysis validation"
echo "============================================================"
echo "AppleSilicon version: ${VERSION}"
echo "Started UTC: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
echo "Host OS: $(uname -s 2>/dev/null || echo unknown)"
echo "Host architecture: $(uname -m 2>/dev/null || echo unknown)"
echo "Python: $(python3 --version 2>&1)"
echo "Comparator: ${TOOL}"
echo "Config: ${CONFIG}"
echo "Fixtures: ${FIXTURES}"
echo "Work root: ${WORK_ROOT}"
echo "Log file: ${LOG_FILE}"

FINAL_STAGE="config-validation"
python3 -m json.tool "${CONFIG}" >/dev/null || fail "CONFIG_INVALID" "P1.08 comparison config is invalid JSON."

FINAL_STAGE="syntax-validation"
python3 -m py_compile "${TOOL}" || fail "PYTHON_SYNTAX_FAILED" "P1.08 comparator failed Python syntax compilation."

FINAL_STAGE="embedded-self-check"
python3 "${TOOL}" self-check --config "${CONFIG}" || fail "EMBEDDED_SELF_CHECK_FAILED" "P1.08 embedded self-check failed."

FINAL_STAGE="equivalence-fixture"
python3 "${TOOL}" compare \
    "${FIXTURES}/reference.trace" \
    "${FIXTURES}/equivalent.trace" \
    --config "${CONFIG}" \
    --normalized-reference "${CHECK_ROOT}/equivalent-reference.normalized.log" \
    --normalized-probe "${CHECK_ROOT}/equivalent-probe.normalized.log" \
    --report-md "${CHECK_ROOT}/equivalent-report.md" \
    --report-json "${CHECK_ROOT}/equivalent-report.json" \
    || fail "EQUIVALENCE_FIXTURE_FAILED" "Semantically identical trace fixtures were reported as divergent."

cmp "${CHECK_ROOT}/equivalent-reference.normalized.log" "${CHECK_ROOT}/equivalent-probe.normalized.log" \
    || fail "NORMALIZATION_NOT_DETERMINISTIC" "Equivalent traces did not produce identical canonical output."
expect_json_value "${CHECK_ROOT}/equivalent-report.json" "identical" "true"

FINAL_STAGE="value-divergence-fixture"
set +e
python3 "${TOOL}" compare \
    "${FIXTURES}/reference.trace" \
    "${FIXTURES}/value-divergence.trace" \
    --config "${CONFIG}" \
    --normalized-reference "${CHECK_ROOT}/value-reference.normalized.log" \
    --normalized-probe "${CHECK_ROOT}/value-probe.normalized.log" \
    --report-md "${CHECK_ROOT}/value-report.md" \
    --report-json "${CHECK_ROOT}/value-report.json"
VALUE_STATUS=$?
set -e
[[ ${VALUE_STATUS} -eq 10 ]] || fail "VALUE_DIVERGENCE_EXIT_WRONG" "Expected divergence exit 10, observed ${VALUE_STATUS}."
expect_json_value "${CHECK_ROOT}/value-report.json" "identical" "false"
expect_json_value "${CHECK_ROOT}/value-report.json" "first_mismatch.classification" "mmio_value_divergence"
expect_json_value "${CHECK_ROOT}/value-report.json" "first_mismatch.reference_event_index" "1"

FINAL_STAGE="sequence-divergence-fixture"
set +e
python3 "${TOOL}" compare \
    "${FIXTURES}/reference.trace" \
    "${FIXTURES}/insertion.trace" \
    --config "${CONFIG}" \
    --normalized-reference "${CHECK_ROOT}/sequence-reference.normalized.log" \
    --normalized-probe "${CHECK_ROOT}/sequence-probe.normalized.log" \
    --report-md "${CHECK_ROOT}/sequence-report.md" \
    --report-json "${CHECK_ROOT}/sequence-report.json"
SEQUENCE_STATUS=$?
set -e
[[ ${SEQUENCE_STATUS} -eq 10 ]] || fail "SEQUENCE_DIVERGENCE_EXIT_WRONG" "Expected divergence exit 10, observed ${SEQUENCE_STATUS}."
expect_json_value "${CHECK_ROOT}/sequence-report.json" "identical" "false"
expect_json_value "${CHECK_ROOT}/sequence-report.json" "first_mismatch.classification" "sequence_divergence"
expect_json_value "${CHECK_ROOT}/sequence-report.json" "first_mismatch.resynchronization.reference_skipped" "0"
expect_json_value "${CHECK_ROOT}/sequence-report.json" "first_mismatch.resynchronization.probe_skipped" "1"

echo "------------------------------------------------------------"
echo "P1.08 synthetic validation passed."
echo "Equivalent trace: no divergence"
echo "Value fixture: mmio_value_divergence @ event 1"
echo "Insertion fixture: sequence_divergence with bounded resynchronization"
echo "Artifacts: ${CHECK_ROOT}"
echo "No QEMU instance or macOS guest was launched."

CLASSIFICATION="P1_08_VALIDATION_PASS"
FINAL_STAGE="complete"

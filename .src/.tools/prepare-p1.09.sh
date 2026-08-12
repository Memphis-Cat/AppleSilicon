#!/usr/bin/env bash

set -Eeuo pipefail

VERSION="0.9.0.0.0.0"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TOOL="${ROOT_DIR}/.src/.tools/reference-manifest.py"
POLICY="${ROOT_DIR}/.src/.configs/p1.09-manifest-policy.json"
REFERENCE_EXAMPLE="${ROOT_DIR}/.src/.configs/p1.09-reference.example.json"
PROBE_EXAMPLE="${ROOT_DIR}/.src/.configs/p1.09-probe.example.json"
REFERENCE_RUNNER="${ROOT_DIR}/.src/.tools/run-p1.09-reference.sh"
WORK_ROOT="${APPLESILICON_P1_09_WORK_ROOT:-${ROOT_DIR}/.build/.p1.09}"
CHECK_ROOT="${WORK_ROOT}/.self-check"
LOG_DIR="${APPLESILICON_LOG_DIR:-${ROOT_DIR}/.logs}"
CLASSIFICATION="UNCLASSIFIED"
FINAL_STAGE="startup"

mkdir -p "${LOG_DIR}"
TIMESTAMP="$(date -u +"%Y%m%d-%H%M%S")"
LOG_FILE="${LOG_DIR}/AppleSilicon-p1.09-prepare-${TIMESTAMP}-$$.log"
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

for cmd in python3 bash mkdir rm tee; do
    command -v "${cmd}" >/dev/null 2>&1 || fail "TOOL_MISSING" "Missing required command: ${cmd}"
done

for path in "${TOOL}" "${POLICY}" "${REFERENCE_EXAMPLE}" "${PROBE_EXAMPLE}" "${REFERENCE_RUNNER}"; do
    [[ -f "${path}" ]] || fail "P1_09_FILE_MISSING" "Required P1.09 file is missing: ${path}"
done

NORMALIZED_BUILD_ROOT="$(python3 - "${ROOT_DIR}/.build" <<'PY'
from pathlib import Path
import sys
print(Path(sys.argv[1]).resolve(strict=False))
PY
)" || fail "UNSAFE_WORK_ROOT" "Could not canonicalize project build root."
NORMALIZED_WORK_ROOT="$(python3 - "${WORK_ROOT}" <<'PY'
from pathlib import Path
import sys
print(Path(sys.argv[1]).resolve(strict=False))
PY
)" || fail "UNSAFE_WORK_ROOT" "Could not canonicalize P1.09 work root."
case "${NORMALIZED_WORK_ROOT}" in
    ""|"/"|"${HOME}"|"${ROOT_DIR}"|"${NORMALIZED_BUILD_ROOT}")
        fail "UNSAFE_WORK_ROOT" "Unsafe P1.09 work root: ${WORK_ROOT}"
        ;;
esac
[[ "${NORMALIZED_WORK_ROOT}" == "${NORMALIZED_BUILD_ROOT}/"* ]] || fail "UNSAFE_WORK_ROOT" "P1.09 work root must remain under ${NORMALIZED_BUILD_ROOT}/."
WORK_ROOT="${NORMALIZED_WORK_ROOT}"
CHECK_ROOT="${WORK_ROOT}/.self-check"
rm -rf -- "${WORK_ROOT}"
mkdir -p "${CHECK_ROOT}"

echo "============================================================"
echo "AppleSilicon P1.09 reference-manifest validation"
echo "============================================================"
echo "AppleSilicon version: ${VERSION}"
echo "Started UTC: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
echo "Host OS: $(uname -s 2>/dev/null || echo unknown)"
echo "Host architecture: $(uname -m 2>/dev/null || echo unknown)"
echo "Python: $(python3 --version 2>&1)"
echo "Policy: ${POLICY}"
echo "Work root: ${WORK_ROOT}"
echo "Log file: ${LOG_FILE}"

FINAL_STAGE="json-validation"
python3 -m json.tool "${POLICY}" >/dev/null || fail "POLICY_INVALID" "P1.09 manifest policy is invalid JSON."
python3 -m json.tool "${REFERENCE_EXAMPLE}" >/dev/null || fail "REFERENCE_EXAMPLE_INVALID" "P1.09 reference example is invalid JSON."
python3 -m json.tool "${PROBE_EXAMPLE}" >/dev/null || fail "PROBE_EXAMPLE_INVALID" "P1.09 probe example is invalid JSON."

FINAL_STAGE="syntax-validation"
python3 - "${TOOL}" <<'PY' || fail "PYTHON_SYNTAX_FAILED" "P1.09 manifest tool failed syntax compilation."
import sys
from pathlib import Path
path = Path(sys.argv[1])
compile(path.read_text(encoding="utf-8"), str(path), "exec")
PY
bash -n "${REFERENCE_RUNNER}" || fail "REFERENCE_RUNNER_SYNTAX_FAILED" "P1.09 reference runner failed bash syntax validation."

FINAL_STAGE="embedded-self-check"
python3 "${TOOL}" self-check --policy "${POLICY}" || fail "SELF_CHECK_FAILED" "P1.09 embedded self-check failed."

FINAL_STAGE="example-validation"
python3 "${TOOL}" validate "${REFERENCE_EXAMPLE}" --policy "${POLICY}" || fail "REFERENCE_EXAMPLE_REJECTED" "Reference example failed validation."
python3 "${TOOL}" validate "${PROBE_EXAMPLE}" --policy "${POLICY}" || fail "PROBE_EXAMPLE_REJECTED" "Probe example failed validation."

FINAL_STAGE="pair-contract-validation"
python3 "${TOOL}" compare \
    "${REFERENCE_EXAMPLE}" \
    "${PROBE_EXAMPLE}" \
    --policy "${POLICY}" \
    --report-json "${CHECK_ROOT}/pair-report.json" \
    --report-md "${CHECK_ROOT}/pair-report.md" \
    || fail "PAIR_CONTRACT_FAILED" "Reference/probe examples do not satisfy the pairing contract."

FINAL_STAGE="collector-validation"
printf 'synthetic firmware\n' > "${CHECK_ROOT}/firmware.fixture"
printf 'synthetic auxiliary\n' > "${CHECK_ROOT}/aux.fixture"
printf 'synthetic disk\n' > "${CHECK_ROOT}/disk.fixture"
printf 'synthetic identity\n' > "${CHECK_ROOT}/identity.fixture"
printf 'synthetic serial\n' > "${CHECK_ROOT}/serial.log"
python3 "${TOOL}" collect \
    --policy "${POLICY}" \
    --role reference \
    --run-id synthetic-collector-reference \
    --started-utc 2026-08-11T00:00:00Z \
    --ended-utc 2026-08-11T00:00:01Z \
    --result synthetic \
    --host-os macOS \
    --host-architecture arm64 \
    --host-cpu-family 'Apple Silicon' \
    --host-virtualization HVF \
    --accelerator hvf \
    --cpu-model host \
    --ram-mib 4096 \
    --smp 4 \
    --command-shape 'qemu-system-aarch64 -accel hvf -cpu host -M vmapple,uuid=<redacted> -m 4096 -smp 4' \
    --firmware "${CHECK_ROOT}/firmware.fixture" \
    --auxiliary-storage "${CHECK_ROOT}/aux.fixture" \
    --disk "${CHECK_ROOT}/disk.fixture" \
    --machine-identity "${CHECK_ROOT}/identity.fixture" \
    --artifact "serial_log=${CHECK_ROOT}/serial.log" \
    --output "${CHECK_ROOT}/collected-reference.json" \
    || fail "COLLECTOR_FAILED" "P1.09 collector failed on synthetic local inputs."
python3 "${TOOL}" validate "${CHECK_ROOT}/collected-reference.json" --policy "${POLICY}" || fail "COLLECTED_MANIFEST_REJECTED" "Collected synthetic manifest failed validation."

echo "------------------------------------------------------------"
echo "P1.09 development-side validation passed."
echo "Manifest privacy policy: enforced"
echo "Reference/probe role contract: enforced"
echo "Input hash equality contract: enforced"
echo "Collector hashing: validated with synthetic local files"
echo "Reference runner: syntax validated only"
echo "No QEMU instance, macOS guest, HVF run, or m1n1 session was launched."
echo "Artifacts: ${CHECK_ROOT}"

CLASSIFICATION="P1_09_VALIDATION_PASS"
FINAL_STAGE="complete"

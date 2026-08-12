#!/usr/bin/env bash
set -Eeuo pipefail

VERSION="2.5.0.0.0.0"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
MANIFEST="${APPLESILICON_P2_06_MANIFEST:-${ROOT_DIR}/.build/p2.06/integration-manifest.json}"
INTEGRITY_TOOL="${ROOT_DIR}/.src/.tools/runtime_integrity.py"
P1_07_RUNNER="${ROOT_DIR}/.src/.tools/run-p1.07-probe.sh"
QEMU_BIN="${APPLESILICON_QEMU_BIN:-}"
LOG_DIR="${APPLESILICON_LOG_DIR:-${ROOT_DIR}/.logs}"
CLASSIFICATION="UNCLASSIFIED"
FINAL_STAGE="startup"

mkdir -p "${LOG_DIR}"
TIMESTAMP="$(date -u +"%Y%m%d-%H%M%S")"
LOG_FILE="${LOG_DIR}/AppleSilicon-p2.06-runtime-${TIMESTAMP}-$$.log"
exec > >(tee "${LOG_FILE}") 2>&1

on_exit() {
    local status=$?
    trap - EXIT
    echo "Classification: ${CLASSIFICATION}"
    echo "Final stage: ${FINAL_STAGE}"
    echo "Exit code: ${status}"
    echo "Finished UTC: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
    echo "Log: ${LOG_FILE}"
    exit "${status}"
}
trap on_exit EXIT
fail() { CLASSIFICATION="$1"; shift; printf '%s\n' "$@" >&2; exit 1; }

echo "AppleSilicon version: ${VERSION}"
echo "Objective: P2.06 final runtime wrapper"
echo "Started UTC: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"

FINAL_STAGE="integration-manifest-validation"
[[ -f "${MANIFEST}" ]] || fail "P2_06_MANIFEST_MISSING" "Integration manifest is missing: ${MANIFEST}"
[[ -x "${INTEGRITY_TOOL}" ]] || fail "P2_06_INTEGRITY_TOOL_MISSING" "Runtime integrity tool is not executable"
FINGERPRINT="$(python3 "${INTEGRITY_TOOL}" verify-p2 "${MANIFEST}")" || fail "P2_06_MANIFEST_INVALID" "P2.06 integration fingerprint or contract did not reproduce"
python3 - "${MANIFEST}" <<'PY'
import json,sys
from pathlib import Path
d=json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
expected={"accelerator":"tcg","cpu":"apple-gxf","control_cpu":"max","machine":"vmapple"}
if d.get("cpu_contract")!=expected: raise SystemExit("P2.06 CPU contract mismatch")
PY
echo "Integration fingerprint: ${FINGERPRINT}"

FINAL_STAGE="runner-validation"
[[ -x "${P1_07_RUNNER}" ]] || fail "P1_07_RUNNER_MISSING" "P1.07 runtime probe is not executable"
[[ -n "${QEMU_BIN}" && -x "${QEMU_BIN}" ]] || fail "QEMU_BINARY_MISSING" "QEMU binary is missing or not executable"

FINAL_STAGE="qemu-capability-gate"
"${QEMU_BIN}" -machine help 2>&1 | grep -E '(^|[[:space:]])vmapple([[:space:]]|$)' >/dev/null || fail "QEMU_VMAPPLE_MISSING" "QEMU does not advertise vmapple"
"${QEMU_BIN}" -accel help 2>&1 | grep -E '(^|[[:space:]])tcg([[:space:]]|$)' >/dev/null || fail "QEMU_TCG_MISSING" "QEMU does not advertise TCG"
"${QEMU_BIN}" -cpu help 2>&1 | grep -E '(^|[[:space:]])apple-gxf([[:space:]]|$)' >/dev/null || fail "QEMU_APPLE_GXF_MISSING" "QEMU does not advertise apple-gxf"

echo "QEMU capability gate: PASS"
echo "Delegating actual observational probe to the locked Part 01 P1.07 harness."

FINAL_STAGE="p1.07-runtime-probe"
set +e
APPLESILICON_VMAPPLE_ACCEL="tcg" \
APPLESILICON_VMAPPLE_CPU_PROFILE="apple-gxf" \
APPLESILICON_QEMU_BIN="${QEMU_BIN}" \
APPLESILICON_LOG_DIR="${LOG_DIR}" \
"${P1_07_RUNNER}"
STATUS=$?
set -e
CLASSIFICATION="P2_06_RUNTIME_DELEGATED"
FINAL_STAGE="complete"
echo "P1.07 delegated probe exit status: ${STATUS}"
echo "Runtime result remains observational and must flow through the Part 01 evidence/promotion gates."
exit "${STATUS}"

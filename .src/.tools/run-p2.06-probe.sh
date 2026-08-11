#!/usr/bin/env bash
set -Eeuo pipefail

VERSION="2.5.0.0.0.0"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
MANIFEST="${APPLESILICON_P2_06_MANIFEST:-${ROOT_DIR}/.build/p2.06/integration-manifest.json}"
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

fail() {
    CLASSIFICATION="$1"
    shift
    printf '%s\n' "$@" >&2
    exit 1
}

echo "AppleSilicon version: ${VERSION}"
echo "Objective: P2.06 final runtime wrapper"
echo "Started UTC: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"

FINAL_STAGE="integration-manifest-validation"
[[ -f "${MANIFEST}" ]] || fail "P2_06_MANIFEST_MISSING" "Integration manifest is missing: ${MANIFEST}"
python3 - "${MANIFEST}" <<'PY'
import json
from pathlib import Path
import sys

data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
if data.get("classification") != "P2_06_INTEGRATION_PASS":
    raise SystemExit("P2.06 integration manifest did not pass")
if data.get("part_status") != "closed_implementation_complete":
    raise SystemExit("Part 02 integration manifest is not closed")
cpu = data.get("cpu_contract", {})
expected = {
    "accelerator": "tcg",
    "cpu": "apple-gxf",
    "control_cpu": "max",
    "machine": "vmapple",
}
if cpu != expected:
    raise SystemExit("P2.06 CPU contract mismatch")
if data.get("prepared_source", {}).get("live_sysreg_policy_count") != 0:
    raise SystemExit("unexpected live Apple sysreg policy")
fp = data.get("integration_fingerprint")
if not isinstance(fp, str) or len(fp) != 64:
    raise SystemExit("P2.06 integration fingerprint invalid")
print(f"Integration fingerprint: {fp}")
PY

FINAL_STAGE="runner-validation"
[[ -x "${P1_07_RUNNER}" ]] || fail "P1_07_RUNNER_MISSING" "P1.07 runtime probe is not executable"
[[ -n "${QEMU_BIN}" ]] || fail "QEMU_BINARY_MISSING" "APPLESILICON_QEMU_BIN is not configured"
[[ -x "${QEMU_BIN}" ]] || fail "QEMU_BINARY_MISSING" "QEMU binary is not executable: ${QEMU_BIN}"

FINAL_STAGE="qemu-capability-gate"
"${QEMU_BIN}" -machine help 2>&1 | grep -Eq '(^|[[:space:]])vmapple([[:space:]]|$)' ||
    fail "QEMU_VMAPPLE_MISSING" "QEMU does not advertise vmapple"
"${QEMU_BIN}" -accel help 2>&1 | grep -Eq '(^|[[:space:]])tcg([[:space:]]|$)' ||
    fail "QEMU_TCG_MISSING" "QEMU does not advertise TCG"
"${QEMU_BIN}" -cpu help 2>&1 | grep -Eq '(^|[[:space:]])apple-gxf([[:space:]]|$)' ||
    fail "QEMU_APPLE_GXF_MISSING" "QEMU does not advertise apple-gxf"

echo "QEMU capability gate: PASS"
echo "Delegating actual observational probe to the locked Part 01 P1.07 harness."
echo "This wrapper validates capabilities, not binary build provenance."

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

#!/usr/bin/env bash
set -Eeuo pipefail

VERSION="4.0.0.0.0.0"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TOOL="${ROOT_DIR}/.src/.tools/runtime-session.py"
POLICY="${ROOT_DIR}/.src/.configs/p4.01-runtime-session-policy.json"
ROLE="${APPLESILICON_P4_01_ROLE:-probe}"
P3_MANIFEST="${APPLESILICON_P3_06_MANIFEST:-${ROOT_DIR}/.build/p3.06/platform-integration-manifest.json}"
QEMU_BIN="${APPLESILICON_QEMU_BIN:-}"
MACHINE_UUID="${APPLESILICON_VMAPPLE_UUID:-}"
FIRMWARE="${APPLESILICON_VMAPPLE_FIRMWARE:-}"
AUX="${APPLESILICON_VMAPPLE_AUX:-}"
DISK="${APPLESILICON_VMAPPLE_DISK:-}"
MACHINE_IDENTITY="${APPLESILICON_VMAPPLE_MACHINE_IDENTITY:-}"
HARDWARE_MODEL="${APPLESILICON_VMAPPLE_HARDWARE_MODEL:-}"
WORK_ROOT="${APPLESILICON_P4_01_WORK_ROOT:-${ROOT_DIR}/.build/p4.01}"
OUTPUT="${APPLESILICON_P4_01_SESSION_PLAN:-${WORK_ROOT}/${ROLE}-runtime-session-plan.json}"
OUTPUT_SECOND="${OUTPUT}.second"
LOG_DIR="${APPLESILICON_LOG_DIR:-${ROOT_DIR}/.logs}"
CLASSIFICATION="UNCLASSIFIED"
FINAL_STAGE="startup"

mkdir -p "${LOG_DIR}" "${WORK_ROOT}"
TIMESTAMP="$(date -u +"%Y%m%d-%H%M%S")"
LOG_FILE="${LOG_DIR}/AppleSilicon-p4.01-plan-${ROLE}-${TIMESTAMP}-$$.log"
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
    exit "${status}"
}
trap on_exit EXIT

fail() {
    CLASSIFICATION="$1"
    shift
    printf '%s\n' "$@" >&2
    exit 1
}

[[ "${ROLE}" == "probe" || "${ROLE}" == "reference" ]] || fail "P4_01_ROLE_INVALID" "Role must be probe or reference"
for name in QEMU_BIN MACHINE_UUID FIRMWARE AUX DISK MACHINE_IDENTITY; do
    [[ -n "${!name}" ]] || fail "P4_01_INPUT_MISSING" "Required environment variable input is empty: ${name}"
done
[[ -f "${P3_MANIFEST}" ]] || fail "P4_01_P3_MANIFEST_MISSING" "P3.06 integration manifest missing: ${P3_MANIFEST}"

echo "AppleSilicon version: ${VERSION}"
echo "Objective: P4.01 local runtime session planning"
echo "Role: ${ROLE}"
echo "Started UTC: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
echo "Sensitive input paths and machine UUID are intentionally not printed."

ARGS=(
    --policy "${POLICY}" plan
    --role "${ROLE}"
    --p3-06-manifest "${P3_MANIFEST}"
    --qemu-bin "${QEMU_BIN}"
    --machine-uuid "${MACHINE_UUID}"
    --firmware "${FIRMWARE}"
    --auxiliary-storage "${AUX}"
    --disk "${DISK}"
    --machine-identity "${MACHINE_IDENTITY}"
)
if [[ -n "${HARDWARE_MODEL}" ]]; then
    ARGS+=(--hardware-model "${HARDWARE_MODEL}")
fi

FINAL_STAGE="first-plan"
python3 "${TOOL}" "${ARGS[@]}" --output "${OUTPUT}" >/dev/null
FINAL_STAGE="second-plan"
python3 "${TOOL}" "${ARGS[@]}" --output "${OUTPUT_SECOND}" >/dev/null
FINAL_STAGE="determinism-check"
cmp -s "${OUTPUT}" "${OUTPUT_SECOND}" || fail "P4_01_PLAN_NONDETERMINISTIC" "Repeated P4.01 session plans differ"

FINAL_STAGE="plan-validation"
python3 - "${OUTPUT}" "${ROLE}" <<'PY'
import json
from pathlib import Path
import re, sys
data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
if data.get("classification") != "P4_01_SESSION_PLAN_READY":
    raise SystemExit("P4.01 plan classification mismatch")
if data.get("role") != sys.argv[2]:
    raise SystemExit("P4.01 plan role mismatch")
if data.get("guest_execution") is not False or data.get("runtime_evidence") is not False:
    raise SystemExit("P4.01 plan must remain pre-execution only")
fp = data.get("session_fingerprint")
if not isinstance(fp, str) or re.fullmatch(r"[0-9a-f]{64}", fp) is None:
    raise SystemExit("P4.01 session fingerprint invalid")
for forbidden in ("/Users/", "/home/", "C:\\Users\\"):
    if forbidden in Path(sys.argv[1]).read_text(encoding="utf-8"):
        raise SystemExit("local user path leaked into P4.01 plan")
print(f"Session fingerprint: {fp}")
PY

CLASSIFICATION="P4_01_SESSION_PLAN_READY"
FINAL_STAGE="complete"
echo "P4.01 runtime session plan: READY"
echo "No guest was launched. This plan is provenance metadata, not runtime evidence."
echo "Plan: ${OUTPUT}"

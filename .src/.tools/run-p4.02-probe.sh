#!/usr/bin/env bash
set -Eeuo pipefail

VERSION="4.1.0.0.0.0"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
POLICY="${ROOT_DIR}/.src/.configs/p4.02-probe-capture-policy.json"
CAPTURE_TOOL="${ROOT_DIR}/.src/.tools/probe-capture.py"
INTEGRITY_TOOL="${ROOT_DIR}/.src/.tools/runtime_integrity.py"
P3_RUNNER="${ROOT_DIR}/.src/.tools/run-p3.06-probe.sh"
COLLECTOR="${ROOT_DIR}/.src/.tools/collect-p1.10-probe.sh"
MANIFEST_TOOL="${ROOT_DIR}/.src/.tools/reference-manifest.py"
MANIFEST_POLICY="${ROOT_DIR}/.src/.configs/p1.09-manifest-policy.json"
TRACE_CONFIG="${ROOT_DIR}/.src/.configs/p1.07-trace-events"
SESSION_PLAN="${APPLESILICON_P4_01_PROBE_PLAN:-${ROOT_DIR}/.build/p4.01/probe-runtime-session-plan.json}"
P3_MANIFEST="${APPLESILICON_P3_06_MANIFEST:-${ROOT_DIR}/.build/p3.06/platform-integration-manifest.json}"
P2_MANIFEST="${APPLESILICON_P2_06_MANIFEST:-${ROOT_DIR}/.build/p2.06/integration-manifest.json}"
QEMU_BIN="${APPLESILICON_QEMU_BIN:-}"
MACHINE_UUID="${APPLESILICON_VMAPPLE_UUID:-}"
FIRMWARE="${APPLESILICON_VMAPPLE_FIRMWARE:-}"
AUX="${APPLESILICON_VMAPPLE_AUX:-}"
DISK="${APPLESILICON_VMAPPLE_DISK:-}"
MACHINE_IDENTITY="${APPLESILICON_VMAPPLE_MACHINE_IDENTITY:-}"
HARDWARE_MODEL="${APPLESILICON_VMAPPLE_HARDWARE_MODEL:-}"
RAM="4G"
SMP="4"
PROBE_SECONDS="30"
GRACE_SECONDS="3"
DEBUG_ITEMS="guest_errors,unimp,int,cpu_reset"
BASE_LOG_DIR="${APPLESILICON_LOG_DIR:-${ROOT_DIR}/.logs}"
CLASSIFICATION="UNCLASSIFIED"
FINAL_STAGE="startup"

mkdir -p "${BASE_LOG_DIR}"
TIMESTAMP="$(date -u +"%Y%m%d-%H%M%S")"
RUN_ID="p4.02-probe-${TIMESTAMP}-$$"
WORK_ROOT="${APPLESILICON_P4_02_WORK_ROOT:-${ROOT_DIR}/.build/p4.02/${RUN_ID}}"
RUN_LOG_DIR="${BASE_LOG_DIR}/${RUN_ID}"
WRAPPER_LOG="${BASE_LOG_DIR}/AppleSilicon-p4.02-${TIMESTAMP}-$$.log"
PREFLIGHT_BEFORE="${WORK_ROOT}/preflight-before.json"
PREFLIGHT_AFTER="${WORK_ROOT}/preflight-after.json"
PROBE_MANIFEST="${WORK_ROOT}/probe-manifest.json"
CAPTURE_MANIFEST="${WORK_ROOT}/probe-capture.json"
mkdir -p "${WORK_ROOT}" "${RUN_LOG_DIR}"
exec > >(tee "${WRAPPER_LOG}") 2>&1

on_exit() {
    local status=$?
    trap - EXIT
    echo "Classification: ${CLASSIFICATION}"
    echo "Final stage: ${FINAL_STAGE}"
    echo "Exit code: ${status}"
    echo "Finished UTC: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
    echo "Wrapper log: ${WRAPPER_LOG}"
    echo "Work root: ${WORK_ROOT}"
    exit "${status}"
}
trap on_exit EXIT
fail() { CLASSIFICATION="$1"; shift; printf '%s\n' "$@" >&2; exit 1; }
require_file() {
    local classification="$1" label="$2" path="$3"
    [[ -n "${path}" ]] || fail "${classification}" "${label} is not configured"
    [[ -f "${path}" && -r "${path}" ]] || fail "${classification}" "${label} is missing or unreadable"
}

for pair in \
    "P4_02_SESSION_PLAN_MISSING|P4.01 probe session plan|${SESSION_PLAN}" \
    "P4_02_P3_MANIFEST_MISSING|P3.06 integration manifest|${P3_MANIFEST}" \
    "P4_02_P2_MANIFEST_MISSING|P2.06 integration manifest|${P2_MANIFEST}" \
    "P4_02_INPUT_FIRMWARE_MISSING|VMApple firmware|${FIRMWARE}" \
    "P4_02_INPUT_AUX_MISSING|VMApple auxiliary storage|${AUX}" \
    "P4_02_INPUT_DISK_MISSING|VMApple root disk|${DISK}" \
    "P4_02_INPUT_IDENTITY_MISSING|compiled P3.02 machine identity|${MACHINE_IDENTITY}"; do
    IFS='|' read -r classification label path <<< "${pair}"
    require_file "${classification}" "${label}" "${path}"
done
[[ -n "${QEMU_BIN}" && -x "${QEMU_BIN}" ]] || fail "P4_02_QEMU_MISSING" "QEMU binary is missing or not executable"
[[ -n "${MACHINE_UUID}" ]] || fail "P4_02_UUID_MISSING" "VMApple uint64 machine id is not configured"
if [[ -n "${HARDWARE_MODEL}" ]]; then require_file "P4_02_INPUT_HARDWARE_MODEL_MISSING" "VMApple hardware model" "${HARDWARE_MODEL}"; fi
for tool in "${CAPTURE_TOOL}" "${INTEGRITY_TOOL}" "${P3_RUNNER}" "${COLLECTOR}" "${MANIFEST_TOOL}"; do
    [[ -x "${tool}" ]] || fail "P4_02_TOOL_MISSING" "Required dependency is not executable: ${tool##*/}"
done

MACHINE_ID="$(python3 "${INTEGRITY_TOOL}" machine-id "${MACHINE_UUID}")" || fail "P4_02_UUID_INVALID" "VMApple machine id must be uint64 decimal or 0x-prefixed"
python3 "${INTEGRITY_TOOL}" identity --compiled "${MACHINE_IDENTITY}" --machine-id "${MACHINE_ID}" >/dev/null ||
    fail "P4_02_IDENTITY_INVALID" "Compiled P3.02 identity does not bind the configured VMApple machine id"

echo "AppleSilicon version: ${VERSION}"
echo "Objective: P4.02 Integrated TCG Probe Capture"
echo "Started UTC: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
echo "Runtime contract: vmapple / tcg / apple-gxf / RAM=${RAM} / SMP=${SMP} / capture=${PROBE_SECONDS}s"
echo "Sensitive VM input paths and the raw machine id are intentionally not printed."

PREFLIGHT_ARGS=(
    --policy "${POLICY}" preflight --session-plan "${SESSION_PLAN}" --p3-06-manifest "${P3_MANIFEST}"
    --qemu-bin "${QEMU_BIN}" --machine-uuid "${MACHINE_ID}" --firmware "${FIRMWARE}"
    --auxiliary-storage "${AUX}" --disk "${DISK}" --machine-identity "${MACHINE_IDENTITY}"
)
if [[ -n "${HARDWARE_MODEL}" ]]; then PREFLIGHT_ARGS+=(--hardware-model "${HARDWARE_MODEL}"); fi

FINAL_STAGE="preflight-before"
python3 "${CAPTURE_TOOL}" "${PREFLIGHT_ARGS[@]}" --output "${PREFLIGHT_BEFORE}" >/dev/null || fail "P4_02_PREFLIGHT_FAILED" "P4.02 preflight failed before guest execution"

FINAL_STAGE="runtime-delegate"
set +e
APPLESILICON_P3_06_MANIFEST="${P3_MANIFEST}" \
APPLESILICON_P2_06_MANIFEST="${P2_MANIFEST}" \
APPLESILICON_QEMU_BIN="${QEMU_BIN}" \
APPLESILICON_VMAPPLE_UUID="${MACHINE_ID}" \
APPLESILICON_VMAPPLE_FIRMWARE="${FIRMWARE}" \
APPLESILICON_VMAPPLE_AUX="${AUX}" \
APPLESILICON_VMAPPLE_DISK="${DISK}" \
APPLESILICON_VMAPPLE_MACHINE_IDENTITY="${MACHINE_IDENTITY}" \
APPLESILICON_VMAPPLE_HARDWARE_MODEL="${HARDWARE_MODEL}" \
APPLESILICON_VMAPPLE_RAM="${RAM}" \
APPLESILICON_VMAPPLE_SMP="${SMP}" \
APPLESILICON_P1_07_PROBE_SECONDS="${PROBE_SECONDS}" \
APPLESILICON_P1_07_GRACE_SECONDS="${GRACE_SECONDS}" \
APPLESILICON_P1_07_DEBUG_ITEMS="${DEBUG_ITEMS}" \
APPLESILICON_P1_07_TRACE_EVENTS="${TRACE_CONFIG}" \
APPLESILICON_LOG_DIR="${RUN_LOG_DIR}" \
"${P3_RUNNER}"
RUNTIME_STATUS=$?
set -e
[[ ${RUNTIME_STATUS} -eq 0 ]] || fail "P4_02_RUNTIME_FAILED" "Integrated P3.06/P2.06/P1.07 runtime delegate failed with status ${RUNTIME_STATUS}"

FINAL_STAGE="launcher-discovery"
LAUNCHER_LOG=""; LAUNCHER_COUNT=0
shopt -s nullglob
for candidate in "${RUN_LOG_DIR}"/AppleSilicon-p1.07-*.log; do
    case "${candidate}" in *-serial.log|*-qemu.log|*-trace-help.log) continue ;; esac
    LAUNCHER_LOG="${candidate}"; LAUNCHER_COUNT=$((LAUNCHER_COUNT + 1))
done
shopt -u nullglob
[[ ${LAUNCHER_COUNT} -eq 1 ]] || fail "P4_02_LAUNCHER_AMBIGUOUS" "Expected exactly one P1.07 launcher log, observed ${LAUNCHER_COUNT}"

FINAL_STAGE="runtime-parameter-validation"
python3 - "${LAUNCHER_LOG}" <<'PY'
from pathlib import Path
import sys
text = Path(sys.argv[1]).read_text(encoding="utf-8", errors="replace")
required = {"Accelerator":"tcg","CPU profile":"apple-gxf","SMP":"4","RAM":"4G","Probe seconds":"30","Grace seconds":"3","Debug items":"guest_errors,unimp,int,cpu_reset"}
for key, expected in required.items():
    values = [line.split(": ", 1)[1] for line in text.splitlines() if line.startswith(key + ": ")]
    if not values or values[0] != expected: raise SystemExit(f"runtime parameter drift: {key}")
classification = [line.split(": ", 1)[1] for line in text.splitlines() if line.startswith("Classification: ")]
if not classification or classification[-1] not in ("P1_07_PROBE_EXITED", "P1_07_PROBE_TIMED_OUT"):
    raise SystemExit("P1.07 did not produce an admissible completed probe classification")
PY

FINAL_STAGE="probe-manifest-collection"
COLLECT_ENV=(
    APPLESILICON_LOG_DIR="${RUN_LOG_DIR}" APPLESILICON_P1_10_WORK_ROOT="${WORK_ROOT}"
    APPLESILICON_P1_10_PROBE_LAUNCHER_LOG="${LAUNCHER_LOG}" APPLESILICON_P1_10_PROBE_MANIFEST="${PROBE_MANIFEST}"
    APPLESILICON_VMAPPLE_FIRMWARE="${FIRMWARE}" APPLESILICON_VMAPPLE_AUX="${AUX}"
    APPLESILICON_VMAPPLE_DISK="${DISK}" APPLESILICON_VMAPPLE_MACHINE_IDENTITY="${MACHINE_IDENTITY}"
    APPLESILICON_P1_07_TRACE_EVENTS="${TRACE_CONFIG}"
)
if [[ -n "${HARDWARE_MODEL}" ]]; then COLLECT_ENV+=(APPLESILICON_VMAPPLE_HARDWARE_MODEL="${HARDWARE_MODEL}"); fi
env "${COLLECT_ENV[@]}" "${COLLECTOR}" || fail "P4_02_PROBE_MANIFEST_FAILED" "P1.09-compatible probe manifest collection failed"
python3 "${MANIFEST_TOOL}" validate "${PROBE_MANIFEST}" --policy "${MANIFEST_POLICY}" || fail "P4_02_PROBE_MANIFEST_INVALID" "Generated probe manifest failed P1.09 validator"

FINAL_STAGE="manifest-runtime-parameter-validation"
python3 - "${PROBE_MANIFEST}" <<'PY'
import json, sys
from pathlib import Path
data=json.loads(Path(sys.argv[1]).read_text(encoding="utf-8")); m=data.get("machine",{})
if m != {"type":"vmapple","accelerator":"tcg","cpu_model":"apple-gxf","ram_mib":4096,"smp":4}: raise SystemExit("probe machine contract drift")
PY

FINAL_STAGE="preflight-after"
python3 "${CAPTURE_TOOL}" "${PREFLIGHT_ARGS[@]}" --output "${PREFLIGHT_AFTER}" >/dev/null || fail "P4_02_POSTFLIGHT_FAILED" "P4.02 provenance check failed after guest execution"
cmp -s "${PREFLIGHT_BEFORE}" "${PREFLIGHT_AFTER}" || fail "P4_02_PROVENANCE_CHANGED" "QEMU/input provenance changed during probe"

FINAL_STAGE="capture-finalization"
python3 "${CAPTURE_TOOL}" --policy "${POLICY}" finalize --session-plan "${SESSION_PLAN}" --probe-manifest "${PROBE_MANIFEST}" \
    --launcher-log "${LAUNCHER_LOG}" --preflight "${PREFLIGHT_BEFORE}" --output "${CAPTURE_MANIFEST}" >/dev/null ||
    fail "P4_02_CAPTURE_FINALIZATION_FAILED" "P4.02 capture manifest finalization failed"
python3 - "${CAPTURE_MANIFEST}" <<'PY'
import json,re,sys
from pathlib import Path
p=Path(sys.argv[1]); text=p.read_text(encoding="utf-8"); d=json.loads(text)
if d.get("classification")!="P4_02_PROBE_CAPTURE_READY" or d.get("divergence_promoted") is not False: raise SystemExit("P4.02 capture state invalid")
if re.fullmatch(r"[0-9a-f]{64}",str(d.get("capture_fingerprint",""))) is None: raise SystemExit("P4.02 capture fingerprint invalid")
for forbidden in ("/Users/","/home/","C:\\Users\\"):
    if forbidden in text: raise SystemExit("local user path leaked into P4.02 capture")
PY
CLASSIFICATION="P4_02_PROBE_CAPTURE_READY"
FINAL_STAGE="complete"
echo "P4.02 probe capture: READY"
echo "No divergence was promoted. P1.10 remains authoritative for promotion."
echo "Probe manifest: ${PROBE_MANIFEST}"
echo "Capture manifest: ${CAPTURE_MANIFEST}"

#!/usr/bin/env bash
set -Eeuo pipefail

VERSION="4.2.0.0.0.0"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
POLICY="${ROOT_DIR}/.src/.configs/p4.03-reference-capture-policy.json"
CAPTURE_TOOL="${ROOT_DIR}/.src/.tools/reference-capture.py"
REFERENCE_RUNNER="${ROOT_DIR}/.src/.tools/run-p1.09-reference.sh"
MANIFEST_TOOL="${ROOT_DIR}/.src/.tools/reference-manifest.py"
MANIFEST_POLICY="${ROOT_DIR}/.src/.configs/p1.09-manifest-policy.json"
TRACE_CONFIG="${ROOT_DIR}/.src/.configs/p1.07-trace-events"
SESSION_PLAN="${APPLESILICON_P4_01_REFERENCE_PLAN:-${ROOT_DIR}/.build/p4.01/reference-runtime-session-plan.json}"
P3_MANIFEST="${APPLESILICON_P3_06_MANIFEST:-${ROOT_DIR}/.build/p3.06/platform-integration-manifest.json}"
QEMU_BIN="${APPLESILICON_QEMU_BIN:-}"
MACHINE_UUID="${APPLESILICON_VMAPPLE_UUID:-}"
FIRMWARE="${APPLESILICON_VMAPPLE_FIRMWARE:-}"
AUX="${APPLESILICON_VMAPPLE_AUX:-}"
DISK="${APPLESILICON_VMAPPLE_DISK:-}"
MACHINE_IDENTITY="${APPLESILICON_VMAPPLE_MACHINE_IDENTITY:-}"
HARDWARE_MODEL="${APPLESILICON_VMAPPLE_HARDWARE_MODEL:-}"
RAM="4G"
SMP="4"
REFERENCE_SECONDS="30"
GRACE_SECONDS="3"
DEBUG_ITEMS="guest_errors,unimp,int,cpu_reset"
BASE_LOG_DIR="${APPLESILICON_LOG_DIR:-${ROOT_DIR}/.logs}"
CLASSIFICATION="UNCLASSIFIED"
FINAL_STAGE="startup"

mkdir -p "${BASE_LOG_DIR}"
TIMESTAMP="$(date -u +"%Y%m%d-%H%M%S")"
RUN_ID="p4.03-reference-${TIMESTAMP}-$$"
WORK_ROOT="${APPLESILICON_P4_03_WORK_ROOT:-${ROOT_DIR}/.build/p4.03/${RUN_ID}}"
RUN_LOG_DIR="${BASE_LOG_DIR}/${RUN_ID}"
WRAPPER_LOG="${BASE_LOG_DIR}/AppleSilicon-p4.03-${TIMESTAMP}-$$.log"
PREFLIGHT_BEFORE="${WORK_ROOT}/preflight-before.json"
PREFLIGHT_AFTER="${WORK_ROOT}/preflight-after.json"
REFERENCE_MANIFEST="${WORK_ROOT}/reference-manifest.json"
CAPTURE_MANIFEST="${WORK_ROOT}/reference-capture.json"
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

fail() {
    CLASSIFICATION="$1"
    shift
    printf '%s\n' "$@" >&2
    exit 1
}

require_file() {
    local classification="$1"
    local label="$2"
    local path="$3"
    [[ -n "${path}" ]] || fail "${classification}" "${label} is not configured"
    [[ -f "${path}" && -r "${path}" ]] || fail "${classification}" "${label} is missing or unreadable"
}

[[ "$(uname -s 2>/dev/null || true)" == "Darwin" && "$(uname -m 2>/dev/null || true)" == "arm64" ]] ||
    fail "P4_03_REFERENCE_HOST_UNAVAILABLE" "P4.03 requires a real Darwin/arm64 Apple Silicon reference host"

for pair in \
    "P4_03_SESSION_PLAN_MISSING|P4.01 reference session plan|${SESSION_PLAN}" \
    "P4_03_P3_MANIFEST_MISSING|P3.06 integration manifest|${P3_MANIFEST}" \
    "P4_03_INPUT_FIRMWARE_MISSING|VMApple firmware|${FIRMWARE}" \
    "P4_03_INPUT_AUX_MISSING|VMApple auxiliary storage|${AUX}" \
    "P4_03_INPUT_DISK_MISSING|VMApple root disk|${DISK}" \
    "P4_03_INPUT_IDENTITY_MISSING|VMApple machine identity|${MACHINE_IDENTITY}"; do
    IFS='|' read -r classification label path <<< "${pair}"
    require_file "${classification}" "${label}" "${path}"
done
[[ -n "${QEMU_BIN}" && -x "${QEMU_BIN}" ]] || fail "P4_03_QEMU_MISSING" "QEMU binary is missing or not executable"
[[ -n "${MACHINE_UUID}" ]] || fail "P4_03_UUID_MISSING" "VMApple machine UUID is not configured"
if [[ -n "${HARDWARE_MODEL}" ]]; then
    require_file "P4_03_INPUT_HARDWARE_MODEL_MISSING" "VMApple hardware model" "${HARDWARE_MODEL}"
fi
for tool in "${CAPTURE_TOOL}" "${REFERENCE_RUNNER}" "${MANIFEST_TOOL}"; do
    [[ -x "${tool}" ]] || fail "P4_03_TOOL_MISSING" "Required P4.03 dependency is not executable: ${tool##*/}"
done

CANONICAL_UUID="$(python3 - "${MACHINE_UUID}" <<'PY'
import sys, uuid
try:
    print(str(uuid.UUID(sys.argv[1])).lower())
except ValueError:
    raise SystemExit("invalid machine UUID")
PY
)" || fail "P4_03_UUID_INVALID" "Machine UUID is invalid"

echo "AppleSilicon version: ${VERSION}"
echo "Objective: P4.03 Apple Silicon HVF Reference Capture"
echo "Started UTC: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
echo "Runtime contract: vmapple / hvf / host / Darwin arm64 / RAM=${RAM} / SMP=${SMP} / capture=${REFERENCE_SECONDS}s"
echo "Sensitive VM input paths and the raw machine UUID are intentionally not printed."

PREFLIGHT_ARGS=(
    --policy "${POLICY}" preflight
    --session-plan "${SESSION_PLAN}"
    --p3-06-manifest "${P3_MANIFEST}"
    --qemu-bin "${QEMU_BIN}"
    --machine-uuid "${CANONICAL_UUID}"
    --firmware "${FIRMWARE}"
    --auxiliary-storage "${AUX}"
    --disk "${DISK}"
    --machine-identity "${MACHINE_IDENTITY}"
)
if [[ -n "${HARDWARE_MODEL}" ]]; then
    PREFLIGHT_ARGS+=(--hardware-model "${HARDWARE_MODEL}")
fi

FINAL_STAGE="preflight-before"
python3 "${CAPTURE_TOOL}" "${PREFLIGHT_ARGS[@]}" --output "${PREFLIGHT_BEFORE}" >/dev/null ||
    fail "P4_03_PREFLIGHT_FAILED" "P4.03 preflight failed before guest execution"

FINAL_STAGE="reference-runtime"
set +e
APPLESILICON_QEMU_BIN="${QEMU_BIN}" \
APPLESILICON_VMAPPLE_UUID="${CANONICAL_UUID}" \
APPLESILICON_VMAPPLE_FIRMWARE="${FIRMWARE}" \
APPLESILICON_VMAPPLE_AUX="${AUX}" \
APPLESILICON_VMAPPLE_DISK="${DISK}" \
APPLESILICON_VMAPPLE_MACHINE_IDENTITY="${MACHINE_IDENTITY}" \
APPLESILICON_VMAPPLE_RAM="${RAM}" \
APPLESILICON_VMAPPLE_SMP="${SMP}" \
APPLESILICON_P1_09_REFERENCE_SECONDS="${REFERENCE_SECONDS}" \
APPLESILICON_P1_09_GRACE_SECONDS="${GRACE_SECONDS}" \
APPLESILICON_P1_09_DEBUG_ITEMS="${DEBUG_ITEMS}" \
APPLESILICON_P1_09_TRACE_EVENTS="${TRACE_CONFIG}" \
APPLESILICON_LOG_DIR="${RUN_LOG_DIR}" \
APPLESILICON_VMAPPLE_HARDWARE_MODEL="${HARDWARE_MODEL}" \
"${REFERENCE_RUNNER}"
RUNTIME_STATUS=$?
set -e
[[ ${RUNTIME_STATUS} -eq 0 ]] || fail "P4_03_REFERENCE_RUNTIME_FAILED" "P1.09 reference runner failed with status ${RUNTIME_STATUS}"

FINAL_STAGE="reference-artifact-discovery"
LAUNCHER_LOG=""
SOURCE_MANIFEST=""
LAUNCHER_COUNT=0
MANIFEST_COUNT=0
shopt -s nullglob
for candidate in "${RUN_LOG_DIR}"/AppleSilicon-p1.09-reference-*.log; do
    case "${candidate}" in
        *-serial.log|*-qemu.log|*-trace-help.log) continue ;;
    esac
    LAUNCHER_LOG="${candidate}"
    LAUNCHER_COUNT=$((LAUNCHER_COUNT + 1))
done
for candidate in "${RUN_LOG_DIR}"/AppleSilicon-p1.09-reference-*-manifest.json; do
    SOURCE_MANIFEST="${candidate}"
    MANIFEST_COUNT=$((MANIFEST_COUNT + 1))
done
shopt -u nullglob
[[ ${LAUNCHER_COUNT} -eq 1 ]] || fail "P4_03_LAUNCHER_AMBIGUOUS" "Expected exactly one P1.09 launcher log, observed ${LAUNCHER_COUNT}"
[[ ${MANIFEST_COUNT} -eq 1 ]] || fail "P4_03_MANIFEST_AMBIGUOUS" "Expected exactly one P1.09 reference manifest, observed ${MANIFEST_COUNT}"
cp "${SOURCE_MANIFEST}" "${REFERENCE_MANIFEST}"

FINAL_STAGE="runtime-parameter-validation"
python3 - "${LAUNCHER_LOG}" <<'PY'
from pathlib import Path
import sys
text = Path(sys.argv[1]).read_text(encoding="utf-8", errors="replace")
required = {
    "Host OS": "Darwin",
    "Host architecture": "arm64",
    "Accelerator": "hvf",
    "CPU profile": "host",
    "SMP": "4",
    "RAM": "4G",
    "Reference seconds": "30",
}
for key, expected in required.items():
    values = [line.split(": ", 1)[1] for line in text.splitlines() if line.startswith(key + ": ")]
    if not values or values[0] != expected:
        raise SystemExit(f"runtime parameter drift: {key}: expected {expected!r}, observed {values[0] if values else None!r}")
classification = [line.split(": ", 1)[1] for line in text.splitlines() if line.startswith("Classification: ")]
if not classification or not classification[-1].startswith("P1_09_REFERENCE_"):
    raise SystemExit("P1.09 did not produce a completed reference classification")
PY

FINAL_STAGE="reference-manifest-validation"
python3 "${MANIFEST_TOOL}" validate "${REFERENCE_MANIFEST}" --policy "${MANIFEST_POLICY}" ||
    fail "P4_03_REFERENCE_MANIFEST_INVALID" "Generated reference manifest failed the authoritative P1.09 validator"
python3 - "${REFERENCE_MANIFEST}" <<'PY'
import json, sys
from pathlib import Path
data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
machine = data.get("machine", {})
if data.get("role") != "reference":
    raise SystemExit("reference manifest role drift")
if machine.get("type") != "vmapple" or machine.get("accelerator") != "hvf" or machine.get("cpu_model") != "host":
    raise SystemExit("reference machine contract drift")
if machine.get("ram_mib") != 4096 or machine.get("smp") != 4:
    raise SystemExit("reference RAM/SMP drift")
PY

FINAL_STAGE="preflight-after"
python3 "${CAPTURE_TOOL}" "${PREFLIGHT_ARGS[@]}" --output "${PREFLIGHT_AFTER}" >/dev/null ||
    fail "P4_03_POSTFLIGHT_FAILED" "P4.03 provenance check failed after guest execution"
cmp -s "${PREFLIGHT_BEFORE}" "${PREFLIGHT_AFTER}" ||
    fail "P4_03_PROVENANCE_CHANGED" "QEMU/input provenance changed during the reference session"

FINAL_STAGE="capture-finalization"
python3 "${CAPTURE_TOOL}" --policy "${POLICY}" finalize \
    --session-plan "${SESSION_PLAN}" \
    --reference-manifest "${REFERENCE_MANIFEST}" \
    --launcher-log "${LAUNCHER_LOG}" \
    --preflight "${PREFLIGHT_BEFORE}" \
    --output "${CAPTURE_MANIFEST}" >/dev/null ||
    fail "P4_03_CAPTURE_FINALIZATION_FAILED" "P4.03 capture manifest finalization failed"

python3 - "${CAPTURE_MANIFEST}" <<'PY'
import json, re, sys
from pathlib import Path
path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")
data = json.loads(text)
if data.get("classification") != "P4_03_REFERENCE_CAPTURE_READY":
    raise SystemExit("P4.03 capture classification mismatch")
fp = data.get("capture_fingerprint")
if not isinstance(fp, str) or re.fullmatch(r"[0-9a-f]{64}", fp) is None:
    raise SystemExit("P4.03 capture fingerprint invalid")
if data.get("divergence_promoted") is not False:
    raise SystemExit("P4.03 must not promote a divergence")
for forbidden in ("/Users/", "/home/", "C:\\Users\\"):
    if forbidden in text:
        raise SystemExit("local user path leaked into P4.03 capture manifest")
print(f"Capture fingerprint: {fp}")
PY

CLASSIFICATION="P4_03_REFERENCE_CAPTURE_READY"
FINAL_STAGE="complete"
echo "P4.03 reference capture: READY"
echo "Reference manifest and capture metadata are sanitized; guest assets remain local."
echo "No divergence was promoted. P1.10 remains authoritative for promotion."
echo "Reference manifest: ${REFERENCE_MANIFEST}"
echo "Capture manifest: ${CAPTURE_MANIFEST}"

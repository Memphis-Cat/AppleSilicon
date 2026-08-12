#!/usr/bin/env bash

set -Eeuo pipefail

VERSION="1.0.0.0.0.0"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
MANIFEST_TOOL="${ROOT_DIR}/.src/.tools/reference-manifest.py"
INTEGRITY_TOOL="${ROOT_DIR}/.src/.tools/runtime_integrity.py"
MANIFEST_POLICY="${APPLESILICON_P1_09_MANIFEST_POLICY:-${ROOT_DIR}/.src/.configs/p1.09-manifest-policy.json}"
TRACE_CONFIG="${APPLESILICON_P1_07_TRACE_EVENTS:-${ROOT_DIR}/.src/.configs/p1.07-trace-events}"
LOG_DIR="${APPLESILICON_LOG_DIR:-${ROOT_DIR}/.logs}"
WORK_ROOT="${APPLESILICON_P1_10_WORK_ROOT:-${ROOT_DIR}/.build/.p1.10}"
LAUNCHER_LOG="${APPLESILICON_P1_10_PROBE_LAUNCHER_LOG:-}"
FIRMWARE="${APPLESILICON_VMAPPLE_FIRMWARE:-}"
AUX="${APPLESILICON_VMAPPLE_AUX:-}"
DISK="${APPLESILICON_VMAPPLE_DISK:-}"
MACHINE_IDENTITY="${APPLESILICON_VMAPPLE_MACHINE_IDENTITY:-}"
HARDWARE_MODEL="${APPLESILICON_VMAPPLE_HARDWARE_MODEL:-}"
CLASSIFICATION="UNCLASSIFIED"
FINAL_STAGE="startup"

mkdir -p "${LOG_DIR}" "${WORK_ROOT}"
TIMESTAMP="$(date -u +"%Y%m%d-%H%M%S")"
LOG_FILE="${LOG_DIR}/AppleSilicon-p1.10-probe-collect-${TIMESTAMP}-$$.log"
OUTPUT_MANIFEST="${APPLESILICON_P1_10_PROBE_MANIFEST:-${WORK_ROOT}/probe-manifest-${TIMESTAMP}-$$.json}"
exec > >(tee "${LOG_FILE}") 2>&1

on_exit() {
    local status=$?
    trap - EXIT
    echo "Classification: ${CLASSIFICATION}"
    echo "Final stage: ${FINAL_STAGE}"
    echo "Exit code: ${status}"
    echo "Finished UTC: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
    echo "Log file: ${LOG_FILE}"
    echo "Output manifest: ${OUTPUT_MANIFEST}"
    exit "${status}"
}
trap on_exit EXIT

fail() { CLASSIFICATION="$1"; shift; printf '%s\n' "$@" >&2; exit 1; }
require_file() {
    local classification="$1" label="$2" path="$3"
    [[ -n "${path}" ]] || fail "${classification}" "${label} path is not configured."
    [[ -f "${path}" && -r "${path}" ]] || fail "${classification}" "${label} is missing or unreadable: ${path}"
}
extract_last() { local label="$1" path="$2"; sed -n "s/^${label}: //p" "${path}" | tail -n 1; }
extract_first() { local label="$1" path="$2"; sed -n "s/^${label}: //p" "${path}" | head -n 1; }

require_file "PROBE_LAUNCHER_MISSING" "P1.07 launcher log" "${LAUNCHER_LOG}"
require_file "MANIFEST_TOOL_MISSING" "P1.09 manifest tool" "${MANIFEST_TOOL}"
require_file "RUNTIME_INTEGRITY_MISSING" "runtime integrity tool" "${INTEGRITY_TOOL}"
require_file "MANIFEST_POLICY_MISSING" "P1.09 manifest policy" "${MANIFEST_POLICY}"
require_file "TRACE_CONFIG_MISSING" "P1.07 trace configuration" "${TRACE_CONFIG}"
require_file "INPUT_FIRMWARE_MISSING" "VMApple firmware" "${FIRMWARE}"
require_file "INPUT_AUX_MISSING" "VMApple auxiliary storage" "${AUX}"
require_file "INPUT_DISK_MISSING" "VMApple disk" "${DISK}"
require_file "INPUT_MACHINE_IDENTITY_MISSING" "compiled P3.02 machine identity" "${MACHINE_IDENTITY}"
if [[ -n "${HARDWARE_MODEL}" ]]; then require_file "INPUT_HARDWARE_MODEL_MISSING" "VMApple hardware model" "${HARDWARE_MODEL}"; fi

FINAL_STAGE="launcher-metadata"
RUN_ID="$(extract_first "Run ID" "${LAUNCHER_LOG}")"
STARTED_UTC="$(extract_first "Started UTC" "${LAUNCHER_LOG}")"
ENDED_UTC="$(extract_last "Finished UTC" "${LAUNCHER_LOG}")"
RESULT="$(extract_last "Classification" "${LAUNCHER_LOG}")"
HOST_OS="$(extract_first "Host OS" "${LAUNCHER_LOG}")"
HOST_ARCH="$(extract_first "Host architecture" "${LAUNCHER_LOG}")"
ACCEL="$(extract_first "Accelerator" "${LAUNCHER_LOG}")"
CPU_PROFILE="$(extract_first "CPU profile" "${LAUNCHER_LOG}")"
SMP="$(extract_first "SMP" "${LAUNCHER_LOG}")"
RAM="$(extract_first "RAM" "${LAUNCHER_LOG}")"
DEBUG_ITEMS="$(extract_first "Debug items" "${LAUNCHER_LOG}")"
MACHINE_ID_HASH="$(extract_first "Machine ID SHA-256" "${LAUNCHER_LOG}")"
SERIAL_LOG="$(extract_last "Serial log" "${LAUNCHER_LOG}")"
QEMU_DEBUG_LOG="$(extract_last "QEMU debug log" "${LAUNCHER_LOG}")"
TRACE_HELP_LOG="$(extract_last "Trace capability log" "${LAUNCHER_LOG}")"

for pair in \
    "Run ID=${RUN_ID}" "Started UTC=${STARTED_UTC}" "Finished UTC=${ENDED_UTC}" "Classification=${RESULT}" \
    "Host OS=${HOST_OS}" "Host architecture=${HOST_ARCH}" "Accelerator=${ACCEL}" "CPU profile=${CPU_PROFILE}" \
    "SMP=${SMP}" "RAM=${RAM}" "Debug items=${DEBUG_ITEMS}" "Machine ID SHA-256=${MACHINE_ID_HASH}" \
    "Serial log=${SERIAL_LOG}" "QEMU debug log=${QEMU_DEBUG_LOG}" "Trace capability log=${TRACE_HELP_LOG}"; do
    key="${pair%%=*}"; value="${pair#*=}"
    [[ -n "${value}" ]] || fail "PROBE_METADATA_INCOMPLETE" "Missing ${key} in P1.07 launcher log."
done
[[ "${RUN_ID}" =~ ^p1\.07-probe-[0-9]{8}-[0-9]{6}-[0-9]+$ ]] || fail "PROBE_RUN_ID_INVALID" "Launcher run ID is invalid: ${RUN_ID}"
case "${RESULT}" in P1_07_PROBE_EXITED|P1_07_PROBE_TIMED_OUT) ;; *) fail "PROBE_RESULT_NOT_RUNTIME" "Launcher result is not an admissible completed P1.07 runtime result: ${RESULT}" ;; esac
[[ "${ACCEL}" == "tcg" ]] || fail "PROBE_ACCELERATOR_INVALID" "Probe launcher must report TCG."
case "${CPU_PROFILE}" in max|apple-gxf) ;; *) fail "PROBE_CPU_INVALID" "Probe CPU must be max or apple-gxf." ;; esac
[[ "${SMP}" =~ ^[0-9]+$ ]] && (( SMP > 0 )) || fail "PROBE_SMP_INVALID" "Invalid SMP: ${SMP}"
[[ "${MACHINE_ID_HASH}" =~ ^[0-9a-f]{64}$ ]] || fail "PROBE_MACHINE_ID_INVALID" "Invalid machine-id digest in launcher log."

FINAL_STAGE="identity-binding"
IDENTITY_INFO="$(python3 "${INTEGRITY_TOOL}" identity --compiled "${MACHINE_IDENTITY}")" || fail "PROBE_IDENTITY_INVALID" "Compiled identity failed validation."
IDENTITY_MACHINE_ID="$(python3 - "${IDENTITY_INFO}" <<'PY'
import json, sys
print(json.loads(sys.argv[1])["machine_id_decimal"])
PY
)"
IDENTITY_MACHINE_HASH="$(python3 - "${IDENTITY_MACHINE_ID}" <<'PY'
import hashlib, sys
print(hashlib.sha256(sys.argv[1].encode("ascii")).hexdigest())
PY
)"
[[ "${IDENTITY_MACHINE_HASH}" == "${MACHINE_ID_HASH}" ]] || fail "PROBE_IDENTITY_MISMATCH" "Launcher machine-id digest differs from compiled identity."

require_file "PROBE_SERIAL_MISSING" "P1.07 serial log" "${SERIAL_LOG}"
require_file "PROBE_QEMU_LOG_MISSING" "P1.07 QEMU debug log" "${QEMU_DEBUG_LOG}"
require_file "PROBE_TRACE_HELP_MISSING" "P1.07 trace capability log" "${TRACE_HELP_LOG}"
CURRENT_OS="$(uname -s 2>/dev/null || printf '%s' unknown)"; CURRENT_ARCH="$(uname -m 2>/dev/null || printf '%s' unknown)"
[[ "${CURRENT_OS}" == "${HOST_OS}" && "${CURRENT_ARCH}" == "${HOST_ARCH}" ]] || fail "PROBE_HOST_CHANGED" "Collector must run on the same host immediately after probe."

if [[ "${RAM}" == *G ]]; then RAM_VALUE="${RAM%G}"; [[ "${RAM_VALUE}" =~ ^[0-9]+$ ]] || fail "PROBE_RAM_INVALID" "Unsupported RAM: ${RAM}"; RAM_MIB=$((RAM_VALUE * 1024));
elif [[ "${RAM}" == *M ]]; then RAM_MIB="${RAM%M}"; [[ "${RAM_MIB}" =~ ^[0-9]+$ ]] || fail "PROBE_RAM_INVALID" "Unsupported RAM: ${RAM}";
else fail "PROBE_RAM_INVALID" "RAM must use G or M units."; fi

if command -v sysctl >/dev/null 2>&1; then HOST_CPU_FAMILY="$(sysctl -n machdep.cpu.brand_string 2>/dev/null || true)"; else HOST_CPU_FAMILY=""; fi
if [[ -z "${HOST_CPU_FAMILY}" ]] && command -v lscpu >/dev/null 2>&1; then HOST_CPU_FAMILY="$(lscpu 2>/dev/null | sed -n 's/^Model name:[[:space:]]*//p' | head -n 1)"; fi
[[ -n "${HOST_CPU_FAMILY}" ]] || HOST_CPU_FAMILY="unknown-${HOST_ARCH}"

FINAL_STAGE="manifest-generation"
MANIFEST_ARGS=(
    collect --policy "${MANIFEST_POLICY}" --role probe --run-id "${RUN_ID}"
    --started-utc "${STARTED_UTC}" --ended-utc "${ENDED_UTC}" --result "${RESULT}"
    --host-os "${HOST_OS}" --host-architecture "${HOST_ARCH}" --host-cpu-family "${HOST_CPU_FAMILY}" --host-virtualization TCG
    --accelerator tcg --cpu-model "${CPU_PROFILE}" --ram-mib "${RAM_MIB}" --smp "${SMP}"
    --command-shape "qemu-system-aarch64 -accel tcg -cpu ${CPU_PROFILE} -M vmapple,uuid=<redacted> -m ${RAM} -smp ${SMP}"
    --firmware "${FIRMWARE}" --auxiliary-storage "${AUX}" --disk "${DISK}" --machine-identity "${MACHINE_IDENTITY}"
    --artifact "launcher_log=${LAUNCHER_LOG}" --artifact "serial_log=${SERIAL_LOG}"
    --artifact "qemu_debug_log=${QEMU_DEBUG_LOG}" --artifact "trace_capability_log=${TRACE_HELP_LOG}"
    --output "${OUTPUT_MANIFEST}"
)
while IFS= read -r event || [[ -n "${event}" ]]; do [[ -z "${event}" || "${event}" == \#* ]] && continue; MANIFEST_ARGS+=(--trace-event "${event}"); done < "${TRACE_CONFIG}"
IFS=',' read -r -a DEBUG_ARRAY <<< "${DEBUG_ITEMS}"
for item in "${DEBUG_ARRAY[@]}"; do [[ -n "${item}" ]] && MANIFEST_ARGS+=(--debug-item "${item}"); done
if [[ -n "${HARDWARE_MODEL}" ]]; then MANIFEST_ARGS+=(--hardware-model "${HARDWARE_MODEL}"); fi
python3 "${MANIFEST_TOOL}" "${MANIFEST_ARGS[@]}" || fail "PROBE_MANIFEST_FAILED" "Could not create P1.10 probe manifest."
python3 "${MANIFEST_TOOL}" validate "${OUTPUT_MANIFEST}" --policy "${MANIFEST_POLICY}" || fail "PROBE_MANIFEST_INVALID" "Generated probe manifest failed P1.09 validation."

CLASSIFICATION="P1_10_PROBE_MANIFEST_READY"
FINAL_STAGE="complete"
echo "AppleSilicon version: ${VERSION}"
echo "Probe runtime run ID: ${RUN_ID}"
echo "Probe source result: ${RESULT}"
echo "Probe manifest: ${OUTPUT_MANIFEST}"
echo "Re-collecting this launcher log preserves the same run ID and cannot manufacture an independent reproduction."

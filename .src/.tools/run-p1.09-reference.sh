#!/usr/bin/env bash

set -Eeuo pipefail

VERSION="0.9.0.0.0.0"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
LOG_DIR="${APPLESILICON_LOG_DIR:-${ROOT_DIR}/.logs}"
QEMU_BIN="${APPLESILICON_QEMU_BIN:-}"
ACCEL="hvf"
CPU_PROFILE="host"
SMP="${APPLESILICON_VMAPPLE_SMP:-4}"
RAM="${APPLESILICON_VMAPPLE_RAM:-4G}"
UUID_VALUE="${APPLESILICON_VMAPPLE_UUID:-}"
FIRMWARE="${APPLESILICON_VMAPPLE_FIRMWARE:-}"
AUX="${APPLESILICON_VMAPPLE_AUX:-}"
DISK="${APPLESILICON_VMAPPLE_DISK:-}"
MACHINE_IDENTITY="${APPLESILICON_VMAPPLE_MACHINE_IDENTITY:-}"
HARDWARE_MODEL="${APPLESILICON_VMAPPLE_HARDWARE_MODEL:-}"
MANIFEST_TOOL="${ROOT_DIR}/.src/.tools/reference-manifest.py"
MANIFEST_POLICY="${ROOT_DIR}/.src/.configs/p1.09-manifest-policy.json"
REFERENCE_SECONDS="${APPLESILICON_P1_09_REFERENCE_SECONDS:-30}"
GRACE_SECONDS="${APPLESILICON_P1_09_GRACE_SECONDS:-3}"
DEBUG_ITEMS="${APPLESILICON_P1_09_DEBUG_ITEMS:-guest_errors,unimp,int,cpu_reset}"
TRACE_CONFIG="${APPLESILICON_P1_09_TRACE_EVENTS:-${ROOT_DIR}/.src/.configs/p1.07-trace-events}"
CLASSIFICATION="UNCLASSIFIED"
FINAL_STAGE="startup"
QEMU_STATUS="not-started"
TIMED_OUT=0

mkdir -p "${LOG_DIR}"
TIMESTAMP="$(date -u +"%Y%m%d-%H%M%S")"
PREFIX="${LOG_DIR}/AppleSilicon-p1.09-reference-${TIMESTAMP}-$$"
LAUNCHER_LOG="${PREFIX}.log"
SERIAL_LOG="${PREFIX}-serial.log"
QEMU_DEBUG_LOG="${PREFIX}-qemu.log"
TRACE_HELP_LOG="${PREFIX}-trace-help.log"
FILTERED_TRACE_FILE="${PREFIX}-trace-events"
MANIFEST_FILE="${PREFIX}-manifest.json"
STARTED_UTC="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"

exec > >(tee "${LAUNCHER_LOG}") 2>&1

on_exit() {
    local status=$?
    trap - EXIT
    echo "Classification: ${CLASSIFICATION}"
    echo "Final stage: ${FINAL_STAGE}"
    echo "QEMU status: ${QEMU_STATUS}"
    echo "Timed out: ${TIMED_OUT}"
    echo "Harness exit code: ${status}"
    echo "Finished UTC: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
    echo "Launcher log: ${LAUNCHER_LOG}"
    echo "Serial log: ${SERIAL_LOG}"
    echo "QEMU debug log: ${QEMU_DEBUG_LOG}"
    echo "Trace capability log: ${TRACE_HELP_LOG}"
    echo "Reference manifest: ${MANIFEST_FILE}"
    exit "${status}"
}
trap on_exit EXIT

fail() {
    CLASSIFICATION="$1"
    shift
    printf '%s\n' "$@" >&2
    exit 1
}

hash_text() {
    if command -v shasum >/dev/null 2>&1; then
        printf '%s' "$1" | shasum -a 256 | awk '{print $1}'
    elif command -v sha256sum >/dev/null 2>&1; then
        printf '%s' "$1" | sha256sum | awk '{print $1}'
    else
        printf '%s' "unavailable"
    fi
}

file_size() {
    if stat -f '%z' "$1" >/dev/null 2>&1; then
        stat -f '%z' "$1"
    else
        stat -c '%s' "$1"
    fi
}

validate_file() {
    local classification="$1"
    local label="$2"
    local path="$3"
    [[ -n "${path}" ]] || fail "${classification}" "${label} path is not configured."
    [[ -f "${path}" ]] || fail "${classification}" "${label} does not exist: ${path}"
    [[ -r "${path}" ]] || fail "${classification}" "${label} is not readable: ${path}"
}

FINAL_STAGE="host-validation"
[[ "$(uname -s)" == "Darwin" ]] || fail "REFERENCE_HOST_UNSUPPORTED" "P1.09 reference capture requires macOS."
[[ "$(uname -m)" == "arm64" ]] || fail "REFERENCE_HOST_UNSUPPORTED" "P1.09 reference capture requires an Apple Silicon arm64 host."

FINAL_STAGE="configuration-validation"
[[ -n "${QEMU_BIN}" ]] || fail "QEMU_BINARY_MISSING" "APPLESILICON_QEMU_BIN is not configured."
[[ -x "${QEMU_BIN}" ]] || fail "QEMU_BINARY_MISSING" "QEMU binary is not executable: ${QEMU_BIN}"
[[ -n "${UUID_VALUE}" ]] || fail "INPUT_UUID_MISSING" "APPLESILICON_VMAPPLE_UUID is not configured."
validate_file "INPUT_FIRMWARE_MISSING" "VMApple firmware" "${FIRMWARE}"
validate_file "INPUT_AUX_MISSING" "VMApple aux image" "${AUX}"
validate_file "INPUT_DISK_MISSING" "VMApple disk image" "${DISK}"
validate_file "INPUT_IDENTITY_MISSING" "VMApple machine identity" "${MACHINE_IDENTITY}"
validate_file "MANIFEST_TOOL_MISSING" "P1.09 manifest tool" "${MANIFEST_TOOL}"
validate_file "MANIFEST_POLICY_MISSING" "P1.09 manifest policy" "${MANIFEST_POLICY}"
if [[ -n "${HARDWARE_MODEL}" ]]; then
    validate_file "INPUT_HARDWARE_MODEL_MISSING" "VMApple hardware model" "${HARDWARE_MODEL}"
fi
validate_file "TRACE_CAPABILITY_FAILED" "trace configuration" "${TRACE_CONFIG}"
[[ "${REFERENCE_SECONDS}" =~ ^[0-9]+$ ]] && (( REFERENCE_SECONDS > 0 )) || fail "LAUNCH_FAILED" "Reference duration must be a positive integer."
[[ "${GRACE_SECONDS}" =~ ^[0-9]+$ ]] || fail "LAUNCH_FAILED" "Grace duration must be a non-negative integer."

UUID_HASH="$(hash_text "${UUID_VALUE}")"
echo "AppleSilicon version: ${VERSION}"
echo "Started UTC: ${STARTED_UTC}"
echo "Host OS: $(uname -s)"
echo "Host architecture: $(uname -m)"
echo "Accelerator: ${ACCEL}"
echo "CPU profile: ${CPU_PROFILE}"
echo "SMP: ${SMP}"
echo "RAM: ${RAM}"
echo "Reference seconds: ${REFERENCE_SECONDS}"
echo "UUID SHA-256: ${UUID_HASH}"
echo "Firmware size: $(file_size "${FIRMWARE}") bytes"
echo "Aux size: $(file_size "${AUX}") bytes"
echo "Disk size: $(file_size "${DISK}") bytes"

FINAL_STAGE="qemu-capability-validation"
"${QEMU_BIN}" --version | head -n 1
"${QEMU_BIN}" -machine help 2>&1 | grep -Eq '(^|[[:space:]])vmapple([[:space:]]|$)' || fail "QEMU_VMAPPLE_MISSING" "Built QEMU does not advertise the vmapple machine."
"${QEMU_BIN}" -accel help 2>&1 | grep -Eq '(^|[[:space:]])hvf([[:space:]]|$)' || fail "QEMU_HVF_MISSING" "Built QEMU does not advertise HVF."

FINAL_STAGE="trace-capability-discovery"
set +e
"${QEMU_BIN}" -trace help > "${TRACE_HELP_LOG}" 2>&1
TRACE_HELP_STATUS=$?
set -e
[[ ${TRACE_HELP_STATUS} -eq 0 ]] || fail "TRACE_CAPABILITY_FAILED" "QEMU -trace help failed with status ${TRACE_HELP_STATUS}."

: > "${FILTERED_TRACE_FILE}"
while IFS= read -r event || [[ -n "${event}" ]]; do
    [[ -z "${event}" ]] && continue
    [[ "${event}" == \#* ]] && continue
    if grep -Fxq "${event}" "${TRACE_HELP_LOG}" || grep -Eq "(^|[[:space:]])${event}([[:space:]]|$)" "${TRACE_HELP_LOG}"; then
        printf '%s\n' "${event}" >> "${FILTERED_TRACE_FILE}"
    else
        fail "TRACE_CAPABILITY_FAILED" "Configured trace event is unavailable in this QEMU build: ${event}"
    fi
done < "${TRACE_CONFIG}"
[[ -s "${FILTERED_TRACE_FILE}" ]] || fail "TRACE_CAPABILITY_FAILED" "No configured trace events survived capability filtering."

echo "Enabled trace events:"
cat "${FILTERED_TRACE_FILE}"

FINAL_STAGE="qemu-launch"
QEMU_ARGS=(
    -no-user-config
    -display none
    -monitor none
    -serial stdio
    -no-reboot
    -m "${RAM}"
    -smp "${SMP}"
    -accel "${ACCEL}"
    -cpu "${CPU_PROFILE}"
    -M "vmapple,uuid=${UUID_VALUE}"
    -bios "${FIRMWARE}"
    -drive "file=${AUX},if=pflash,format=raw"
    -drive "file=${DISK},if=pflash,format=raw"
    -drive "file=${AUX},if=none,id=aux,format=raw"
    -drive "file=${DISK},if=none,id=root,format=raw"
    -device "vmapple-virtio-blk-pci,variant=aux,drive=aux"
    -device "vmapple-virtio-blk-pci,variant=root,drive=root"
    -d "${DEBUG_ITEMS}"
    -D "${QEMU_DEBUG_LOG}"
    -trace "events=${FILTERED_TRACE_FILE}"
)

echo "Launching controlled P1.09 HVF reference capture."
echo "Redacted shape: -accel hvf -cpu host -M vmapple,uuid=<redacted> -smp ${SMP} -m ${RAM}"

set +e
"${QEMU_BIN}" "${QEMU_ARGS[@]}" > >(tee "${SERIAL_LOG}") 2>&1 &
QEMU_PID=$!
set -e
DEADLINE=$((SECONDS + REFERENCE_SECONDS))

while kill -0 "${QEMU_PID}" 2>/dev/null; do
    if (( SECONDS >= DEADLINE )); then
        TIMED_OUT=1
        break
    fi
    sleep 1
done

if (( TIMED_OUT == 1 )); then
    FINAL_STAGE="reference-timeout"
    kill -TERM "${QEMU_PID}" 2>/dev/null || true
    GRACE_DEADLINE=$((SECONDS + GRACE_SECONDS))
    while kill -0 "${QEMU_PID}" 2>/dev/null && (( SECONDS < GRACE_DEADLINE )); do
        sleep 1
    done
    if kill -0 "${QEMU_PID}" 2>/dev/null; then
        kill -KILL "${QEMU_PID}" 2>/dev/null || true
    fi
fi

set +e
wait "${QEMU_PID}"
QEMU_EXIT=$?
set -e
QEMU_STATUS="${QEMU_EXIT}"

if (( TIMED_OUT == 1 )); then
    CLASSIFICATION="P1_09_REFERENCE_TIMED_OUT"
else
    CLASSIFICATION="P1_09_REFERENCE_EXITED"
fi

FINAL_STAGE="manifest-generation"
ENDED_UTC="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
HOST_CPU_FAMILY="$(sysctl -n machdep.cpu.brand_string 2>/dev/null || printf '%s' 'Apple Silicon')"
RAM_MIB="${RAM%G}"
if [[ "${RAM}" == *G ]]; then
    RAM_MIB=$((RAM_MIB * 1024))
elif [[ "${RAM}" == *M ]]; then
    RAM_MIB="${RAM%M}"
else
    fail "MANIFEST_GENERATION_FAILED" "P1.09 manifest generation requires RAM to use G or M units, observed: ${RAM}"
fi
MANIFEST_ARGS=(
    collect
    --policy "${MANIFEST_POLICY}"
    --role reference
    --run-id "p1.09-reference-${TIMESTAMP}-$$"
    --started-utc "${STARTED_UTC}"
    --ended-utc "${ENDED_UTC}"
    --result "${CLASSIFICATION}"
    --host-os macOS
    --host-architecture arm64
    --host-cpu-family "${HOST_CPU_FAMILY}"
    --host-virtualization HVF
    --accelerator hvf
    --cpu-model host
    --ram-mib "${RAM_MIB}"
    --smp "${SMP}"
    --command-shape "qemu-system-aarch64 -accel hvf -cpu host -M vmapple,uuid=<redacted> -m ${RAM} -smp ${SMP}"
    --firmware "${FIRMWARE}"
    --auxiliary-storage "${AUX}"
    --disk "${DISK}"
    --machine-identity "${MACHINE_IDENTITY}"
    --artifact "serial_log=${SERIAL_LOG}"
    --artifact "qemu_debug_log=${QEMU_DEBUG_LOG}"
    --artifact "trace_capability_log=${TRACE_HELP_LOG}"
    --output "${MANIFEST_FILE}"
)
if [[ -n "${HARDWARE_MODEL}" ]]; then
    MANIFEST_ARGS+=(--hardware-model "${HARDWARE_MODEL}")
fi
python3 "${MANIFEST_TOOL}" "${MANIFEST_ARGS[@]}" || fail "MANIFEST_GENERATION_FAILED" "P1.09 could not create the sanitized reference manifest."

FINAL_STAGE="complete"
echo "QEMU exit status: ${QEMU_EXIT}"
echo "Reference manifest: ${MANIFEST_FILE}"
echo "This run is reference evidence only. It does not establish a TCG divergence by itself."

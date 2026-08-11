#!/usr/bin/env bash

set -Eeuo pipefail

VERSION="0.7.0.0.0.0"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
LOG_DIR="${APPLESILICON_LOG_DIR:-${ROOT_DIR}/.logs}"
QEMU_BIN="${APPLESILICON_QEMU_BIN:-}"
ACCEL="${APPLESILICON_VMAPPLE_ACCEL:-tcg}"
CPU_PROFILE="${APPLESILICON_VMAPPLE_CPU_PROFILE:-max}"
SMP="${APPLESILICON_VMAPPLE_SMP:-4}"
RAM="${APPLESILICON_VMAPPLE_RAM:-4G}"
UUID_VALUE="${APPLESILICON_VMAPPLE_UUID:-}"
FIRMWARE="${APPLESILICON_VMAPPLE_FIRMWARE:-}"
AUX="${APPLESILICON_VMAPPLE_AUX:-}"
DISK="${APPLESILICON_VMAPPLE_DISK:-}"
PROBE_SECONDS="${APPLESILICON_P1_07_PROBE_SECONDS:-30}"
GRACE_SECONDS="${APPLESILICON_P1_07_GRACE_SECONDS:-3}"
DEBUG_ITEMS="${APPLESILICON_P1_07_DEBUG_ITEMS:-guest_errors,unimp,int,cpu_reset}"
TRACE_CONFIG="${APPLESILICON_P1_07_TRACE_EVENTS:-${ROOT_DIR}/.src/.configs/p1.07-trace-events}"
CLASSIFICATION="UNCLASSIFIED"
FINAL_STAGE="startup"
QEMU_STATUS="not-started"
TIMED_OUT=0

mkdir -p "${LOG_DIR}"
TIMESTAMP="$(date -u +"%Y%m%d-%H%M%S")"
PREFIX="${LOG_DIR}/AppleSilicon-p1.07-${TIMESTAMP}-$$"
LAUNCHER_LOG="${PREFIX}.log"
SERIAL_LOG="${PREFIX}-serial.log"
QEMU_DEBUG_LOG="${PREFIX}-qemu.log"
TRACE_HELP_LOG="${PREFIX}-trace-help.log"
FILTERED_TRACE_FILE="${PREFIX}-trace-events"

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
    if command -v sha256sum >/dev/null 2>&1; then
        printf '%s' "$1" | sha256sum | awk '{print $1}'
    elif command -v shasum >/dev/null 2>&1; then
        printf '%s' "$1" | shasum -a 256 | awk '{print $1}'
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

FINAL_STAGE="configuration-validation"
[[ "${ACCEL}" == "tcg" ]] || fail "QEMU_TCG_MISSING" "P1.07 requires APPLESILICON_VMAPPLE_ACCEL=tcg."
case "${CPU_PROFILE}" in
    max|apple-gxf) ;;
    *) fail "QEMU_CPU_PROFILE_MISSING" "P1.07 accepts max or apple-gxf." ;;
esac
[[ -n "${QEMU_BIN}" ]] || fail "QEMU_BINARY_MISSING" "APPLESILICON_QEMU_BIN is not configured."
[[ -x "${QEMU_BIN}" ]] || fail "QEMU_BINARY_MISSING" "QEMU binary is not executable: ${QEMU_BIN}"
[[ -n "${UUID_VALUE}" ]] || fail "INPUT_UUID_MISSING" "APPLESILICON_VMAPPLE_UUID is not configured."
validate_file "INPUT_FIRMWARE_MISSING" "VMApple firmware" "${FIRMWARE}"
validate_file "INPUT_AUX_MISSING" "VMApple aux image" "${AUX}"
validate_file "INPUT_DISK_MISSING" "VMApple disk image" "${DISK}"
validate_file "TRACE_CAPABILITY_FAILED" "P1.07 trace configuration" "${TRACE_CONFIG}"
[[ "${PROBE_SECONDS}" =~ ^[0-9]+$ ]] && (( PROBE_SECONDS > 0 )) || fail "LAUNCH_FAILED" "Probe duration must be a positive integer."
[[ "${GRACE_SECONDS}" =~ ^[0-9]+$ ]] || fail "LAUNCH_FAILED" "Grace duration must be a non-negative integer."

UUID_HASH="$(hash_text "${UUID_VALUE}")"
echo "AppleSilicon version: ${VERSION}"
echo "Started UTC: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
echo "Host OS: $(uname -s 2>/dev/null || echo unknown)"
echo "Host architecture: $(uname -m 2>/dev/null || echo unknown)"
echo "QEMU binary: ${QEMU_BIN}"
echo "Accelerator: ${ACCEL}"
echo "CPU profile: ${CPU_PROFILE}"
echo "SMP: ${SMP}"
echo "RAM: ${RAM}"
echo "Probe seconds: ${PROBE_SECONDS}"
echo "Grace seconds: ${GRACE_SECONDS}"
echo "Debug items: ${DEBUG_ITEMS}"
echo "UUID SHA-256: ${UUID_HASH}"
echo "Firmware size: $(file_size "${FIRMWARE}") bytes"
echo "Aux size: $(file_size "${AUX}") bytes"
echo "Disk size: $(file_size "${DISK}") bytes"

FINAL_STAGE="qemu-capability-validation"
"${QEMU_BIN}" --version | head -n 1
"${QEMU_BIN}" -machine help 2>&1 | grep -Eq '(^|[[:space:]])vmapple([[:space:]]|$)' || fail "QEMU_VMAPPLE_MISSING" "Built QEMU does not advertise the vmapple machine."
"${QEMU_BIN}" -accel help 2>&1 | grep -Eq '(^|[[:space:]])tcg([[:space:]]|$)' || fail "QEMU_TCG_MISSING" "Built QEMU does not advertise the TCG accelerator."
"${QEMU_BIN}" -cpu help 2>&1 | grep -Eq "(^|[[:space:]])${CPU_PROFILE}([[:space:]]|$)" || fail "QEMU_CPU_PROFILE_MISSING" "Built QEMU does not advertise CPU profile ${CPU_PROFILE}."

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

echo "Launching controlled P1.07 probe."
echo "Redacted shape: -accel ${ACCEL} -cpu ${CPU_PROFILE} -M vmapple,uuid=<redacted> -smp ${SMP} -m ${RAM}"

set +e
"${QEMU_BIN}" "${QEMU_ARGS[@]}" > >(tee "${SERIAL_LOG}") 2>&1 &
QEMU_PID=$!
set -e
START_SECONDS=${SECONDS}
DEADLINE=$((START_SECONDS + PROBE_SECONDS))

while kill -0 "${QEMU_PID}" 2>/dev/null; do
    if (( SECONDS >= DEADLINE )); then
        TIMED_OUT=1
        break
    fi
    sleep 1
done

if (( TIMED_OUT == 1 )); then
    FINAL_STAGE="probe-timeout"
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
    CLASSIFICATION="P1_07_PROBE_TIMED_OUT"
else
    CLASSIFICATION="P1_07_PROBE_EXITED"
fi

FINAL_STAGE="complete"
echo "QEMU exit status: ${QEMU_EXIT}"
echo "The result is observational only; no macOS boot-success claim is made."

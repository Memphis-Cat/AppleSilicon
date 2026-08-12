#!/usr/bin/env bash

set -Eeuo pipefail

VERSION="0.7.0.0.0.0"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
LOG_DIR="${APPLESILICON_LOG_DIR:-${ROOT_DIR}/.logs}"
INTEGRITY_TOOL="${ROOT_DIR}/.src/.tools/runtime_integrity.py"
QEMU_BIN="${APPLESILICON_QEMU_BIN:-}"
ACCEL="${APPLESILICON_VMAPPLE_ACCEL:-tcg}"
CPU_PROFILE="${APPLESILICON_VMAPPLE_CPU_PROFILE:-max}"
SMP="${APPLESILICON_VMAPPLE_SMP:-4}"
RAM="${APPLESILICON_VMAPPLE_RAM:-4G}"
UUID_VALUE="${APPLESILICON_VMAPPLE_UUID:-}"
MACHINE_IDENTITY="${APPLESILICON_VMAPPLE_MACHINE_IDENTITY:-}"
FIRMWARE="${APPLESILICON_VMAPPLE_FIRMWARE:-}"
AUX="${APPLESILICON_VMAPPLE_AUX:-}"
DISK="${APPLESILICON_VMAPPLE_DISK:-}"
PROBE_SECONDS="${APPLESILICON_P1_07_PROBE_SECONDS:-30}"
GRACE_SECONDS="${APPLESILICON_P1_07_GRACE_SECONDS:-3}"
DEBUG_ITEMS="${APPLESILICON_P1_07_DEBUG_ITEMS:-guest_errors,unimp,int,cpu_reset}"
QEMU_SEED="${APPLESILICON_P1_07_QEMU_SEED:-}"
TRACE_CONFIG="${APPLESILICON_P1_07_TRACE_EVENTS:-${ROOT_DIR}/.src/.configs/p1.07-trace-events}"
CLASSIFICATION="UNCLASSIFIED"
FINAL_STAGE="startup"
QEMU_STATUS="not-started"
TIMED_OUT=0
QEMU_PID=""

mkdir -p "${LOG_DIR}"
TIMESTAMP="$(date -u +"%Y%m%d-%H%M%S")"
RUN_ID="p1.07-probe-${TIMESTAMP}-$$"
PREFIX="${LOG_DIR}/AppleSilicon-p1.07-${TIMESTAMP}-$$"
LAUNCHER_LOG="${PREFIX}.log"
SERIAL_LOG="${PREFIX}-serial.log"
QEMU_DEBUG_LOG="${PREFIX}-qemu.log"
TRACE_HELP_LOG="${PREFIX}-trace-help.log"
FILTERED_TRACE_FILE="${PREFIX}-trace-events"

exec > >(tee "${LAUNCHER_LOG}") 2>&1

cleanup_qemu() {
    if [[ -n "${QEMU_PID}" ]] && kill -0 "${QEMU_PID}" 2>/dev/null; then
        kill -TERM "${QEMU_PID}" 2>/dev/null || true
        local deadline=$((SECONDS + GRACE_SECONDS))
        while kill -0 "${QEMU_PID}" 2>/dev/null && (( SECONDS < deadline )); do sleep 1; done
        if kill -0 "${QEMU_PID}" 2>/dev/null; then kill -KILL "${QEMU_PID}" 2>/dev/null || true; fi
        wait "${QEMU_PID}" 2>/dev/null || true
    fi
    QEMU_PID=""
}

on_signal() {
    CLASSIFICATION="P1_07_PROBE_INTERRUPTED"
    FINAL_STAGE="signal-cleanup"
    cleanup_qemu
    exit 130
}

on_exit() {
    local status=$?
    trap - EXIT INT TERM HUP
    cleanup_qemu
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
trap on_signal INT TERM HUP

fail() {
    CLASSIFICATION="$1"
    shift
    printf '%s\n' "$@" >&2
    exit 1
}

hash_text() {
    python3 - "$1" <<'PY'
import hashlib, sys
print(hashlib.sha256(sys.argv[1].encode("ascii")).hexdigest())
PY
}

file_size() {
    if stat -f '%z' "$1" >/dev/null 2>&1; then stat -f '%z' "$1"; else stat -c '%s' "$1"; fi
}

validate_file() {
    local classification="$1" label="$2" path="$3"
    [[ -n "${path}" ]] || fail "${classification}" "${label} path is not configured."
    [[ -f "${path}" && -r "${path}" ]] || fail "${classification}" "${label} is missing or unreadable: ${path}"
}

FINAL_STAGE="configuration-validation"
for command in python3 grep tee; do command -v "${command}" >/dev/null 2>&1 || fail "TOOL_MISSING" "Missing required command: ${command}"; done
[[ -f "${INTEGRITY_TOOL}" ]] || fail "RUNTIME_INTEGRITY_MISSING" "Runtime integrity helper is missing."
[[ "${ACCEL}" == "tcg" ]] || fail "QEMU_TCG_MISSING" "P1.07 requires APPLESILICON_VMAPPLE_ACCEL=tcg."
case "${CPU_PROFILE}" in max|apple-gxf) ;; *) fail "QEMU_CPU_PROFILE_MISSING" "P1.07 accepts max or apple-gxf." ;; esac
[[ "${SMP}" =~ ^[0-9]+$ ]] && (( SMP >= 1 && SMP <= 32 )) || fail "INVALID_SMP" "SMP must be an integer from 1 through 32."
[[ "${RAM}" =~ ^[1-9][0-9]*[GM]$ ]] || fail "INVALID_RAM" "RAM must be a positive integer followed by G or M (for example 4G or 4096M)."
[[ -n "${QEMU_BIN}" && -x "${QEMU_BIN}" ]] || fail "QEMU_BINARY_MISSING" "APPLESILICON_QEMU_BIN is missing or not executable."
[[ -n "${UUID_VALUE}" ]] || fail "INPUT_UUID_MISSING" "APPLESILICON_VMAPPLE_UUID (VMApple uint64 machine id) is not configured."
validate_file "INPUT_IDENTITY_MISSING" "compiled P3.02 machine identity" "${MACHINE_IDENTITY}"
validate_file "INPUT_FIRMWARE_MISSING" "VMApple firmware" "${FIRMWARE}"
validate_file "INPUT_AUX_MISSING" "VMApple aux image" "${AUX}"
validate_file "INPUT_DISK_MISSING" "VMApple disk image" "${DISK}"
validate_file "TRACE_CAPABILITY_FAILED" "P1.07 trace configuration" "${TRACE_CONFIG}"
[[ "${PROBE_SECONDS}" =~ ^[0-9]+$ ]] && (( PROBE_SECONDS > 0 )) || fail "LAUNCH_FAILED" "Probe duration must be a positive integer."
[[ "${GRACE_SECONDS}" =~ ^[0-9]+$ ]] || fail "LAUNCH_FAILED" "Grace duration must be a non-negative integer."
if [[ -n "${QEMU_SEED}" ]]; then
    [[ "${QEMU_SEED}" =~ ^(0[xX][0-9a-fA-F]+|[0-9]+)$ ]] ||
        fail "INVALID_QEMU_SEED" "QEMU seed must be decimal or 0x-prefixed hexadecimal."
fi

MACHINE_ID="$(python3 "${INTEGRITY_TOOL}" machine-id "${UUID_VALUE}")" || fail "INPUT_UUID_INVALID" "VMApple machine id must be uint64 decimal or 0x-prefixed."
python3 "${INTEGRITY_TOOL}" identity --compiled "${MACHINE_IDENTITY}" --machine-id "${MACHINE_ID}" >/dev/null ||
    fail "INPUT_IDENTITY_INVALID" "Compiled P3.02 identity failed runtime validation."
IDENTITY_ARGS=()
while IFS= read -r item; do IDENTITY_ARGS+=("${item}"); done < <(
    python3 "${INTEGRITY_TOOL}" identity --compiled "${MACHINE_IDENTITY}" --machine-id "${MACHINE_ID}" --emit-globals
)
(( ${#IDENTITY_ARGS[@]} >= 4 && ${#IDENTITY_ARGS[@]} % 2 == 0 )) || fail "INPUT_IDENTITY_INVALID" "Compiled identity emitted an invalid global argument set."

FIRMWARE_BYTES="$(file_size "${FIRMWARE}")"
(( FIRMWARE_BYTES > 0 && FIRMWARE_BYTES <= 1048576 )) || fail "INPUT_FIRMWARE_INVALID" "Firmware must be non-empty and fit VMApple's 1 MiB firmware window."
MACHINE_ID_HASH="$(hash_text "${MACHINE_ID}")"
echo "AppleSilicon version: ${VERSION}"
echo "Run ID: ${RUN_ID}"
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
if [[ -n "${QEMU_SEED}" ]]; then
    echo "QEMU deterministic seed: ${QEMU_SEED}"
fi
echo "Machine ID SHA-256: ${MACHINE_ID_HASH}"
echo "UUID SHA-256: ${MACHINE_ID_HASH}"
echo "Firmware size: ${FIRMWARE_BYTES} bytes"
echo "Aux size: $(file_size "${AUX}") bytes"
echo "Disk size: $(file_size "${DISK}") bytes"
echo "Identity globals: $(( ${#IDENTITY_ARGS[@]} / 2 ))"

FINAL_STAGE="qemu-capability-validation"
QEMU_VERSION_OUTPUT="$("${QEMU_BIN}" --version 2>&1)" || fail "QEMU_BINARY_MISSING" "QEMU --version failed."
printf '%s\n' "${QEMU_VERSION_OUTPUT%%$'\n'*}"
"${QEMU_BIN}" -machine help 2>&1 | grep -E '(^|[[:space:]])vmapple([[:space:]]|$)' >/dev/null || fail "QEMU_VMAPPLE_MISSING" "Built QEMU does not advertise vmapple."
"${QEMU_BIN}" -accel help 2>&1 | grep -E '(^|[[:space:]])tcg([[:space:]]|$)' >/dev/null || fail "QEMU_TCG_MISSING" "Built QEMU does not advertise TCG."
"${QEMU_BIN}" -cpu help 2>&1 | grep -E "(^|[[:space:]])${CPU_PROFILE}([[:space:]]|$)" >/dev/null || fail "QEMU_CPU_PROFILE_MISSING" "Built QEMU does not advertise CPU ${CPU_PROFILE}."

FINAL_STAGE="trace-capability-discovery"
set +e
"${QEMU_BIN}" -trace help > "${TRACE_HELP_LOG}" 2>&1
TRACE_HELP_STATUS=$?
set -e
[[ ${TRACE_HELP_STATUS} -eq 0 ]] || fail "TRACE_CAPABILITY_FAILED" "QEMU -trace help failed with status ${TRACE_HELP_STATUS}."
: > "${FILTERED_TRACE_FILE}"
while IFS= read -r event || [[ -n "${event}" ]]; do
    [[ -z "${event}" || "${event}" == \#* ]] && continue
    if grep -Fxq "${event}" "${TRACE_HELP_LOG}" || grep -Eq "(^|[[:space:]])${event}([[:space:]]|$)" "${TRACE_HELP_LOG}"; then
        printf '%s\n' "${event}" >> "${FILTERED_TRACE_FILE}"
    else
        fail "TRACE_CAPABILITY_FAILED" "Configured trace event is unavailable: ${event}"
    fi
done < "${TRACE_CONFIG}"
[[ -s "${FILTERED_TRACE_FILE}" ]] || fail "TRACE_CAPABILITY_FAILED" "No configured trace events survived filtering."
echo "Enabled trace events:"
cat "${FILTERED_TRACE_FILE}"

FINAL_STAGE="qemu-launch"
QEMU_ARGS=(
    -no-user-config -display none -monitor none -serial stdio -no-reboot
    -m "${RAM}" -smp "${SMP}" -accel "${ACCEL}" -cpu "${CPU_PROFILE}"
    -M "vmapple,uuid=${MACHINE_ID}"
)
if [[ -n "${QEMU_SEED}" ]]; then
    QEMU_ARGS+=(-seed "${QEMU_SEED}")
fi
QEMU_ARGS+=("${IDENTITY_ARGS[@]}")
QEMU_ARGS+=(
    -bios "${FIRMWARE}"
    -drive "file=${AUX},if=pflash,format=raw"
    -drive "file=${DISK},if=pflash,format=raw"
    -drive "file=${AUX},if=none,id=aux,format=raw"
    -drive "file=${DISK},if=none,id=root,format=raw"
    -device "vmapple-virtio-blk-pci,variant=aux,drive=aux"
    -device "vmapple-virtio-blk-pci,variant=root,drive=root"
    -d "${DEBUG_ITEMS}" -D "${QEMU_DEBUG_LOG}" -trace "events=${FILTERED_TRACE_FILE}"
)

echo "Launching controlled P1.07 probe."
echo "Redacted shape: -accel ${ACCEL} -cpu ${CPU_PROFILE} -M vmapple,uuid=<redacted> -smp ${SMP} -m ${RAM}"
set +e
"${QEMU_BIN}" "${QEMU_ARGS[@]}" > >(tee "${SERIAL_LOG}") 2>&1 &
QEMU_PID=$!
set -e
DEADLINE=$((SECONDS + PROBE_SECONDS))
while kill -0 "${QEMU_PID}" 2>/dev/null; do
    if (( SECONDS >= DEADLINE )); then TIMED_OUT=1; break; fi
    sleep 1
done

if (( TIMED_OUT == 1 )); then
    FINAL_STAGE="probe-timeout"
    kill -TERM "${QEMU_PID}" 2>/dev/null || true
    GRACE_DEADLINE=$((SECONDS + GRACE_SECONDS))
    while kill -0 "${QEMU_PID}" 2>/dev/null && (( SECONDS < GRACE_DEADLINE )); do sleep 1; done
    if kill -0 "${QEMU_PID}" 2>/dev/null; then kill -KILL "${QEMU_PID}" 2>/dev/null || true; fi
fi

set +e
wait "${QEMU_PID}"
QEMU_EXIT=$?
set -e
QEMU_PID=""
QEMU_STATUS="${QEMU_EXIT}"
if (( TIMED_OUT == 1 )); then CLASSIFICATION="P1_07_PROBE_TIMED_OUT"; else CLASSIFICATION="P1_07_PROBE_EXITED"; fi
FINAL_STAGE="complete"
echo "QEMU exit status: ${QEMU_EXIT}"
echo "The result is observational only; no macOS boot-success claim is made."

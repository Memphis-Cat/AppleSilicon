#!/usr/bin/env bash

set -Eeuo pipefail

VERSION="0.3.0.0.0.0"
EXPECTED_INFERNO_REVISION="cc4302a99167abec69b714cfd00c38caece7e7de"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SOURCE_DIR="${APPLESILICON_INFERNO_SOURCE:-${ROOT_DIR}/.src/.upstream/.inferno}"
QEMU_BIN="${APPLESILICON_QEMU_AARCH64:-${ROOT_DIR}/.build/inferno/qemu-system-aarch64}"
LOG_DIR="${APPLESILICON_LOG_DIR:-${ROOT_DIR}/.logs}"
MODE="binary"

if [[ ${1:-} == "--source-only" ]]; then
    MODE="source-only"
elif [[ $# -gt 0 ]]; then
    echo "Usage: $0 [--source-only]" >&2
    exit 64
fi

mkdir -p "${LOG_DIR}"
TIMESTAMP="$(date -u +"%Y%m%d-%H%M%S")"
LOG_FILE="${LOG_DIR}/AppleSilicon-probe-vmapple-${TIMESTAMP}-$$.log"
FINAL_STAGE="startup"
CLASSIFICATION="UNCLASSIFIED"

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

require_command() {
    local command_name="$1"
    if ! command -v "${command_name}" >/dev/null 2>&1; then
        echo "Missing required command: ${command_name}" >&2
        return 1
    fi
}

run_nonfatal() {
    local name="$1"
    shift
    FINAL_STAGE="${name}"
    echo "------------------------------------------------------------"
    echo "Stage: ${name}"
    printf 'Command:'
    printf ' %q' "$@"
    printf '\n'

    set +e
    "$@"
    local status=$?
    set -e

    echo "Stage exit code: ${status}"
    return "${status}"
}

capture_nonfatal() {
    local __result_var="$1"
    local name="$2"
    shift 2

    FINAL_STAGE="${name}"
    echo "------------------------------------------------------------"
    echo "Stage: ${name}"
    printf 'Command:'
    printf ' %q' "$@"
    printf '\n'

    local output
    local status
    set +e
    output="$("$@" 2>&1)"
    status=$?
    set -e

    printf '%s\n' "${output}"
    echo "Stage exit code: ${status}"
    printf -v "${__result_var}" '%s' "${output}"
    return "${status}"
}

source_has_line() {
    local file="$1"
    local pattern="$2"
    grep -Fq -- "${pattern}" "${file}"
}

echo "============================================================"
echo "AppleSilicon VMApple capability probe"
echo "============================================================"
echo "AppleSilicon version: ${VERSION}"
echo "Started UTC: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
echo "Mode: ${MODE}"
echo "Host OS: $(uname -s 2>/dev/null || echo unknown)"
echo "Host release: $(uname -r 2>/dev/null || echo unknown)"
echo "Host architecture: $(uname -m 2>/dev/null || echo unknown)"
echo "Project root: ${ROOT_DIR}"
echo "Inferno source: ${SOURCE_DIR}"
echo "QEMU AArch64 binary: ${QEMU_BIN}"
echo "Expected Inferno revision: ${EXPECTED_INFERNO_REVISION}"
echo "Log file: ${LOG_FILE}"

FINAL_STAGE="tool-preflight"
require_command git
require_command grep

if [[ ! -d "${SOURCE_DIR}" ]]; then
    echo "Inferno source directory does not exist: ${SOURCE_DIR}" >&2
    CLASSIFICATION="SOURCE_UNAVAILABLE"
    exit 1
fi

if ! git -C "${SOURCE_DIR}" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo "Inferno source path is not a Git work tree: ${SOURCE_DIR}" >&2
    CLASSIFICATION="SOURCE_INVALID"
    exit 1
fi

FINAL_STAGE="revision-validation"
OBSERVED_REVISION="$(git -C "${SOURCE_DIR}" rev-parse HEAD)"
echo "Observed Inferno revision: ${OBSERVED_REVISION}"

if [[ "${OBSERVED_REVISION}" != "${EXPECTED_INFERNO_REVISION}" ]]; then
    echo "Inferno revision mismatch." >&2
    echo "Expected: ${EXPECTED_INFERNO_REVISION}" >&2
    echo "Observed: ${OBSERVED_REVISION}" >&2
    CLASSIFICATION="SOURCE_REVISION_MISMATCH"
    exit 1
fi

KCONFIG_FILE="${SOURCE_DIR}/hw/vmapple/Kconfig"
VMAPPLE_FILE="${SOURCE_DIR}/hw/vmapple/vmapple.c"

if [[ ! -f "${KCONFIG_FILE}" || ! -f "${VMAPPLE_FILE}" ]]; then
    echo "Required VMApple source files are missing from the pinned source tree." >&2
    CLASSIFICATION="VMAPPLE_SOURCE_MISSING"
    exit 1
fi

FINAL_STAGE="source-gate-inspection"
VMAPPLE_ARM_GATE="no"
VMAPPLE_HVF_GATE="no"
VMAPPLE_HOST_CPU_DEFAULT="no"

if source_has_line "${KCONFIG_FILE}" "depends on ARM"; then
    VMAPPLE_ARM_GATE="yes"
fi

if source_has_line "${KCONFIG_FILE}" "depends on HVF"; then
    VMAPPLE_HVF_GATE="yes"
fi

if source_has_line "${VMAPPLE_FILE}" 'mc->default_cpu_type = ARM_CPU_TYPE_NAME("host");'; then
    VMAPPLE_HOST_CPU_DEFAULT="yes"
fi

echo "VMAPPLE ARM gate: ${VMAPPLE_ARM_GATE}"
echo "VMAPPLE HVF gate: ${VMAPPLE_HVF_GATE}"
echo "VMApple default CPU is host: ${VMAPPLE_HOST_CPU_DEFAULT}"

echo "Relevant Kconfig lines:"
grep -nE 'config VMAPPLE$|depends on ARM|depends on HVF|default y if ARM' "${KCONFIG_FILE}" || true

echo "Relevant VMApple CPU-default lines:"
grep -nF 'default_cpu_type' "${VMAPPLE_FILE}" || true

if [[ "${MODE}" == "source-only" ]]; then
    FINAL_STAGE="source-only-complete"
    CLASSIFICATION="SOURCE_ONLY"
    echo "P1.03 source-only inspection completed successfully."
    exit 0
fi

FINAL_STAGE="binary-preflight"
if [[ ! -x "${QEMU_BIN}" ]]; then
    echo "P1.02 qemu-system-aarch64 binary is unavailable or not executable." >&2
    echo "Expected path: ${QEMU_BIN}" >&2
    echo "Use --source-only when only source inspection is intended." >&2
    CLASSIFICATION="BINARY_UNAVAILABLE"
    exit 1
fi

QEMU_VERSION_OUTPUT=""
if ! capture_nonfatal QEMU_VERSION_OUTPUT "qemu-version" "${QEMU_BIN}" --version; then
    CLASSIFICATION="QEMU_VERSION_FAILED"
    exit 1
fi

MACHINE_HELP_OUTPUT=""
if ! capture_nonfatal MACHINE_HELP_OUTPUT "machine-inventory" "${QEMU_BIN}" -machine help; then
    CLASSIFICATION="MACHINE_INVENTORY_FAILED"
    exit 1
fi

VMAPPLE_PRESENT="no"
if printf '%s\n' "${MACHINE_HELP_OUTPUT}" | grep -Eq '(^|[[:space:]])vmapple([[:space:]]|$)'; then
    VMAPPLE_PRESENT="yes"
fi

echo "Detected vmapple machine: ${VMAPPLE_PRESENT}"

ACCEL_HELP_OUTPUT=""
if ! capture_nonfatal ACCEL_HELP_OUTPUT "accelerator-inventory" "${QEMU_BIN}" -accel help; then
    echo "Accelerator inventory command returned non-zero; output retained for classification."
fi

CPU_HELP_OUTPUT=""
if ! capture_nonfatal CPU_HELP_OUTPUT "cpu-inventory" "${QEMU_BIN}" -cpu help; then
    echo "CPU inventory command returned non-zero; output retained for classification."
fi

for accelerator in hvf kvm tcg; do
    if printf '%s\n' "${ACCEL_HELP_OUTPUT}" | grep -Eq "(^|[[:space:]])${accelerator}([[:space:]]|$)"; then
        echo "Accelerator ${accelerator}: present"
    else
        echo "Accelerator ${accelerator}: absent"
    fi
done

for cpu_model in host max; do
    if printf '%s\n' "${CPU_HELP_OUTPUT}" | grep -Eq "(^|[[:space:]])${cpu_model}([[:space:]]|$)"; then
        echo "CPU model ${cpu_model}: present"
    else
        echo "CPU model ${cpu_model}: absent"
    fi
done

if [[ "${VMAPPLE_PRESENT}" == "yes" ]]; then
    VMAPPLE_HELP_OUTPUT=""
    if capture_nonfatal VMAPPLE_HELP_OUTPUT "vmapple-property-inventory" "${QEMU_BIN}" -M vmapple,help; then
        echo "VMApple property query: success"
    else
        echo "VMApple property query: non-zero; output retained"
    fi

    FINAL_STAGE="classification"
    CLASSIFICATION="VMAPPLE_PRESENT"
    echo "P1.03 result: VMApple is compiled into this qemu-system-aarch64 binary."
    echo "This result does not claim that VMApple works under TCG/KVM or boots macOS."
    exit 0
fi

FINAL_STAGE="classification"
CLASSIFICATION="VMAPPLE_NOT_COMPILED"
echo "P1.03 result: qemu-system-aarch64 exists but does not list the vmapple machine."
echo "Source VMAPPLE HVF gate: ${VMAPPLE_HVF_GATE}"
echo "The current build-gate evidence is preserved for P1.04."
exit 0

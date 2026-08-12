#!/usr/bin/env bash

set -Eeuo pipefail

VERSION="0.6.0.0.0.0"
EXPECTED_INFERNO_REVISION="cc4302a99167abec69b714cfd00c38caece7e7de"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SOURCE_DIR="${APPLESILICON_INFERNO_SOURCE:-${ROOT_DIR}/.src/.upstream/.inferno}"
PATCH_0001="${APPLESILICON_P1_04_PATCH:-${ROOT_DIR}/.src/.patches/0001-vmapple-decouple-build-from-hvf.patch}"
PATCH_0002="${APPLESILICON_P1_05_PATCH:-${ROOT_DIR}/.src/.patches/0002-vmapple-optional-apple-pvg.patch}"
WORK_ROOT="${APPLESILICON_P1_06_WORK_ROOT:-${ROOT_DIR}/.build/p1.06}"
PREPARED_SOURCE="${WORK_ROOT}/inferno-src"
PROFILE_FILE="${WORK_ROOT}/vmapple-cpu-profile.env"
LOG_DIR="${APPLESILICON_LOG_DIR:-${ROOT_DIR}/.logs}"
ACCEL="${APPLESILICON_VMAPPLE_ACCEL:-tcg}"
CPU_PROFILE="${APPLESILICON_VMAPPLE_CPU_PROFILE:-max}"
SMP="${APPLESILICON_VMAPPLE_SMP:-4}"
MODE="prepare"
CLASSIFICATION="UNCLASSIFIED"
FINAL_STAGE="startup"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --check-only)
            MODE="check-only"
            shift
            ;;
        --profile)
            if [[ $# -lt 2 ]]; then
                echo "--profile requires max or apple-gxf" >&2
                exit 64
            fi
            CPU_PROFILE="$2"
            shift 2
            ;;
        *)
            echo "Usage: $0 [--check-only] [--profile max|apple-gxf]" >&2
            exit 64
            ;;
    esac
done

mkdir -p "${LOG_DIR}"
TIMESTAMP="$(date -u +"%Y%m%d-%H%M%S")"
LOG_FILE="${LOG_DIR}/AppleSilicon-p1.06-${TIMESTAMP}-$$.log"

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
    local name="$1"
    if ! command -v "${name}" >/dev/null 2>&1; then
        echo "Missing required command: ${name}" >&2
        return 1
    fi
}

fail_classified() {
    CLASSIFICATION="$1"
    shift
    printf '%s\n' "$@" >&2
    exit 1
}

safe_reset_work_root() {
    local normalized_root normalized_build_root
    normalized_root="$(python3 - "${WORK_ROOT}" <<'PY'
from pathlib import Path
import sys
print(Path(sys.argv[1]).resolve(strict=False))
PY
)" || return 1
    normalized_build_root="$(python3 - "${ROOT_DIR}/.build" <<'PY'
from pathlib import Path
import sys
print(Path(sys.argv[1]).resolve(strict=False))
PY
)" || return 1
    case "${normalized_root}" in
        ""|"/"|"${ROOT_DIR}"|"${HOME}"|"${normalized_build_root}")
            echo "Refusing unsafe P1.06 work-root reset: ${WORK_ROOT}" >&2
            return 1
            ;;
    esac
    if [[ "${normalized_root}" != "${normalized_build_root}/"* ]]; then
        echo "Refusing P1.06 work root outside ${normalized_build_root}: ${WORK_ROOT}" >&2
        return 1
    fi
    WORK_ROOT="${normalized_root}"
    PREPARED_SOURCE="${WORK_ROOT}/inferno-src"
    PROFILE_FILE="${WORK_ROOT}/vmapple-cpu-profile.env"
    rm -rf -- "${WORK_ROOT}"
    mkdir -p "${WORK_ROOT}"
}

validate_profile() {
    if [[ "${ACCEL}" != "tcg" ]]; then
        fail_classified "NON_TCG_ACCELERATOR_FORBIDDEN" \
            "P1.06 is specifically the non-host TCG CPU-selection objective." \
            "Requested accelerator: ${ACCEL}"
    fi

    if [[ "${CPU_PROFILE}" == "host" ]]; then
        fail_classified "HOST_PROFILE_FORBIDDEN" \
            "The host CPU is the reference path and is intentionally forbidden in the P1.06 non-host profile."
    fi

    case "${CPU_PROFILE}" in
        max|apple-gxf)
            ;;
        *)
            fail_classified "CPU_PROFILE_UNSUPPORTED" \
                "Unsupported P1.06 CPU profile: ${CPU_PROFILE}" \
                "Accepted profiles: max, apple-gxf"
            ;;
    esac

    if ! [[ "${SMP}" =~ ^[0-9]+$ ]] || (( SMP < 1 || SMP > 32 )); then
        fail_classified "INVALID_SMP" \
            "APPLESILICON_VMAPPLE_SMP must be an integer from 1 through 32." \
            "Observed value: ${SMP}"
    fi
}

echo "============================================================"
echo "AppleSilicon P1.06 CPU-selection preparation"
echo "============================================================"
echo "AppleSilicon version: ${VERSION}"
echo "Started UTC: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
echo "Mode: ${MODE}"
echo "Host OS: $(uname -s 2>/dev/null || echo unknown)"
echo "Host architecture: $(uname -m 2>/dev/null || echo unknown)"
echo "Project root: ${ROOT_DIR}"
echo "Inferno source: ${SOURCE_DIR}"
echo "Expected Inferno revision: ${EXPECTED_INFERNO_REVISION}"
echo "Requested accelerator: ${ACCEL}"
echo "Requested CPU profile: ${CPU_PROFILE}"
echo "Requested SMP: ${SMP}"
echo "Prepared source: ${PREPARED_SOURCE}"
echo "Profile output: ${PROFILE_FILE}"
echo "Log file: ${LOG_FILE}"

FINAL_STAGE="tool-preflight"
require_command git
require_command grep
require_command python3
validate_profile

FINAL_STAGE="source-validation"
if [[ ! -d "${SOURCE_DIR}" ]]; then
    fail_classified "SOURCE_UNAVAILABLE" "Inferno source directory does not exist: ${SOURCE_DIR}"
fi

if ! git -C "${SOURCE_DIR}" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    fail_classified "SOURCE_INVALID" "Inferno source path is not a Git work tree: ${SOURCE_DIR}"
fi

OBSERVED_REVISION="$(git -C "${SOURCE_DIR}" rev-parse HEAD)"
echo "Observed Inferno revision: ${OBSERVED_REVISION}"

if [[ "${OBSERVED_REVISION}" != "${EXPECTED_INFERNO_REVISION}" ]]; then
    fail_classified "SOURCE_REVISION_MISMATCH" \
        "Expected Inferno revision: ${EXPECTED_INFERNO_REVISION}" \
        "Observed Inferno revision: ${OBSERVED_REVISION}"
fi

DIRTY_STATUS="$(git -C "${SOURCE_DIR}" status --porcelain --untracked-files=no)"
if [[ -n "${DIRTY_STATUS}" ]]; then
    CLASSIFICATION="SOURCE_DIRTY"
    echo "Pinned Inferno source contains tracked modifications:" >&2
    printf '%s\n' "${DIRTY_STATUS}" >&2
    exit 1
fi

for patch in "${PATCH_0001}" "${PATCH_0002}"; do
    if [[ ! -f "${patch}" ]]; then
        fail_classified "PATCH_MISSING" "Required patch does not exist: ${patch}"
    fi
done

VMAPPLE_SOURCE="${SOURCE_DIR}/hw/vmapple/vmapple.c"
VL_SOURCE="${SOURCE_DIR}/system/vl.c"
CPU64_SOURCE="${SOURCE_DIR}/target/arm/cpu64.c"

for source_file in "${VMAPPLE_SOURCE}" "${VL_SOURCE}" "${CPU64_SOURCE}"; do
    if [[ ! -f "${source_file}" ]]; then
        fail_classified "SOURCE_CONTRACT_FILE_MISSING" "Required source file is missing: ${source_file}"
    fi
done

FINAL_STAGE="cpu-contract-validation"
if ! grep -Fq 'mc->default_cpu_type = ARM_CPU_TYPE_NAME("host");' "${VMAPPLE_SOURCE}"; then
    fail_classified "HOST_DEFAULT_MISSING" "VMApple no longer contains the expected host reference default."
fi

if ! grep -Fq 'ms->possible_cpus->cpus[n].type = ms->cpu_type;' "${VMAPPLE_SOURCE}"; then
    fail_classified "VMAPPLE_CPU_TYPE_PATH_MISSING" \
        "VMApple no longer builds possible CPUs from MachineState::cpu_type."
fi

if ! grep -Fq 'current_machine->cpu_type = parse_cpu_option(cpu_option);' "${VL_SOURCE}"; then
    fail_classified "CPU_OVERRIDE_PATH_MISSING" \
        "The QEMU startup path no longer overrides the machine CPU type from -cpu as expected."
fi

if ! grep -Fq '{ .name = "max",' "${CPU64_SOURCE}"; then
    fail_classified "MAX_CPU_MODEL_MISSING" "Pinned Inferno no longer defines the max AArch64 CPU model."
fi

if ! grep -Fq '{ .name = "apple-gxf",' "${CPU64_SOURCE}"; then
    fail_classified "APPLE_GXF_CPU_MODEL_MISSING" "Pinned Inferno no longer defines the apple-gxf AArch64 CPU model."
fi

if ! grep -Fq 'static void aarch64_apple_gxf_initfn(Object *obj)' "${CPU64_SOURCE}"; then
    fail_classified "APPLE_GXF_CPU_MODEL_MISSING" "apple-gxf initialization code is missing."
fi

echo "CPU selection source contract: present"
echo "VMApple reference default: host"
echo "P1.06 control CPU: max"
echo "P1.06 experimental CPU: apple-gxf"

FINAL_STAGE="patch-check-0001"
set +e
git -C "${SOURCE_DIR}" apply --check "${PATCH_0001}"
PATCH_STATUS=$?
set -e
if [[ ${PATCH_STATUS} -ne 0 ]]; then
    fail_classified "PATCH_0001_CHECK_FAILED" "P1.04 patch does not apply cleanly to the pinned Inferno revision."
fi

FINAL_STAGE="patch-check-0002"
set +e
git -C "${SOURCE_DIR}" apply --check "${PATCH_0002}"
PATCH_STATUS=$?
set -e
if [[ ${PATCH_STATUS} -ne 0 ]]; then
    fail_classified "PATCH_0002_CHECK_FAILED" "P1.05 patch does not apply cleanly to the pinned Inferno revision."
fi

if [[ "${MODE}" == "check-only" ]]; then
    CLASSIFICATION="P1_06_CHECKS_PASS"
    FINAL_STAGE="check-only-complete"
    echo "P1.06 source and CPU-profile checks completed successfully."
    echo "No source tree was prepared and no guest was launched."
    exit 0
fi

FINAL_STAGE="work-root-reset"
safe_reset_work_root

FINAL_STAGE="source-clone"
git clone --quiet --no-hardlinks "${SOURCE_DIR}" "${PREPARED_SOURCE}"
git -C "${PREPARED_SOURCE}" checkout --quiet --detach "${EXPECTED_INFERNO_REVISION}"

FINAL_STAGE="nested-submodules"
git -C "${PREPARED_SOURCE}" submodule update --init --recursive

FINAL_STAGE="patch-apply-0001"
set +e
git -C "${PREPARED_SOURCE}" apply "${PATCH_0001}"
PATCH_STATUS=$?
set -e
if [[ ${PATCH_STATUS} -ne 0 ]]; then
    fail_classified "PATCH_0001_APPLY_FAILED" "P1.04 patch failed in the P1.06 disposable source tree."
fi

FINAL_STAGE="patch-apply-0002"
set +e
git -C "${PREPARED_SOURCE}" apply "${PATCH_0002}"
PATCH_STATUS=$?
set -e
if [[ ${PATCH_STATUS} -ne 0 ]]; then
    fail_classified "PATCH_0002_APPLY_FAILED" "P1.05 patch failed in the P1.06 disposable source tree."
fi

PATCHED_KCONFIG="${PREPARED_SOURCE}/hw/vmapple/Kconfig"
PATCHED_VMAPPLE="${PREPARED_SOURCE}/hw/vmapple/vmapple.c"
PATCHED_VL="${PREPARED_SOURCE}/system/vl.c"
PATCHED_CPU64="${PREPARED_SOURCE}/target/arm/cpu64.c"

FINAL_STAGE="post-patch-validation"
VALIDATION_FAILED=0

if grep -Fq 'depends on HVF' "${PATCHED_KCONFIG}"; then
    echo "Validation failure: P1.04 HVF build gate returned." >&2
    VALIDATION_FAILED=1
fi

if ! grep -Fq 'depends on AARCH64' "${PATCHED_KCONFIG}"; then
    echo "Validation failure: P1.04 AARCH64 gate is missing." >&2
    VALIDATION_FAILED=1
fi

if ! grep -Fq 'qdev_try_new("apple-gfx-mmio")' "${PATCHED_VMAPPLE}"; then
    echo "Validation failure: P1.05 optional Apple PVG path is missing." >&2
    VALIDATION_FAILED=1
fi

if grep -Fq 'qdev_new("apple-gfx-mmio")' "${PATCHED_VMAPPLE}"; then
    echo "Validation failure: unconditional Apple PVG construction returned." >&2
    VALIDATION_FAILED=1
fi

if ! grep -Fq 'mc->default_cpu_type = ARM_CPU_TYPE_NAME("host");' "${PATCHED_VMAPPLE}"; then
    echo "Validation failure: VMApple host reference default changed." >&2
    VALIDATION_FAILED=1
fi

if ! grep -Fq 'ms->possible_cpus->cpus[n].type = ms->cpu_type;' "${PATCHED_VMAPPLE}"; then
    echo "Validation failure: VMApple no longer consumes MachineState::cpu_type." >&2
    VALIDATION_FAILED=1
fi

if ! grep -Fq 'current_machine->cpu_type = parse_cpu_option(cpu_option);' "${PATCHED_VL}"; then
    echo "Validation failure: QEMU -cpu override path is missing." >&2
    VALIDATION_FAILED=1
fi

if ! grep -Fq '{ .name = "max",' "${PATCHED_CPU64}"; then
    echo "Validation failure: max CPU model is missing." >&2
    VALIDATION_FAILED=1
fi

if ! grep -Fq '{ .name = "apple-gxf",' "${PATCHED_CPU64}"; then
    echo "Validation failure: apple-gxf CPU model is missing." >&2
    VALIDATION_FAILED=1
fi

if [[ ${VALIDATION_FAILED} -ne 0 ]]; then
    fail_classified "POST_PATCH_VALIDATION_FAILED" "Prepared source did not satisfy the P1.06 contract."
fi

FINAL_STAGE="profile-emission"
cat > "${PROFILE_FILE}" <<EOF
APPLESILICON_VERSION=${VERSION}
APPLESILICON_INFERNO_REVISION=${EXPECTED_INFERNO_REVISION}
APPLESILICON_VMAPPLE_ACCEL=${ACCEL}
APPLESILICON_VMAPPLE_CPU_PROFILE=${CPU_PROFILE}
APPLESILICON_VMAPPLE_MACHINE=vmapple
APPLESILICON_VMAPPLE_SMP=${SMP}
APPLESILICON_VMAPPLE_QEMU_ARGS="-accel ${ACCEL} -cpu ${CPU_PROFILE} -M vmapple -smp ${SMP}"
EOF

cat "${PROFILE_FILE}"

echo "------------------------------------------------------------"
echo "Selected non-host argument fragment:"
echo "-accel ${ACCEL} -cpu ${CPU_PROFILE} -M vmapple -smp ${SMP}"
echo "This is not a complete guest boot command."

echo "------------------------------------------------------------"
echo "Tracked P1.04/P1.05 source delta:"
git -C "${PREPARED_SOURCE}" diff --check
git -C "${PREPARED_SOURCE}" diff -- hw/vmapple/Kconfig hw/vmapple/vmapple.c

CLASSIFICATION="P1_06_PREPARED"
FINAL_STAGE="p1.06-complete"
echo "P1.06 explicit non-host VMApple CPU-selection preparation completed."
echo "Prepared source: ${PREPARED_SOURCE}"
echo "Selected CPU profile: ${CPU_PROFILE}"
echo "No QEMU guest was launched and no macOS compatibility result is claimed."

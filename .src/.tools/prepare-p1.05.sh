#!/usr/bin/env bash

set -Eeuo pipefail

VERSION="0.5.0.0.0.0"
EXPECTED_INFERNO_REVISION="cc4302a99167abec69b714cfd00c38caece7e7de"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SOURCE_DIR="${APPLESILICON_INFERNO_SOURCE:-${ROOT_DIR}/.src/.upstream/.inferno}"
PATCH_0001="${APPLESILICON_P1_04_PATCH:-${ROOT_DIR}/.src/.patches/0001-vmapple-decouple-build-from-hvf.patch}"
PATCH_0002="${APPLESILICON_P1_05_PATCH:-${ROOT_DIR}/.src/.patches/0002-vmapple-optional-apple-pvg.patch}"
WORK_ROOT="${APPLESILICON_P1_05_WORK_ROOT:-${ROOT_DIR}/.build/p1.05}"
PREPARED_SOURCE="${WORK_ROOT}/inferno-src"
LOG_DIR="${APPLESILICON_LOG_DIR:-${ROOT_DIR}/.logs}"
CLASSIFICATION="UNCLASSIFIED"
FINAL_STAGE="startup"

if [[ $# -gt 0 ]]; then
    echo "Usage: $0" >&2
    exit 64
fi

mkdir -p "${LOG_DIR}"
TIMESTAMP="$(date -u +"%Y%m%d-%H%M%S")"
LOG_FILE="${LOG_DIR}/AppleSilicon-p1.05-${TIMESTAMP}-$$.log"

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
            echo "Refusing unsafe P1.05 work-root reset: ${WORK_ROOT}" >&2
            return 1
            ;;
    esac
    if [[ "${normalized_root}" != "${normalized_build_root}/"* ]]; then
        echo "Refusing P1.05 work root outside ${normalized_build_root}: ${WORK_ROOT}" >&2
        return 1
    fi
    WORK_ROOT="${normalized_root}"
    PREPARED_SOURCE="${WORK_ROOT}/inferno-src"
    rm -rf -- "${WORK_ROOT}"
    mkdir -p "${WORK_ROOT}"
}

check_patch() {
    local classification="$1"
    local patch_file="$2"

    set +e
    git -C "${PREPARED_SOURCE}" apply --check "${patch_file}"
    local status=$?
    set -e

    if [[ ${status} -ne 0 ]]; then
        fail_classified "${classification}" "Patch does not apply cleanly: ${patch_file}"
    fi
}

apply_patch() {
    local classification="$1"
    local patch_file="$2"

    set +e
    git -C "${PREPARED_SOURCE}" apply "${patch_file}"
    local status=$?
    set -e

    if [[ ${status} -ne 0 ]]; then
        fail_classified "${classification}" "Patch failed to apply: ${patch_file}"
    fi
}

echo "============================================================"
echo "AppleSilicon P1.05 preparation"
echo "============================================================"
echo "AppleSilicon version: ${VERSION}"
echo "Started UTC: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
echo "Host OS: $(uname -s 2>/dev/null || echo unknown)"
echo "Host architecture: $(uname -m 2>/dev/null || echo unknown)"
echo "Project root: ${ROOT_DIR}"
echo "Inferno source: ${SOURCE_DIR}"
echo "P1.04 patch: ${PATCH_0001}"
echo "P1.05 patch: ${PATCH_0002}"
echo "Prepared source: ${PREPARED_SOURCE}"
echo "Expected Inferno revision: ${EXPECTED_INFERNO_REVISION}"
echo "Log file: ${LOG_FILE}"

FINAL_STAGE="tool-preflight"
require_command git
require_command grep
require_command python3

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

if [[ ! -f "${PATCH_0001}" ]]; then
    fail_classified "PATCH_0001_MISSING" "P1.04 patch is missing: ${PATCH_0001}"
fi

if [[ ! -f "${PATCH_0002}" ]]; then
    fail_classified "PATCH_0002_MISSING" "P1.05 patch is missing: ${PATCH_0002}"
fi

FINAL_STAGE="work-root-reset"
safe_reset_work_root

FINAL_STAGE="source-clone"
git clone --quiet --no-hardlinks "${SOURCE_DIR}" "${PREPARED_SOURCE}"
git -C "${PREPARED_SOURCE}" checkout --quiet --detach "${EXPECTED_INFERNO_REVISION}"

FINAL_STAGE="nested-submodules"
git -C "${PREPARED_SOURCE}" submodule update --init --recursive

FINAL_STAGE="patch-0001-check"
check_patch "PATCH_0001_CHECK_FAILED" "${PATCH_0001}"

FINAL_STAGE="patch-0001-apply"
apply_patch "PATCH_0001_APPLY_FAILED" "${PATCH_0001}"

FINAL_STAGE="patch-0002-check"
check_patch "PATCH_0002_CHECK_FAILED" "${PATCH_0002}"

FINAL_STAGE="patch-0002-apply"
apply_patch "PATCH_0002_APPLY_FAILED" "${PATCH_0002}"

KCONFIG_FILE="${PREPARED_SOURCE}/hw/vmapple/Kconfig"
VMAPPLE_FILE="${PREPARED_SOURCE}/hw/vmapple/vmapple.c"
QDEV_FILE="${PREPARED_SOURCE}/hw/core/qdev.c"

FINAL_STAGE="post-patch-validation"
VALIDATION_FAILED=0

if grep -Fq 'depends on HVF' "${KCONFIG_FILE}"; then
    echo "Validation failure: VMAPPLE still depends on HVF." >&2
    VALIDATION_FAILED=1
fi

if ! grep -Fq 'depends on AARCH64' "${KCONFIG_FILE}"; then
    echo "Validation failure: VMAPPLE is missing the P1.04 AARCH64 gate." >&2
    VALIDATION_FAILED=1
fi

if grep -Fq '#include "system/hvf.h"' "${VMAPPLE_FILE}"; then
    echo "Validation failure: vmapple.c still includes system/hvf.h." >&2
    VALIDATION_FAILED=1
fi

if ! grep -Fq 'qdev_try_new("apple-gfx-mmio")' "${VMAPPLE_FILE}"; then
    echo "Validation failure: VMApple does not use qdev_try_new for Apple PVG." >&2
    VALIDATION_FAILED=1
fi

if grep -Fq 'qdev_new("apple-gfx-mmio")' "${VMAPPLE_FILE}"; then
    echo "Validation failure: unconditional apple-gfx-mmio qdev_new remains." >&2
    VALIDATION_FAILED=1
fi

if ! grep -Fq 'VMApple: apple-gfx-mmio unavailable; continuing without Apple PVG' "${VMAPPLE_FILE}"; then
    echo "Validation failure: missing explicit no-PVG diagnostic." >&2
    VALIDATION_FAILED=1
fi

if ! grep -Fq 'sysbus_mmio_map(gfx, 0, vms->memmap[VMAPPLE_APV_GFX].base);' "${VMAPPLE_FILE}"; then
    echo "Validation failure: existing PVG GFX MMIO mapping was not preserved." >&2
    VALIDATION_FAILED=1
fi

if ! grep -Fq 'sysbus_mmio_map(gfx, 1, vms->memmap[VMAPPLE_APV_IOSFC].base);' "${VMAPPLE_FILE}"; then
    echo "Validation failure: existing PVG IOSFC MMIO mapping was not preserved." >&2
    VALIDATION_FAILED=1
fi

if ! grep -Fq 'sysbus_connect_irq(gfx, 0, qdev_get_gpio_in(vms->gic, irq_gfx));' "${VMAPPLE_FILE}"; then
    echo "Validation failure: existing PVG graphics IRQ wiring was not preserved." >&2
    VALIDATION_FAILED=1
fi

if ! grep -Fq 'sysbus_connect_irq(gfx, 1, qdev_get_gpio_in(vms->gic, irq_iosfc));' "${VMAPPLE_FILE}"; then
    echo "Validation failure: existing PVG IOSFC IRQ wiring was not preserved." >&2
    VALIDATION_FAILED=1
fi

if ! grep -Fq 'create_gfx(vms, sysmem);' "${VMAPPLE_FILE}"; then
    echo "Validation failure: VMApple no longer invokes create_gfx()." >&2
    VALIDATION_FAILED=1
fi

if ! grep -Fq 'mc->default_cpu_type = ARM_CPU_TYPE_NAME("host");' "${VMAPPLE_FILE}"; then
    echo "Validation failure: P1.05 unexpectedly changed the VMApple CPU default." >&2
    VALIDATION_FAILED=1
fi

if ! grep -Fq 'DeviceState *qdev_try_new(const char *name)' "${QDEV_FILE}"; then
    echo "Validation failure: pinned QEMU core does not expose the expected qdev_try_new primitive." >&2
    VALIDATION_FAILED=1
fi

if [[ ${VALIDATION_FAILED} -ne 0 ]]; then
    fail_classified "POST_PATCH_VALIDATION_FAILED" "Prepared source did not satisfy the P1.05 contract."
fi

echo "Relevant VMApple graphics creation lines:"
grep -nE 'create_gfx|qdev_try_new\("apple-gfx-mmio"\)|apple-gfx-mmio unavailable|sysbus_mmio_map\(gfx|sysbus_connect_irq\(gfx' "${VMAPPLE_FILE}" || true

echo "Relevant VMApple build-gate lines:"
grep -nE 'config VMAPPLE$|depends on ARM|depends on AARCH64|depends on HVF' "${KCONFIG_FILE}" || true

echo "VMApple CPU default after P1.05:"
grep -nF 'default_cpu_type' "${VMAPPLE_FILE}" || true

echo "Tracked patch delta:"
git -C "${PREPARED_SOURCE}" diff --check
git -C "${PREPARED_SOURCE}" diff -- hw/vmapple/Kconfig hw/vmapple/vmapple.c

CLASSIFICATION="P1_05_PREPARED"
FINAL_STAGE="p1.05-complete"
echo "P1.05 prepared source tree successfully."
echo "Prepared source: ${PREPARED_SOURCE}"
echo "Apple PVG remains enabled when apple-gfx-mmio exists and is skipped when absent."
echo "No guest was launched and no graphics, CPU, or macOS runtime compatibility is claimed."

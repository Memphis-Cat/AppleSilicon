#!/usr/bin/env bash

set -Eeuo pipefail

VERSION="0.4.0.0.0.0"
EXPECTED_INFERNO_REVISION="cc4302a99167abec69b714cfd00c38caece7e7de"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SOURCE_DIR="${APPLESILICON_INFERNO_SOURCE:-${ROOT_DIR}/.src/.upstream/.inferno}"
PATCH_FILE="${APPLESILICON_P1_04_PATCH:-${ROOT_DIR}/.src/.patches/0001-vmapple-decouple-build-from-hvf.patch}"
WORK_ROOT="${APPLESILICON_P1_04_WORK_ROOT:-${ROOT_DIR}/.build/p1.04}"
PREPARED_SOURCE="${WORK_ROOT}/inferno-src"
LOG_DIR="${APPLESILICON_LOG_DIR:-${ROOT_DIR}/.logs}"
MODE="prepare"
CLASSIFICATION="UNCLASSIFIED"
FINAL_STAGE="startup"

if [[ ${1:-} == "--check-only" ]]; then
    MODE="check-only"
elif [[ $# -gt 0 ]]; then
    echo "Usage: $0 [--check-only]" >&2
    exit 64
fi

mkdir -p "${LOG_DIR}"
TIMESTAMP="$(date -u +"%Y%m%d-%H%M%S")"
LOG_FILE="${LOG_DIR}/AppleSilicon-p1.04-${TIMESTAMP}-$$.log"

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
            echo "Refusing unsafe P1.04 work-root reset: ${WORK_ROOT}" >&2
            return 1
            ;;
    esac
    if [[ "${normalized_root}" != "${normalized_build_root}/"* ]]; then
        echo "Refusing P1.04 work root outside ${normalized_build_root}: ${WORK_ROOT}" >&2
        return 1
    fi
    WORK_ROOT="${normalized_root}"
    PREPARED_SOURCE="${WORK_ROOT}/inferno-src"
    rm -rf -- "${WORK_ROOT}"
    mkdir -p "${WORK_ROOT}"
}

fail_classified() {
    CLASSIFICATION="$1"
    shift
    printf '%s\n' "$@" >&2
    exit 1
}

echo "============================================================"
echo "AppleSilicon P1.04 preparation"
echo "============================================================"
echo "AppleSilicon version: ${VERSION}"
echo "Started UTC: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
echo "Mode: ${MODE}"
echo "Host OS: $(uname -s 2>/dev/null || echo unknown)"
echo "Host architecture: $(uname -m 2>/dev/null || echo unknown)"
echo "Project root: ${ROOT_DIR}"
echo "Inferno source: ${SOURCE_DIR}"
echo "Patch: ${PATCH_FILE}"
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

if [[ ! -f "${PATCH_FILE}" ]]; then
    fail_classified "PATCH_MISSING" "P1.04 patch does not exist: ${PATCH_FILE}"
fi

FINAL_STAGE="patch-check"
set +e
git -C "${SOURCE_DIR}" apply --check "${PATCH_FILE}"
PATCH_CHECK_STATUS=$?
set -e

if [[ ${PATCH_CHECK_STATUS} -ne 0 ]]; then
    fail_classified "PATCH_CHECK_FAILED" "P1.04 patch does not apply cleanly to the pinned Inferno revision."
fi

echo "Patch check: clean"

if [[ "${MODE}" == "check-only" ]]; then
    CLASSIFICATION="P1_04_PATCH_APPLIES"
    FINAL_STAGE="check-only-complete"
    echo "P1.04 patch applies cleanly to the pinned source."
    exit 0
fi

FINAL_STAGE="work-root-reset"
safe_reset_work_root

FINAL_STAGE="source-clone"
git clone --quiet --no-hardlinks "${SOURCE_DIR}" "${PREPARED_SOURCE}"
git -C "${PREPARED_SOURCE}" checkout --quiet --detach "${EXPECTED_INFERNO_REVISION}"

FINAL_STAGE="nested-submodules"
git -C "${PREPARED_SOURCE}" submodule update --init --recursive

FINAL_STAGE="patch-apply"
set +e
git -C "${PREPARED_SOURCE}" apply "${PATCH_FILE}"
PATCH_APPLY_STATUS=$?
set -e

if [[ ${PATCH_APPLY_STATUS} -ne 0 ]]; then
    fail_classified "PATCH_APPLY_FAILED" "P1.04 patch failed while preparing the disposable source tree."
fi

KCONFIG_FILE="${PREPARED_SOURCE}/hw/vmapple/Kconfig"
VMAPPLE_FILE="${PREPARED_SOURCE}/hw/vmapple/vmapple.c"

FINAL_STAGE="post-patch-validation"
VALIDATION_FAILED=0

if grep -Fq 'depends on HVF' "${KCONFIG_FILE}"; then
    echo "Validation failure: VMAPPLE still depends on HVF." >&2
    VALIDATION_FAILED=1
fi

if ! grep -Fq 'depends on ARM' "${KCONFIG_FILE}"; then
    echo "Validation failure: VMAPPLE lost its ARM-family gate." >&2
    VALIDATION_FAILED=1
fi

if ! grep -Fq 'depends on AARCH64' "${KCONFIG_FILE}"; then
    echo "Validation failure: VMAPPLE is missing the explicit AARCH64 gate." >&2
    VALIDATION_FAILED=1
fi

if grep -Fq '#include "system/hvf.h"' "${VMAPPLE_FILE}"; then
    echo "Validation failure: vmapple.c still includes system/hvf.h." >&2
    VALIDATION_FAILED=1
fi

if ! grep -Fq 'mc->default_cpu_type = ARM_CPU_TYPE_NAME("host");' "${VMAPPLE_FILE}"; then
    echo "Validation failure: P1.04 unexpectedly changed the VMApple CPU default." >&2
    VALIDATION_FAILED=1
fi

if [[ ${VALIDATION_FAILED} -ne 0 ]]; then
    fail_classified "POST_PATCH_VALIDATION_FAILED" "Prepared source did not satisfy the P1.04 contract."
fi

echo "Relevant patched Kconfig lines:"
grep -nE 'config VMAPPLE$|depends on ARM|depends on AARCH64|depends on HVF|default y if ARM' "${KCONFIG_FILE}" || true

echo "VMApple CPU default after patch:"
grep -nF 'default_cpu_type' "${VMAPPLE_FILE}" || true

echo "Tracked patch delta:"
git -C "${PREPARED_SOURCE}" diff --check
git -C "${PREPARED_SOURCE}" diff -- hw/vmapple/Kconfig hw/vmapple/vmapple.c

CLASSIFICATION="P1_04_PREPARED"
FINAL_STAGE="p1.04-complete"
echo "P1.04 prepared source tree successfully."
echo "Prepared source: ${PREPARED_SOURCE}"
echo "No guest was launched and no runtime compatibility is claimed."

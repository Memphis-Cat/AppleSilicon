#!/usr/bin/env bash

set -Eeuo pipefail

VERSION="0.7.0.0.0.0"
EXPECTED_INFERNO_REVISION="cc4302a99167abec69b714cfd00c38caece7e7de"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SOURCE_DIR="${APPLESILICON_INFERNO_SOURCE:-${ROOT_DIR}/.src/.upstream/.inferno}"
PATCH_0001="${ROOT_DIR}/.src/.patches/0001-vmapple-decouple-build-from-hvf.patch"
PATCH_0002="${ROOT_DIR}/.src/.patches/0002-vmapple-optional-apple-pvg.patch"
TRACE_SOURCE="${ROOT_DIR}/.src/.configs/p1.07-trace-events"
WORK_ROOT="${APPLESILICON_P1_07_WORK_ROOT:-${ROOT_DIR}/.build/.p1.07}"
PREPARED_SOURCE="${WORK_ROOT}/.inferno-src"
MANIFEST="${WORK_ROOT}/probe-manifest.env"
TRACE_COPY="${WORK_ROOT}/trace-events"
LOG_DIR="${APPLESILICON_LOG_DIR:-${ROOT_DIR}/.logs}"
CPU_PROFILE="${APPLESILICON_VMAPPLE_CPU_PROFILE:-max}"
SMP="${APPLESILICON_VMAPPLE_SMP:-4}"
RAM="${APPLESILICON_VMAPPLE_RAM:-4G}"
CLASSIFICATION="UNCLASSIFIED"
FINAL_STAGE="startup"

mkdir -p "${LOG_DIR}"
TIMESTAMP="$(date -u +"%Y%m%d-%H%M%S")"
LOG_FILE="${LOG_DIR}/AppleSilicon-p1.07-prepare-${TIMESTAMP}-$$.log"
exec > >(tee "${LOG_FILE}") 2>&1

on_exit() {
    local status=$?
    trap - EXIT
    echo "Classification: ${CLASSIFICATION}"
    echo "Final stage: ${FINAL_STAGE}"
    echo "Exit code: ${status}"
    echo "Finished UTC: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
    echo "Log file: ${LOG_FILE}"
    exit "${status}"
}
trap on_exit EXIT

fail() {
    CLASSIFICATION="$1"
    shift
    printf '%s\n' "$@" >&2
    exit 1
}

for cmd in git grep cp mkdir rm tee python3; do
    command -v "${cmd}" >/dev/null 2>&1 || fail "TOOL_MISSING" "Missing required command: ${cmd}"
done

case "${CPU_PROFILE}" in
    max|apple-gxf) ;;
    *) fail "CPU_PROFILE_UNSUPPORTED" "Accepted profiles: max, apple-gxf" ;;
esac

if ! [[ "${SMP}" =~ ^[0-9]+$ ]] || (( SMP < 1 || SMP > 32 )); then
    fail "INVALID_SMP" "SMP must be an integer from 1 through 32."
fi

FINAL_STAGE="source-validation"
[[ -d "${SOURCE_DIR}" ]] || fail "SOURCE_UNAVAILABLE" "Inferno source is unavailable: ${SOURCE_DIR}"
OBSERVED_REVISION="$(git -C "${SOURCE_DIR}" rev-parse HEAD 2>/dev/null || true)"
[[ "${OBSERVED_REVISION}" == "${EXPECTED_INFERNO_REVISION}" ]] || fail "SOURCE_REVISION_MISMATCH" "Expected ${EXPECTED_INFERNO_REVISION}; observed ${OBSERVED_REVISION:-unknown}"
[[ -z "$(git -C "${SOURCE_DIR}" status --porcelain --untracked-files=no)" ]] || fail "SOURCE_DIRTY" "Pinned Inferno has tracked modifications."
[[ -f "${PATCH_0001}" && -f "${PATCH_0002}" ]] || fail "PATCH_MISSING" "Required P1.04/P1.05 patch is missing."
[[ -f "${TRACE_SOURCE}" ]] || fail "TRACE_CONFIG_MISSING" "Trace event configuration is missing."

grep -Fq 'mc->default_cpu_type = ARM_CPU_TYPE_NAME("host");' "${SOURCE_DIR}/hw/vmapple/vmapple.c" || fail "HOST_REFERENCE_MISSING" "VMApple host reference default changed."
grep -Fq 'ms->possible_cpus->cpus[n].type = ms->cpu_type;' "${SOURCE_DIR}/hw/vmapple/vmapple.c" || fail "CPU_SELECTION_PATH_MISSING" "VMApple CPU selection path changed."
grep -Fq 'current_machine->cpu_type = parse_cpu_option(cpu_option);' "${SOURCE_DIR}/system/vl.c" || fail "CPU_OVERRIDE_PATH_MISSING" "QEMU -cpu override path changed."
grep -Fq '{ .name = "max",' "${SOURCE_DIR}/target/arm/cpu64.c" || fail "MAX_CPU_MISSING" "max CPU model missing."
grep -Fq '{ .name = "apple-gxf",' "${SOURCE_DIR}/target/arm/cpu64.c" || fail "APPLE_GXF_CPU_MISSING" "apple-gxf CPU model missing."

FINAL_STAGE="patch-validation"
git -C "${SOURCE_DIR}" apply --check "${PATCH_0001}" || fail "PATCH_0001_CHECK_FAILED" "P1.04 patch does not apply cleanly."
git -C "${SOURCE_DIR}" apply --check "${PATCH_0002}" || fail "PATCH_0002_CHECK_FAILED" "P1.05 patch does not apply cleanly."

FINAL_STAGE="work-root-reset"
NORMALIZED_BUILD_ROOT="$(python3 - "${ROOT_DIR}/.build" <<'PY'
from pathlib import Path
import sys
print(Path(sys.argv[1]).resolve(strict=False))
PY
)" || fail "UNSAFE_WORK_ROOT" "Could not canonicalize project build root."
NORMALIZED_WORK_ROOT="$(python3 - "${WORK_ROOT}" <<'PY'
from pathlib import Path
import sys
print(Path(sys.argv[1]).resolve(strict=False))
PY
)" || fail "UNSAFE_WORK_ROOT" "Could not canonicalize work root."
case "${NORMALIZED_WORK_ROOT}" in
    ""|"/"|"${HOME}"|"${ROOT_DIR}"|"${NORMALIZED_BUILD_ROOT}") fail "UNSAFE_WORK_ROOT" "Unsafe work root: ${WORK_ROOT}" ;;
esac
[[ "${NORMALIZED_WORK_ROOT}" == "${NORMALIZED_BUILD_ROOT}/"* ]] || fail "UNSAFE_WORK_ROOT" "Work root must remain under ${NORMALIZED_BUILD_ROOT}/."
WORK_ROOT="${NORMALIZED_WORK_ROOT}"
PREPARED_SOURCE="${WORK_ROOT}/.inferno-src"
MANIFEST="${WORK_ROOT}/probe-manifest.env"
TRACE_COPY="${WORK_ROOT}/trace-events"
rm -rf -- "${WORK_ROOT}"
mkdir -p "${WORK_ROOT}"

FINAL_STAGE="source-preparation"
git clone --quiet --no-hardlinks "${SOURCE_DIR}" "${PREPARED_SOURCE}"
git -C "${PREPARED_SOURCE}" checkout --quiet --detach "${EXPECTED_INFERNO_REVISION}"
git -C "${PREPARED_SOURCE}" submodule update --init --recursive
git -C "${PREPARED_SOURCE}" apply "${PATCH_0001}"
git -C "${PREPARED_SOURCE}" apply "${PATCH_0002}"

PATCHED_VMAPPLE="${PREPARED_SOURCE}/hw/vmapple/vmapple.c"
PATCHED_KCONFIG="${PREPARED_SOURCE}/hw/vmapple/Kconfig"
grep -Fq 'depends on AARCH64' "${PATCHED_KCONFIG}" || fail "POST_PATCH_VALIDATION_FAILED" "AARCH64 VMApple gate missing."
if grep -Fq 'depends on HVF' "${PATCHED_KCONFIG}"; then
    fail "POST_PATCH_VALIDATION_FAILED" "HVF VMApple build gate returned."
fi
grep -Fq 'qdev_try_new("apple-gfx-mmio")' "${PATCHED_VMAPPLE}" || fail "POST_PATCH_VALIDATION_FAILED" "Optional Apple PVG path missing."
grep -Fq 'mc->default_cpu_type = ARM_CPU_TYPE_NAME("host");' "${PATCHED_VMAPPLE}" || fail "POST_PATCH_VALIDATION_FAILED" "Reference CPU default changed."
git -C "${PREPARED_SOURCE}" diff --check

FINAL_STAGE="manifest-emission"
cp "${TRACE_SOURCE}" "${TRACE_COPY}"
cat > "${MANIFEST}" <<EOF
APPLESILICON_VERSION=${VERSION}
APPLESILICON_INFERNO_REVISION=${EXPECTED_INFERNO_REVISION}
APPLESILICON_VMAPPLE_ACCEL=tcg
APPLESILICON_VMAPPLE_CPU_PROFILE=${CPU_PROFILE}
APPLESILICON_VMAPPLE_SMP=${SMP}
APPLESILICON_VMAPPLE_RAM=${RAM}
APPLESILICON_P1_07_PREPARED_SOURCE=${PREPARED_SOURCE}
APPLESILICON_P1_07_TRACE_EVENTS=${TRACE_COPY}
APPLESILICON_P1_07_RUNTIME_LAUNCHER=${ROOT_DIR}/.src/.tools/run-p1.07-probe.sh
EOF

cat "${MANIFEST}"
echo "Runtime shape: -accel tcg -cpu ${CPU_PROFILE} -M vmapple -smp ${SMP} -m ${RAM}"
echo "No guest was launched."

CLASSIFICATION="P1_07_PREPARED"
FINAL_STAGE="complete"

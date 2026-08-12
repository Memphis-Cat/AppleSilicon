#!/usr/bin/env bash
set -Eeuo pipefail

VERSION="3.2.0.0.0.0"
EXPECTED_INFERNO_REVISION="cc4302a99167abec69b714cfd00c38caece7e7de"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SOURCE_DIR="${APPLESILICON_INFERNO_SOURCE:-${ROOT_DIR}/.src/.upstream/.inferno}"
CONTRACT="${ROOT_DIR}/.src/.configs/p3.03-io-contract.json"
TOOL="${ROOT_DIR}/.src/.tools/platform-io-contract.py"
WORK_ROOT="${APPLESILICON_P3_03_WORK_ROOT:-${ROOT_DIR}/.build/p3.03}"
SUMMARY_A="${WORK_ROOT}/platform-io-summary-a.json"
SUMMARY_B="${WORK_ROOT}/platform-io-summary-b.json"
LOG_DIR="${APPLESILICON_LOG_DIR:-${ROOT_DIR}/.logs}"
CLASSIFICATION="UNCLASSIFIED"
FINAL_STAGE="startup"

mkdir -p "${LOG_DIR}"
TIMESTAMP="$(date -u +"%Y%m%d-%H%M%S")"
LOG_FILE="${LOG_DIR}/AppleSilicon-p3.03-${TIMESTAMP}-$$.log"
exec > >(tee "${LOG_FILE}") 2>&1

on_exit() {
    local status=$?
    trap - EXIT
    echo "Classification: ${CLASSIFICATION}"
    echo "Final stage: ${FINAL_STAGE}"
    echo "Exit code: ${status}"
    echo "Finished UTC: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
    echo "Log: ${LOG_FILE}"
    exit "${status}"
}
trap on_exit EXIT

fail() {
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
)" || fail "P3_03_UNSAFE_WORK_ROOT" "Could not canonicalize P3.03 work root: ${WORK_ROOT}"
    normalized_build_root="$(python3 - "${ROOT_DIR}/.build" <<'PY'
from pathlib import Path
import sys
print(Path(sys.argv[1]).resolve(strict=False))
PY
)" || fail "P3_03_UNSAFE_WORK_ROOT" "Could not canonicalize project build root"
    case "${normalized_root}" in
        ""|"/"|"${ROOT_DIR}"|"${HOME}"|"${normalized_build_root}")
            fail "P3_03_UNSAFE_WORK_ROOT" "Refusing unsafe work-root reset: ${WORK_ROOT}"
            ;;
    esac
    [[ "${normalized_root}" == "${normalized_build_root}/"* ]] ||
        fail "P3_03_UNSAFE_WORK_ROOT" "Work root must remain below ${normalized_build_root}"
    WORK_ROOT="${normalized_root}"
    SUMMARY_A="${WORK_ROOT}/platform-io-summary-a.json"
    SUMMARY_B="${WORK_ROOT}/platform-io-summary-b.json"
    rm -rf -- "${WORK_ROOT}"
    mkdir -p "${WORK_ROOT}"
}

echo "AppleSilicon version: ${VERSION}"
echo "Objective: P3.03"
echo "Started UTC: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
echo "Inferno source: ${SOURCE_DIR}"

FINAL_STAGE="tool-preflight"
for command in git python3 cmp grep; do
    command -v "${command}" >/dev/null 2>&1 ||
        fail "P3_03_TOOL_MISSING" "Missing required command: ${command}"
done
for path in "${CONTRACT}" "${TOOL}"; do
    [[ -f "${path}" ]] || fail "P3_03_INPUT_MISSING" "Missing P3.03 input: ${path}"
done

FINAL_STAGE="syntax"
python3 - "${TOOL}" <<'PY'
from pathlib import Path
import sys
path = Path(sys.argv[1])
compile(path.read_text(encoding="utf-8"), str(path), "exec")
print("Python syntax: PASS")
PY
python3 -m json.tool "${CONTRACT}" >/dev/null
echo "JSON syntax: PASS"

FINAL_STAGE="contract-validation"
python3 "${TOOL}" --contract "${CONTRACT}" validate
python3 "${TOOL}" --contract "${CONTRACT}" self-check

FINAL_STAGE="source-validation"
[[ -d "${SOURCE_DIR}" ]] || fail "SOURCE_UNAVAILABLE" "Inferno source directory does not exist"
git -C "${SOURCE_DIR}" rev-parse --is-inside-work-tree >/dev/null 2>&1 ||
    fail "SOURCE_INVALID" "Inferno source is not a Git work tree"
OBSERVED_REVISION="$(git -C "${SOURCE_DIR}" rev-parse HEAD)"
[[ "${OBSERVED_REVISION}" == "${EXPECTED_INFERNO_REVISION}" ]] ||
    fail "SOURCE_REVISION_MISMATCH" "Expected ${EXPECTED_INFERNO_REVISION}; observed ${OBSERVED_REVISION}"
[[ -z "$(git -C "${SOURCE_DIR}" status --porcelain --untracked-files=no)" ]] ||
    fail "SOURCE_DIRTY" "Pinned Inferno source contains tracked modifications"

VMAPPLE="${SOURCE_DIR}/hw/vmapple/vmapple.c"
OBSERVED_BLOB="$(git -C "${SOURCE_DIR}" hash-object "hw/vmapple/vmapple.c")"
[[ "${OBSERVED_BLOB}" == "89c04c09f705d987ee96c11c1f5f4fc79713bf2e" ]] ||
    fail "P3_03_SOURCE_BLOB_DRIFT" "VMApple source blob drifted: ${OBSERVED_BLOB}"
echo "source lock: PASS: hw/vmapple/vmapple.c ${OBSERVED_BLOB}"

FINAL_STAGE="source-contract"
python3 "${TOOL}" --contract "${CONTRACT}" verify-source --source "${VMAPPLE}"

grep -Fq 'mc->max_cpus = 32;' "${VMAPPLE}" ||
    fail "P3_03_MAX_CPU_DRIFT" "VMApple max CPU count drifted"
grep -Fq 'qdev_prop_set_uint32(vms->gic, "num-cpu", smp_cpus);' "${VMAPPLE}" ||
    fail "P3_03_GIC_CPU_COUNT_DRIFT" "GIC num-cpu no longer follows VMApple SMP count"
grep -Fq 'vms->memmap[VMAPPLE_GIC_REDIST].size / GICV3_REDIST_SIZE' "${VMAPPLE}" ||
    fail "P3_03_GIC_REDIST_GEOMETRY_DRIFT" "GIC redistributor capacity calculation drifted"
grep -Fq 'qemu_set_irq(qdev_get_gpio_in(gpio_key_dev, 0), 1);' "${VMAPPLE}" ||
    fail "P3_03_POWER_REQUEST_DRIFT" "VMApple powerdown request path drifted"

echo "Pinned source wiring contract: PASS"
echo "Power-button event semantics remain runtime-evidence gated."

FINAL_STAGE="deterministic-summary"
safe_reset_work_root
python3 "${TOOL}" --contract "${CONTRACT}" summary > "${SUMMARY_A}"
python3 "${TOOL}" --contract "${CONTRACT}" summary > "${SUMMARY_B}"
cmp -s "${SUMMARY_A}" "${SUMMARY_B}" ||
    fail "P3_03_NONDETERMINISTIC_SUMMARY" "P3.03 summary differs across identical runs"

python3 - "${SUMMARY_A}" <<'PY'
import json
from pathlib import Path
import sys
data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
if data.get("classification") != "P3_03_SUMMARY":
    raise SystemExit("summary classification mismatch")
if data.get("gic_max_cpus") != 32:
    raise SystemExit("GIC CPU capacity mismatch")
if data.get("virtual_timer_ppi") != 27:
    raise SystemExit("virtual timer PPI mismatch")
if data.get("runtime_executed") is not False:
    raise SystemExit("P3.03 preparation must remain non-guest")
print("Deterministic summary: PASS")
print("Contract fingerprint:", data["fingerprint"])
PY

echo "No QEMU/macOS/HVF/TCG guest was launched."
echo "No generic device was replaced or reimplemented."
CLASSIFICATION="P3_03_PREPARATION_PASS"
FINAL_STAGE="complete"
echo "P3.03 interrupt/timer/power/console preparation: PASS"

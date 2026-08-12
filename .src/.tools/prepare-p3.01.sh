#!/usr/bin/env bash
set -Eeuo pipefail

VERSION="3.0.0.0.0.0"
EXPECTED_INFERNO_REVISION="cc4302a99167abec69b714cfd00c38caece7e7de"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SOURCE_DIR="${APPLESILICON_INFERNO_SOURCE:-${ROOT_DIR}/.src/.upstream/.inferno}"
CONTRACT="${ROOT_DIR}/.src/.configs/p3.01-platform-contract.json"
TOOL="${ROOT_DIR}/.src/.tools/platform-contract.py"
WORK_ROOT="${APPLESILICON_P3_01_WORK_ROOT:-${ROOT_DIR}/.build/p3.01}"
SUMMARY_FILE="${WORK_ROOT}/platform-contract-summary.json"
LOG_DIR="${APPLESILICON_LOG_DIR:-${ROOT_DIR}/.logs}"
CLASSIFICATION="UNCLASSIFIED"
FINAL_STAGE="startup"

mkdir -p "${LOG_DIR}"
TIMESTAMP="$(date -u +"%Y%m%d-%H%M%S")"
LOG_FILE="${LOG_DIR}/AppleSilicon-p3.01-${TIMESTAMP}-$$.log"
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
)" || fail "P3_01_UNSAFE_WORK_ROOT" "Could not canonicalize P3.01 work root: ${WORK_ROOT}"
    normalized_build_root="$(python3 - "${ROOT_DIR}/.build" <<'PY'
from pathlib import Path
import sys
print(Path(sys.argv[1]).resolve(strict=False))
PY
)" || fail "P3_01_UNSAFE_WORK_ROOT" "Could not canonicalize project build root"
    case "${normalized_root}" in
        ""|"/"|"${ROOT_DIR}"|"${HOME}"|"${normalized_build_root}")
            fail "P3_01_UNSAFE_WORK_ROOT" "Refusing unsafe work-root reset: ${WORK_ROOT}"
            ;;
    esac
    [[ "${normalized_root}" == "${normalized_build_root}/"* ]] ||
        fail "P3_01_UNSAFE_WORK_ROOT" "Work root must remain below ${normalized_build_root}"
    WORK_ROOT="${normalized_root}"
    SUMMARY_FILE="${WORK_ROOT}/platform-contract-summary.json"
    rm -rf -- "${WORK_ROOT}"
    mkdir -p "${WORK_ROOT}"
}

echo "AppleSilicon version: ${VERSION}"
echo "Objective: P3.01"
echo "Started UTC: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
echo "Inferno source: ${SOURCE_DIR}"
echo "Expected Inferno revision: ${EXPECTED_INFERNO_REVISION}"

FINAL_STAGE="tool-preflight"
for command in git python3; do
    command -v "${command}" >/dev/null 2>&1 ||
        fail "P3_01_TOOL_MISSING" "Missing required command: ${command}"
done
[[ -f "${CONTRACT}" ]] || fail "P3_01_CONTRACT_MISSING" "Missing contract: ${CONTRACT}"
[[ -f "${TOOL}" ]] || fail "P3_01_TOOL_MISSING" "Missing validator: ${TOOL}"

FINAL_STAGE="python-syntax"
python3 - "${TOOL}" <<'PY'
from pathlib import Path
import sys
path = Path(sys.argv[1])
compile(path.read_text(encoding="utf-8"), str(path), "exec")
print("Python syntax: PASS")
PY

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

FINAL_STAGE="source-lock-validation"
python3 - "${CONTRACT}" "${SOURCE_DIR}" <<'PY'
import json
import pathlib
import subprocess
import sys

contract = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
source = pathlib.Path(sys.argv[2])
locks = contract["source_locks"]["inferno"]["files"]
for rel, expected in locks.items():
    path = source / rel
    if not path.is_file():
        raise SystemExit(f"locked source file missing: {rel}")
    observed = subprocess.check_output(
        ["git", "-C", str(source), "hash-object", rel],
        text=True,
    ).strip()
    if observed != expected:
        raise SystemExit(f"source blob drift: {rel}: expected {expected}, observed {observed}")
    print(f"source lock: PASS: {rel} {observed}")
PY

FINAL_STAGE="platform-source-invariants"
grep -Fq 'select ARM_GICV3' "${SOURCE_DIR}/hw/vmapple/Kconfig" ||
    fail "P3_01_GENERIC_GIC_MISSING" "VMApple no longer selects ARM_GICV3"
grep -Fq 'select PL011' "${SOURCE_DIR}/hw/vmapple/Kconfig" ||
    fail "P3_01_GENERIC_UART_MISSING" "VMApple no longer selects PL011"
grep -Fq 'select PL031' "${SOURCE_DIR}/hw/vmapple/Kconfig" ||
    fail "P3_01_GENERIC_RTC_MISSING" "VMApple no longer selects PL031"
grep -Fq 'select PL061' "${SOURCE_DIR}/hw/vmapple/Kconfig" ||
    fail "P3_01_GENERIC_GPIO_MISSING" "VMApple no longer selects PL061"
grep -Fq 'TYPE_VMAPPLE_CFG' "${SOURCE_DIR}/hw/vmapple/vmapple.c" ||
    fail "P3_01_CFG_MISSING" "VMApple cfg device wiring missing"
grep -Fq 'TYPE_VMAPPLE_BDIF' "${SOURCE_DIR}/hw/vmapple/vmapple.c" ||
    fail "P3_01_BDIF_MISSING" "VMApple backdoor wiring missing"
grep -Fq 'VMAPPLE_APV_GFX' "${SOURCE_DIR}/hw/vmapple/vmapple.c" ||
    fail "P3_01_GFX_MAP_MISSING" "VMApple graphics map missing"
grep -Fq 'uint64_t ecid' "${SOURCE_DIR}/hw/vmapple/cfg.c" ||
    fail "P3_01_CFG_ECID_MISSING" "VMApple cfg ECID field missing"
grep -Fq 'char model[32]' "${SOURCE_DIR}/hw/vmapple/cfg.c" ||
    fail "P3_01_CFG_MODEL_MISSING" "VMApple cfg model field missing"
grep -Fq 'VBLK_DATA_FLAGS_READ' "${SOURCE_DIR}/hw/vmapple/bdif.c" ||
    fail "P3_01_BDIF_READ_MISSING" "VMApple BDIF read path missing"
grep -Fq 'PCI_VENDOR_ID_APPLE' "${SOURCE_DIR}/hw/vmapple/virtio-blk.c" ||
    fail "P3_01_STORAGE_APPLE_ID_MISSING" "VMApple virtio-blk Apple PCI identity missing"

FINAL_STAGE="summary"
safe_reset_work_root
python3 "${TOOL}" --contract "${CONTRACT}" summary --json > "${SUMMARY_FILE}"
cat "${SUMMARY_FILE}"

FINAL_STAGE="summary-validation"
python3 - "${SUMMARY_FILE}" <<'PY'
import json
from pathlib import Path
import sys
data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
if data.get("classification") != "P3_01_PLATFORM_CONTRACT_VALID":
    raise SystemExit("P3.01 summary classification mismatch")
if data.get("component_count", 0) < 15:
    raise SystemExit("P3.01 platform inventory unexpectedly small")
if data.get("guest_execution") is not False:
    raise SystemExit("P3.01 must remain non-guest")
if data.get("next_objective") != "P3.02":
    raise SystemExit("P3.01 next objective mismatch")
for required in ("generic_qemu", "vmapple_specific", "host_framework_dependent", "unknown_requires_evidence"):
    if data.get("ownership_counts", {}).get(required, 0) < 1:
        raise SystemExit(f"ownership class missing from summary: {required}")
print("P3.01 deterministic summary: PASS")
PY

echo "No QEMU/macOS/HVF/TCG guest or m1n1 runtime was launched."
CLASSIFICATION="P3_01_PREPARATION_PASS"
FINAL_STAGE="complete"
echo "P3.01 platform contract preparation: PASS"

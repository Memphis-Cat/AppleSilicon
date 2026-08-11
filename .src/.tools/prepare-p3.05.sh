#!/usr/bin/env bash
set -Eeuo pipefail

VERSION="3.4.0.0.0.0"
EXPECTED_INFERNO_REVISION="cc4302a99167abec69b714cfd00c38caece7e7de"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SOURCE_DIR="${APPLESILICON_INFERNO_SOURCE:-${ROOT_DIR}/.src/.upstream/.inferno}"
CONTRACT="${ROOT_DIR}/.src/.configs/p3.05-peripheral-contract.json"
TOOL="${ROOT_DIR}/.src/.tools/platform-peripheral-contract.py"
PVG_PATCH="${ROOT_DIR}/.src/.patches/0002-vmapple-optional-apple-pvg.patch"
WORK_ROOT="${APPLESILICON_P3_05_WORK_ROOT:-${ROOT_DIR}/.build/p3.05}"
SUMMARY_A="${WORK_ROOT}/platform-peripheral-summary-a.json"
SUMMARY_B="${WORK_ROOT}/platform-peripheral-summary-b.json"
LOG_DIR="${APPLESILICON_LOG_DIR:-${ROOT_DIR}/.logs}"
CLASSIFICATION="UNCLASSIFIED"
FINAL_STAGE="startup"

mkdir -p "${LOG_DIR}"
TIMESTAMP="$(date -u +"%Y%m%d-%H%M%S")"
LOG_FILE="${LOG_DIR}/AppleSilicon-p3.05-${TIMESTAMP}-$$.log"
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
    case "${WORK_ROOT}" in
        ""|"/"|"${ROOT_DIR}"|"${HOME}"|"${ROOT_DIR}/.build")
            fail "P3_05_UNSAFE_WORK_ROOT" "Refusing unsafe work-root reset: ${WORK_ROOT}"
            ;;
    esac
    [[ "${WORK_ROOT}" == "${ROOT_DIR}/.build/"* ]] ||
        fail "P3_05_UNSAFE_WORK_ROOT" "Work root must remain below ${ROOT_DIR}/.build"
    rm -rf "${WORK_ROOT}"
    mkdir -p "${WORK_ROOT}"
}

echo "AppleSilicon version: ${VERSION}"
echo "Objective: P3.05"
echo "Started UTC: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
echo "Inferno source: ${SOURCE_DIR}"

FINAL_STAGE="tool-preflight"
for command in git python3 cmp; do
    command -v "${command}" >/dev/null 2>&1 ||
        fail "P3_05_TOOL_MISSING" "Missing required command: ${command}"
done
for path in "${CONTRACT}" "${TOOL}" "${PVG_PATCH}"; do
    [[ -f "${path}" ]] || fail "P3_05_INPUT_MISSING" "Missing P3.05 input: ${path}"
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
AES="${SOURCE_DIR}/hw/vmapple/aes.c"
XHCI="${SOURCE_DIR}/hw/usb/hcd-xhci-pci.c"

check_blob() {
    local rel="$1"
    local expected="$2"
    local observed
    observed="$(git -C "${SOURCE_DIR}" hash-object "${rel}")"
    [[ "${observed}" == "${expected}" ]] ||
        fail "P3_05_SOURCE_BLOB_DRIFT" "${rel}: expected ${expected}; observed ${observed}"
    echo "source lock: PASS: ${rel} ${observed}"
}

check_blob "hw/vmapple/vmapple.c" "89c04c09f705d987ee96c11c1f5f4fc79713bf2e"
check_blob "hw/vmapple/Kconfig" "2382b297672274f27c447b9168cab9425f01ed17"
check_blob "hw/vmapple/aes.c" "3f6c2721bf3d8d46cc21323ef6d2492e28a7020b"
check_blob "hw/usb/hcd-xhci-pci.c" "b93c80b09d8237a1d2a5df0f5c7262fd1a292324"

PATCH_BLOB="$(git -C "${ROOT_DIR}" hash-object ".src/.patches/0002-vmapple-optional-apple-pvg.patch")"
[[ "${PATCH_BLOB}" == "04ac7e35c8c15bc6c2d7ef5b1cbc76f0c4875ecd" ]] ||
    fail "P3_05_PVG_PATCH_DRIFT" "P1.05 optional-PVG patch drifted: ${PATCH_BLOB}"
echo "project patch lock: PASS: ${PATCH_BLOB}"

FINAL_STAGE="source-contract"
python3 "${TOOL}" --contract "${CONTRACT}" verify-source \
    --vmapple "${VMAPPLE}" \
    --aes "${AES}" \
    --xhci "${XHCI}" \
    --pvg-patch "${PVG_PATCH}"

echo "Generic GPEX/virtio/XHCI paths remain preserved."
echo "AES unresolved command semantics remain evidence-gated."
echo "Apple PVG remains optional and host-framework dependent."

FINAL_STAGE="deterministic-summary"
safe_reset_work_root
python3 "${TOOL}" --contract "${CONTRACT}" summary > "${SUMMARY_A}"
python3 "${TOOL}" --contract "${CONTRACT}" summary > "${SUMMARY_B}"
cmp -s "${SUMMARY_A}" "${SUMMARY_B}" ||
    fail "P3_05_NONDETERMINISTIC_SUMMARY" "P3.05 summary differs across identical runs"

python3 - "${SUMMARY_A}" <<'PY'
import json
from pathlib import Path
import sys

data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
if data.get("classification") != "P3_05_SUMMARY":
    raise SystemExit("summary classification mismatch")
if data.get("pcie_irq_range") != [32, 47]:
    raise SystemExit("PCIe IRQ range mismatch")
if data.get("xhci_conditional_intr_mapping") is not True:
    raise SystemExit("XHCI macOS workaround missing")
if data.get("pvg_policy") != "warn_and_continue_without_pvg":
    raise SystemExit("PVG optionalization policy mismatch")
if data.get("runtime_executed") is not False:
    raise SystemExit("P3.05 preparation must remain non-guest")
if data.get("new_patch_required") is not False:
    raise SystemExit("P3.05 must not claim a new patch")
print("Deterministic summary: PASS")
print("Contract fingerprint:", data["fingerprint"])
PY

echo "No QEMU/macOS/HVF/TCG guest was launched."
echo "No proprietary firmware, disk or identity artifact was opened."
echo "No new Inferno source patch was introduced by P3.05."
CLASSIFICATION="P3_05_PREPARATION_PASS"
FINAL_STAGE="complete"
echo "P3.05 PCIe/peripheral/crypto/graphics preparation: PASS"

#!/usr/bin/env bash
set -Eeuo pipefail

VERSION="3.3.0.0.0.0"
EXPECTED_INFERNO_REVISION="cc4302a99167abec69b714cfd00c38caece7e7de"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SOURCE_DIR="${APPLESILICON_INFERNO_SOURCE:-${ROOT_DIR}/.src/.upstream/.inferno}"
CONTRACT="${ROOT_DIR}/.src/.configs/p3.04-storage-contract.json"
TOOL="${ROOT_DIR}/.src/.tools/platform-storage-contract.py"
WORK_ROOT="${APPLESILICON_P3_04_WORK_ROOT:-${ROOT_DIR}/.build/p3.04}"
SUMMARY_A="${WORK_ROOT}/platform-storage-summary-a.json"
SUMMARY_B="${WORK_ROOT}/platform-storage-summary-b.json"
LOG_DIR="${APPLESILICON_LOG_DIR:-${ROOT_DIR}/.logs}"
CLASSIFICATION="UNCLASSIFIED"
FINAL_STAGE="startup"

mkdir -p "${LOG_DIR}"
TIMESTAMP="$(date -u +"%Y%m%d-%H%M%S")"
LOG_FILE="${LOG_DIR}/AppleSilicon-p3.04-${TIMESTAMP}-$$.log"
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
)" || fail "P3_04_UNSAFE_WORK_ROOT" "Could not canonicalize P3.04 work root: ${WORK_ROOT}"
    normalized_build_root="$(python3 - "${ROOT_DIR}/.build" <<'PY'
from pathlib import Path
import sys
print(Path(sys.argv[1]).resolve(strict=False))
PY
)" || fail "P3_04_UNSAFE_WORK_ROOT" "Could not canonicalize project build root"
    case "${normalized_root}" in
        ""|"/"|"${ROOT_DIR}"|"${HOME}"|"${normalized_build_root}")
            fail "P3_04_UNSAFE_WORK_ROOT" "Refusing unsafe work-root reset: ${WORK_ROOT}"
            ;;
    esac
    [[ "${normalized_root}" == "${normalized_build_root}/"* ]] ||
        fail "P3_04_UNSAFE_WORK_ROOT" "Work root must remain below ${normalized_build_root}"
    WORK_ROOT="${normalized_root}"
    SUMMARY_A="${WORK_ROOT}/platform-storage-summary-a.json"
    SUMMARY_B="${WORK_ROOT}/platform-storage-summary-b.json"
    rm -rf -- "${WORK_ROOT}"
    mkdir -p "${WORK_ROOT}"
}

echo "AppleSilicon version: ${VERSION}"
echo "Objective: P3.04"
echo "Started UTC: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
echo "Inferno source: ${SOURCE_DIR}"

FINAL_STAGE="tool-preflight"
for command in git python3 cmp grep; do
    command -v "${command}" >/dev/null 2>&1 ||
        fail "P3_04_TOOL_MISSING" "Missing required command: ${command}"
done
for path in "${CONTRACT}" "${TOOL}"; do
    [[ -f "${path}" ]] || fail "P3_04_INPUT_MISSING" "Missing P3.04 input: ${path}"
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
BDIF="${SOURCE_DIR}/hw/vmapple/bdif.c"
VIRTIO="${SOURCE_DIR}/hw/vmapple/virtio-blk.c"
QAPI_VIRTIO="${SOURCE_DIR}/qapi/virtio.json"
PCI_IDS="${SOURCE_DIR}/include/hw/pci/pci_ids.h"

for path in "${VMAPPLE}" "${BDIF}" "${VIRTIO}" "${QAPI_VIRTIO}" "${PCI_IDS}"; do
    [[ -f "${path}" ]] || fail "P3_04_SOURCE_FILE_MISSING" "Missing source file: ${path}"
done

check_blob() {
    local relative="$1"
    local expected="$2"
    local observed
    observed="$(git -C "${SOURCE_DIR}" hash-object "${relative}")"
    [[ "${observed}" == "${expected}" ]] ||
        fail "P3_04_SOURCE_BLOB_DRIFT" "${relative} blob drifted: expected ${expected}; observed ${observed}"
    echo "source lock: PASS: ${relative} ${observed}"
}

check_blob "hw/vmapple/vmapple.c" "89c04c09f705d987ee96c11c1f5f4fc79713bf2e"
check_blob "hw/vmapple/bdif.c" "5ccd374581969c0e8c70714fbd82aa0bdb0e189f"
check_blob "hw/vmapple/virtio-blk.c" "5d990e63079714b0fc6deea0caf588f2be6a9241"

FINAL_STAGE="source-contract"
python3 "${TOOL}" --contract "${CONTRACT}" verify-source \
    --vmapple "${VMAPPLE}" \
    --bdif "${BDIF}" \
    --virtio-blk "${VIRTIO}"

grep -Fq "{ 'enum': 'VMAppleVirtioBlkVariant'" "${QAPI_VIRTIO}" ||
    fail "P3_04_VARIANT_ENUM_MISSING" "VMApple virtio-blk variant enum is missing"
grep -Fq "'data': [ 'unspecified', 'root', 'aux' ]" "${QAPI_VIRTIO}" ||
    fail "P3_04_VARIANT_ENUM_DRIFT" "VMApple virtio-blk variant enum order drifted"
grep -Fq '#define PCI_VENDOR_ID_APPLE              0x106b' "${PCI_IDS}" ||
    fail "P3_04_APPLE_VENDOR_ID_DRIFT" "Apple PCI vendor ID drifted"
grep -Fq '#define PCI_DEVICE_ID_APPLE_VIRTIO_BLK   0x1a00' "${PCI_IDS}" ||
    fail "P3_04_APPLE_DEVICE_ID_DRIFT" "Apple virtio-blk PCI device ID drifted"

echo "Pinned boot/storage source contract: PASS"
echo "BDIF write support remains runtime-evidence gated."
echo "Apple barrier flush semantics remain runtime-evidence gated."

FINAL_STAGE="deterministic-summary"
safe_reset_work_root
python3 "${TOOL}" --contract "${CONTRACT}" summary > "${SUMMARY_A}"
python3 "${TOOL}" --contract "${CONTRACT}" summary > "${SUMMARY_B}"
cmp -s "${SUMMARY_A}" "${SUMMARY_B}" ||
    fail "P3_04_NONDETERMINISTIC_SUMMARY" "P3.04 summary differs across identical runs"

python3 - "${SUMMARY_A}" <<'PY'
import json
from pathlib import Path
import sys
data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
if data.get("classification") != "P3_04_SUMMARY":
    raise SystemExit("summary classification mismatch")
if data.get("bdif_base") != "0x30000000":
    raise SystemExit("BDIF base mismatch")
if data.get("bdif_read_only") is not True:
    raise SystemExit("BDIF must remain read-only")
if data.get("runtime_variants") != ["root", "aux"]:
    raise SystemExit("runtime storage variants mismatch")
if data.get("pci_vendor_id") != "0x106b" or data.get("pci_device_id") != "0x1a00":
    raise SystemExit("Apple virtio-blk PCI identity mismatch")
if data.get("barrier") != "successful_no_op":
    raise SystemExit("Apple barrier contract mismatch")
if data.get("runtime_executed") is not False:
    raise SystemExit("P3.04 preparation must remain non-guest")
print("Deterministic summary: PASS")
print("Contract fingerprint:", data["fingerprint"])
PY

echo "No QEMU/macOS/HVF/TCG guest was launched."
echo "No firmware, AUX image or root disk was opened by this preparation step."
echo "No new Inferno source patch was applied."
CLASSIFICATION="P3_04_PREPARATION_PASS"
FINAL_STAGE="complete"
echo "P3.04 boot backdoor/storage preparation: PASS"

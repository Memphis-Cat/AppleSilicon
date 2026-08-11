#!/usr/bin/env bash

set -Eeuo pipefail

VERSION="2.0.0.0.0.0"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
LOG_DIR="${APPLESILICON_LOG_DIR:-${ROOT_DIR}/.logs}"
CONTRACT="${APPLESILICON_P2_01_CONTRACT:-${ROOT_DIR}/.src/.configs/p2.01-cpu-contract.json}"
TOOL="${ROOT_DIR}/.src/.tools/cpu-contract.py"

mkdir -p "${LOG_DIR}"
TIMESTAMP="$(date -u +"%Y%m%d-%H%M%S")"
LOG_FILE="${LOG_DIR}/AppleSilicon-p2.01-${TIMESTAMP}-$$.log"
FINAL_STAGE="startup"
CLASSIFICATION="UNCLASSIFIED"

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

echo "AppleSilicon version: ${VERSION}"
echo "Objective: P2.01"
echo "Started UTC: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
echo "Host OS: $(uname -s 2>/dev/null || echo unknown)"
echo "Host architecture: $(uname -m 2>/dev/null || echo unknown)"
echo "Contract: ${CONTRACT}"
echo "Tool: ${TOOL}"

FINAL_STAGE="input-validation"
[[ -f "${CONTRACT}" && -r "${CONTRACT}" ]] || fail "P2_01_CONTRACT_MISSING" "CPU contract is unavailable: ${CONTRACT}"
[[ -f "${TOOL}" && -r "${TOOL}" ]] || fail "P2_01_TOOL_MISSING" "CPU contract tool is unavailable: ${TOOL}"
command -v python3 >/dev/null 2>&1 || fail "P2_01_PYTHON_MISSING" "python3 is required."

FINAL_STAGE="json-syntax"
python3 - "${CONTRACT}" <<'PY'
import json
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
with path.open("r", encoding="utf-8") as handle:
    value = json.load(handle)
if not isinstance(value, dict):
    raise SystemExit("contract root must be an object")
print("JSON syntax: PASS")
PY

FINAL_STAGE="python-syntax"
python3 - "${TOOL}" <<'PY'
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
source = path.read_text(encoding="utf-8")
compile(source, str(path), "exec")
print("Python syntax: PASS")
PY

FINAL_STAGE="contract-validation"
python3 "${TOOL}" validate --contract "${CONTRACT}"

FINAL_STAGE="self-check"
python3 "${TOOL}" self-check --contract "${CONTRACT}"

FINAL_STAGE="summary"
python3 "${TOOL}" summary --contract "${CONTRACT}"

FINAL_STAGE="representative-lookups"
echo "--- HID0 ---"
python3 "${TOOL}" lookup HID0 --contract "${CONTRACT}"
echo "--- GXF_CONFIG_EL1 ---"
python3 "${TOOL}" lookup GXF_CONFIG_EL1 --contract "${CONTRACT}"

FINAL_STAGE="complete"
CLASSIFICATION="P2_01_PREPARATION_PASS"
echo "P2.01 preparation: PASS"
echo "No QEMU/macOS/HVF/TCG guest/m1n1 runtime was launched."

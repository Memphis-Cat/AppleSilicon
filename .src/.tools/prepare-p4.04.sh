#!/usr/bin/env bash
set -Eeuo pipefail

VERSION="4.3.0.0.0.0"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
POLICY="${ROOT_DIR}/.src/.configs/p4.04-ab-session-policy.json"
TOOL="${ROOT_DIR}/.src/.tools/ab-session.py"
ASSEMBLER="${ROOT_DIR}/.src/.tools/assemble-p4.04.sh"
P1_TOOL="${ROOT_DIR}/.src/.tools/reference-manifest.py"
P1_POLICY="${ROOT_DIR}/.src/.configs/p1.09-manifest-policy.json"
LOG_DIR="${APPLESILICON_LOG_DIR:-${ROOT_DIR}/.logs}"
CLASSIFICATION="UNCLASSIFIED"
FINAL_STAGE="startup"

mkdir -p "${LOG_DIR}"
TIMESTAMP="$(date -u +"%Y%m%d-%H%M%S")"
LOG_FILE="${LOG_DIR}/AppleSilicon-p4.04-prepare-${TIMESTAMP}-$$.log"
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
echo "Objective: P4.04 static preparation"
echo "No guest is launched and no divergence is promoted by this command."

FINAL_STAGE="file-validation"
for file in "${POLICY}" "${TOOL}" "${ASSEMBLER}" "${P1_TOOL}" "${P1_POLICY}"; do
    [[ -f "${file}" ]] || fail "P4_04_FILE_MISSING" "Required P4.04 file missing: ${file##*/}"
done

FINAL_STAGE="syntax-validation"
python3 - "${TOOL}" <<'PY'
from pathlib import Path
import sys
compile(Path(sys.argv[1]).read_text(encoding="utf-8"), sys.argv[1], "exec")
print("Python syntax: PASS")
PY
bash -n "${ASSEMBLER}"
echo "Bash syntax: PASS"

FINAL_STAGE="policy-validation"
python3 "${TOOL}" --policy "${POLICY}" validate-policy
python3 "${TOOL}" --policy "${POLICY}" self-check
python3 "${P1_TOOL}" self-check --policy "${P1_POLICY}"

FINAL_STAGE="patch-series-validation"
PATCH_COUNT="$(find "${ROOT_DIR}/.src/.patches" -maxdepth 1 -type f -name '[0-9][0-9][0-9][0-9]-*.patch' | wc -l | tr -d ' ')"
[[ "${PATCH_COUNT}" == "5" ]] || fail "P4_04_PATCH_SERIES_DRIFT" "Expected exactly five compatibility patches"

CLASSIFICATION="P4_04_VALIDATION_PASS"
FINAL_STAGE="complete"
echo "P4.04 static preparation: PASS"
echo "Real P4.02/P4.03 capture inputs remain deferred to integrated testing."

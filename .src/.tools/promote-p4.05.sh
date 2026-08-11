#!/usr/bin/env bash
set -Eeuo pipefail

VERSION="4.4.0.0.0.0"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
POLICY="${ROOT_DIR}/.src/.configs/p4.05-divergence-promotion-policy.json"
TOOL="${ROOT_DIR}/.src/.tools/divergence-promotion.py"
WORK_DIR="${APPLESILICON_P4_05_WORK_DIR:-${ROOT_DIR}/.build/p4.05}"
LOG_DIR="${APPLESILICON_LOG_DIR:-${ROOT_DIR}/.logs}"
OUTPUT="${APPLESILICON_P4_05_OUTPUT:-${WORK_DIR}/promotion.json}"
CLASSIFICATION="UNCLASSIFIED"
FINAL_STAGE="startup"

mkdir -p "${WORK_DIR}" "${LOG_DIR}"
TIMESTAMP="$(date -u +"%Y%m%d-%H%M%S")"
LOG_FILE="${LOG_DIR}/AppleSilicon-p4.05-promote-${TIMESTAMP}-$$.log"
RUN1="${WORK_DIR}/.promotion-run-1-$$"
RUN2="${WORK_DIR}/.promotion-run-2-$$"
TMP1="${WORK_DIR}/.promotion-1-$$.json"
TMP2="${WORK_DIR}/.promotion-2-$$.json"
exec > >(tee "${LOG_FILE}") 2>&1

cleanup() {
    rm -rf "${RUN1}" "${RUN2}"
    rm -f "${TMP1}" "${TMP2}"
}

on_exit() {
    local status=$?
    trap - EXIT
    cleanup
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

[[ -x "${TOOL}" ]] || fail "P4_05_TOOL_MISSING" "P4.05 promotion tool is missing or not executable"
[[ -f "${POLICY}" ]] || fail "P4_05_POLICY_MISSING" "P4.05 promotion policy is missing"

if (( $# < 10 || $# % 5 != 0 )); then
    fail "P4_05_INPUT_ERROR" \
        "Usage: promote-p4.05.sh AB REF_MANIFEST PROBE_MANIFEST REF_TRACE PROBE_TRACE [repeat for another reproduction]" \
        "At least two five-path reproduction groups are required."
fi

REPRO_ARGS=()
while (( $# )); do
    AB="$1"; REF_MANIFEST="$2"; PROBE_MANIFEST="$3"; REF_TRACE="$4"; PROBE_TRACE="$5"
    shift 5
    for pair in \
        "P4.04 A/B session|${AB}" \
        "reference manifest|${REF_MANIFEST}" \
        "probe manifest|${PROBE_MANIFEST}" \
        "reference trace|${REF_TRACE}" \
        "probe trace|${PROBE_TRACE}"; do
        LABEL="${pair%%|*}"
        PATH_VALUE="${pair#*|}"
        [[ -f "${PATH_VALUE}" && -r "${PATH_VALUE}" ]] ||
            fail "P4_05_INPUT_MISSING" "${LABEL} missing or unreadable"
    done
    REPRO_ARGS+=(--reproduction "${AB}" "${REF_MANIFEST}" "${PROBE_MANIFEST}" "${REF_TRACE}" "${PROBE_TRACE}")
done

echo "AppleSilicon version: ${VERSION}"
echo "Objective: P4.05 Reproducible Divergence Promotion"
echo "This command does not launch a guest. It consumes already captured runtime evidence."
echo "P1.10 remains the promotion authority and auto-commit remains disabled."

FINAL_STAGE="deterministic-promotion-1"
mkdir -p "${RUN1}"
python3 "${TOOL}" --policy "${POLICY}" promote \
    "${REPRO_ARGS[@]}" --work-dir "${RUN1}" --output "${TMP1}" >/dev/null ||
    fail "P4_05_PROMOTION_REJECTED" "P4.05/P1.10 rejected the supplied reproductions"

FINAL_STAGE="deterministic-promotion-2"
mkdir -p "${RUN2}"
python3 "${TOOL}" --policy "${POLICY}" promote \
    "${REPRO_ARGS[@]}" --work-dir "${RUN2}" --output "${TMP2}" >/dev/null ||
    fail "P4_05_PROMOTION_REJECTED" "P4.05 second deterministic promotion pass failed"

cmp -s "${TMP1}" "${TMP2}" ||
    fail "P4_05_NONDETERMINISTIC" "P4.05 promotion result differed across identical repeated evaluation"

FINAL_STAGE="publish-local-evidence"
rm -rf "${WORK_DIR}/candidates" "${WORK_DIR}/p1.10"
mv "${RUN1}/candidates" "${WORK_DIR}/candidates"
mv "${RUN1}/p1.10" "${WORK_DIR}/p1.10"
mkdir -p "$(dirname "${OUTPUT}")"
cp "${TMP1}" "${OUTPUT}"

python3 - "${OUTPUT}" <<'PY'
import json, re, sys
from pathlib import Path
path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")
data = json.loads(text)
if data.get("classification") != "P4_05_REPRODUCIBLE_DIVERGENCE_PROMOTED":
    raise SystemExit("P4.05 classification mismatch")
if data.get("divergence_promoted") is not True:
    raise SystemExit("P4.05 did not bind a P1.10 promotion")
auth = data.get("promotion_authority", {})
if auth.get("stage") != "P1.10" or auth.get("id") != "P01-DIVERGENCE-0001" or auth.get("status") != "promoted":
    raise SystemExit("P1.10 promotion authority mismatch")
if auth.get("auto_committed") is not False:
    raise SystemExit("P1.10 auto-commit unexpectedly enabled")
if auth.get("reproduction_count", 0) < 2:
    raise SystemExit("insufficient reproduction count")
fp = data.get("promotion_fingerprint")
if not isinstance(fp, str) or re.fullmatch(r"[0-9a-f]{64}", fp) is None:
    raise SystemExit("P4.05 promotion fingerprint invalid")
for forbidden in ("/Users/", "/home/", "C:\\Users\\"):
    if forbidden in text:
        raise SystemExit("local user path leaked into P4.05 output")
print(f"Promotion fingerprint: {fp}")
print(f"Divergence signature: {auth['divergence_signature']}")
PY

CLASSIFICATION="P4_05_REPRODUCIBLE_DIVERGENCE_PROMOTED"
FINAL_STAGE="complete"
echo "P4.05 reproducible divergence promotion: PROMOTED BY P1.10"
echo "Output: ${OUTPUT}"
echo "No source patch was created and no promotion artifact was auto-committed."

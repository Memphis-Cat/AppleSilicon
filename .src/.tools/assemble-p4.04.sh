#!/usr/bin/env bash
set -Eeuo pipefail

VERSION="4.3.0.0.0.0"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
POLICY="${ROOT_DIR}/.src/.configs/p4.04-ab-session-policy.json"
TOOL="${ROOT_DIR}/.src/.tools/ab-session.py"
LOG_DIR="${APPLESILICON_LOG_DIR:-${ROOT_DIR}/.logs}"
WORK_DIR="${APPLESILICON_P4_04_WORK_DIR:-${ROOT_DIR}/.build/p4.04}"
REFERENCE_PLAN="${APPLESILICON_P4_01_REFERENCE_PLAN:-}"
PROBE_PLAN="${APPLESILICON_P4_01_PROBE_PLAN:-}"
REFERENCE_CAPTURE="${APPLESILICON_P4_03_REFERENCE_CAPTURE:-}"
PROBE_CAPTURE="${APPLESILICON_P4_02_PROBE_CAPTURE:-}"
REFERENCE_MANIFEST="${APPLESILICON_P4_03_REFERENCE_MANIFEST:-}"
PROBE_MANIFEST="${APPLESILICON_P4_02_PROBE_MANIFEST:-}"
OUTPUT="${APPLESILICON_P4_04_OUTPUT:-${WORK_DIR}/ab-session.json}"
CLASSIFICATION="UNCLASSIFIED"
FINAL_STAGE="startup"

mkdir -p "${LOG_DIR}" "${WORK_DIR}"
TIMESTAMP="$(date -u +"%Y%m%d-%H%M%S")"
LOG_FILE="${LOG_DIR}/AppleSilicon-p4.04-assemble-${TIMESTAMP}-$$.log"
TMP1="${WORK_DIR}/.ab-session-1-$$.json"
TMP2="${WORK_DIR}/.ab-session-2-$$.json"
exec > >(tee "${LOG_FILE}") 2>&1

cleanup() { rm -f "${TMP1}" "${TMP2}"; }
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

require_file() {
    local classification="$1" label="$2" path="$3"
    [[ -n "${path}" ]] || fail "${classification}" "${label} is not configured"
    [[ -f "${path}" && -r "${path}" ]] || fail "${classification}" "${label} is missing or unreadable"
}

require_file "P4_04_REFERENCE_PLAN_MISSING" "P4.01 reference plan" "${REFERENCE_PLAN}"
require_file "P4_04_PROBE_PLAN_MISSING" "P4.01 probe plan" "${PROBE_PLAN}"
require_file "P4_04_REFERENCE_CAPTURE_MISSING" "P4.03 reference capture" "${REFERENCE_CAPTURE}"
require_file "P4_04_PROBE_CAPTURE_MISSING" "P4.02 probe capture" "${PROBE_CAPTURE}"
require_file "P4_04_REFERENCE_MANIFEST_MISSING" "P1.09 reference manifest" "${REFERENCE_MANIFEST}"
require_file "P4_04_PROBE_MANIFEST_MISSING" "P1.09 probe manifest" "${PROBE_MANIFEST}"
[[ -x "${TOOL}" ]] || fail "P4_04_TOOL_MISSING" "P4.04 assembler tool is not executable"

echo "AppleSilicon version: ${VERSION}"
echo "Objective: P4.04 Comparable A/B Session Assembly"
echo "No guest is launched. No divergence is promoted."

ARGS=(
    --policy "${POLICY}" assemble
    --reference-plan "${REFERENCE_PLAN}"
    --probe-plan "${PROBE_PLAN}"
    --reference-capture "${REFERENCE_CAPTURE}"
    --probe-capture "${PROBE_CAPTURE}"
    --reference-manifest "${REFERENCE_MANIFEST}"
    --probe-manifest "${PROBE_MANIFEST}"
)

FINAL_STAGE="deterministic-assembly-1"
python3 "${TOOL}" "${ARGS[@]}" --output "${TMP1}" >/dev/null ||
    fail "P4_04_NOT_COMPARABLE" "P4.04 rejected the supplied reference/probe pair"

FINAL_STAGE="deterministic-assembly-2"
python3 "${TOOL}" "${ARGS[@]}" --output "${TMP2}" >/dev/null ||
    fail "P4_04_NOT_COMPARABLE" "P4.04 second deterministic assembly failed"
cmp -s "${TMP1}" "${TMP2}" || fail "P4_04_NONDETERMINISTIC" "P4.04 A/B bundle was not byte-identical across repeated assembly"

FINAL_STAGE="output-validation"
mkdir -p "$(dirname "${OUTPUT}")"
cp "${TMP1}" "${OUTPUT}"
python3 - "${OUTPUT}" <<'PY'
import json, re, sys
from pathlib import Path
path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")
data = json.loads(text)
if data.get("classification") != "P4_04_AB_SESSION_READY":
    raise SystemExit("P4.04 classification mismatch")
if data.get("p1_09_pairing", {}).get("comparable") is not True:
    raise SystemExit("P1.09 comparability missing")
if data.get("p1_09_pairing", {}).get("contract_mismatches") != []:
    raise SystemExit("P1.09 pair contains mismatches")
if data.get("divergence_promoted") is not False:
    raise SystemExit("P4.04 must not promote a divergence")
fp = data.get("ab_fingerprint")
if not isinstance(fp, str) or re.fullmatch(r"[0-9a-f]{64}", fp) is None:
    raise SystemExit("P4.04 A/B fingerprint invalid")
for forbidden in ("/Users/", "/home/", "C:\\Users\\"):
    if forbidden in text:
        raise SystemExit("local user path leaked into P4.04 bundle")
print(f"A/B fingerprint: {fp}")
PY

CLASSIFICATION="P4_04_AB_SESSION_READY"
FINAL_STAGE="complete"
echo "P4.04 A/B session assembly: READY"
echo "Output: ${OUTPUT}"
echo "The pair is comparable; trace comparison and divergence promotion remain P1.08/P1.10 responsibilities."

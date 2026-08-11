#!/usr/bin/env bash
set -Eeuo pipefail

VERSION="4.1.0.0.0.0"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
POLICY="${ROOT_DIR}/.src/.configs/p4.02-probe-capture-policy.json"
TOOL="${ROOT_DIR}/.src/.tools/probe-capture.py"
RUNNER="${ROOT_DIR}/.src/.tools/run-p4.02-probe.sh"
LOG_DIR="${APPLESILICON_LOG_DIR:-${ROOT_DIR}/.logs}"
CLASSIFICATION="UNCLASSIFIED"
FINAL_STAGE="startup"

mkdir -p "${LOG_DIR}"
TIMESTAMP="$(date -u +"%Y%m%d-%H%M%S")"
LOG_FILE="${LOG_DIR}/AppleSilicon-p4.02-prepare-${TIMESTAMP}-$$.log"
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
echo "Objective: P4.02 static preparation"
echo "No guest is launched by this command."

FINAL_STAGE="file-validation"
for file in "${POLICY}" "${TOOL}" "${RUNNER}"; do
    [[ -f "${file}" ]] || fail "P4_02_FILE_MISSING" "Required P4.02 file missing: ${file##*/}"
done

FINAL_STAGE="syntax-validation"
python3 - "${TOOL}" <<'PY'
from pathlib import Path
import sys
compile(Path(sys.argv[1]).read_text(encoding="utf-8"), sys.argv[1], "exec")
print("Python syntax: PASS")
PY
bash -n "${RUNNER}"
echo "Bash syntax: PASS"

FINAL_STAGE="policy-validation"
python3 - "${POLICY}" <<'PY'
import json, sys
from pathlib import Path
p = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
expected = {"ram":"4G","ram_mib":4096,"smp":4,"capture_seconds":30,"grace_seconds":3}
if p.get("runtime_parameters") != expected:
    raise SystemExit("P4.02 runtime parameter lock drift")
if p.get("next_objective") != "P4.03":
    raise SystemExit("P4.02 next objective drift")
req = p.get("requirements", {})
for key in ("runtime_parameters_must_be_locked_before_run", "probe_manifest_ram_and_smp_must_match_runtime_parameters", "preflight_results_must_be_byte_identical", "capture_manifest_is_not_a_divergence_promotion", "p1_10_promotion_gate_remains_authoritative"):
    if req.get(key) is not True:
        raise SystemExit("P4.02 disabled requirement: " + key)
print("P4.02 runtime policy: PASS")
PY
python3 "${TOOL}" --policy "${POLICY}" validate-policy
python3 "${TOOL}" --policy "${POLICY}" self-check

FINAL_STAGE="patch-series-validation"
PATCH_COUNT="$(find "${ROOT_DIR}/.src/.patches" -maxdepth 1 -type f -name '[0-9][0-9][0-9][0-9]-*.patch' | wc -l | tr -d ' ')"
[[ "${PATCH_COUNT}" == "5" ]] || fail "P4_02_PATCH_SERIES_DRIFT" "Expected exactly five compatibility patches"

CLASSIFICATION="P4_02_VALIDATION_PASS"
FINAL_STAGE="complete"
echo "P4.02 static preparation: PASS"
echo "Runtime execution remains deferred."

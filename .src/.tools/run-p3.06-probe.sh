#!/usr/bin/env bash
set -Eeuo pipefail

VERSION="3.5.0.0.0.0"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
P3_MANIFEST="${APPLESILICON_P3_06_MANIFEST:-${ROOT_DIR}/.build/p3.06/platform-integration-manifest.json}"
P2_MANIFEST="${APPLESILICON_P2_06_MANIFEST:-${ROOT_DIR}/.build/p2.06/integration-manifest.json}"
INTEGRITY_TOOL="${ROOT_DIR}/.src/.tools/runtime_integrity.py"
P2_RUNNER="${ROOT_DIR}/.src/.tools/run-p2.06-probe.sh"
LOG_DIR="${APPLESILICON_LOG_DIR:-${ROOT_DIR}/.logs}"
CLASSIFICATION="UNCLASSIFIED"
FINAL_STAGE="startup"

mkdir -p "${LOG_DIR}"
TIMESTAMP="$(date -u +"%Y%m%d-%H%M%S")"
LOG_FILE="${LOG_DIR}/AppleSilicon-p3.06-runtime-${TIMESTAMP}-$$.log"
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
fail() { CLASSIFICATION="$1"; shift; printf '%s\n' "$@" >&2; exit 1; }

echo "AppleSilicon version: ${VERSION}"
echo "Objective: P3.06 final runtime wrapper"
echo "Started UTC: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"

FINAL_STAGE="platform-manifest-validation"
[[ -f "${P3_MANIFEST}" ]] || fail "P3_06_MANIFEST_MISSING" "P3.06 platform integration manifest is missing"
[[ -f "${P2_MANIFEST}" ]] || fail "P2_06_MANIFEST_MISSING" "P2.06 CPU integration manifest is missing"
[[ -x "${INTEGRITY_TOOL}" ]] || fail "P3_06_INTEGRITY_TOOL_MISSING" "Runtime integrity tool is not executable"
P3_FP="$(python3 "${INTEGRITY_TOOL}" verify-p3 "${P3_MANIFEST}" --p2 "${P2_MANIFEST}")" ||
    fail "P3_06_MANIFEST_INVALID" "P3.06/P2.06 fingerprints or binding did not reproduce"
P2_FP="$(python3 "${INTEGRITY_TOOL}" verify-p2 "${P2_MANIFEST}")" ||
    fail "P2_06_MANIFEST_INVALID" "P2.06 fingerprint did not reproduce"
python3 - "${P3_MANIFEST}" <<'PY'
import json,sys
from pathlib import Path
d=json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
expected={"machine":"vmapple","accelerator":"tcg","cpu":"apple-gxf","control_cpu":"max"}
if d.get("integrated_machine")!=expected: raise SystemExit("P3.06 integrated machine contract mismatch")
c=d.get("cross_contracts",{})
if c.get("fake_gpu_allowed") is not False: raise SystemExit("fake-GPU policy drift")
if c.get("layout_discrepancy")!="unresolved": raise SystemExit("P3.02 layout discrepancy unexpectedly resolved")
if c.get("power_semantics")!="evidence_gated": raise SystemExit("P3.03 power semantics lost evidence gate")
PY
echo "Platform integration fingerprint: ${P3_FP}"
echo "CPU integration fingerprint: ${P2_FP}"

FINAL_STAGE="runner-validation"
[[ -x "${P2_RUNNER}" ]] || fail "P2_06_RUNNER_MISSING" "P2.06 runtime wrapper is not executable"
echo "P3.06 platform contract gate: PASS"
echo "Delegating observational runtime probe to P2.06 → P1.07."

FINAL_STAGE="p2.06-runtime-delegate"
set +e
APPLESILICON_P2_06_MANIFEST="${P2_MANIFEST}" \
APPLESILICON_LOG_DIR="${LOG_DIR}" \
"${P2_RUNNER}"
STATUS=$?
set -e
CLASSIFICATION="P3_06_RUNTIME_DELEGATED"
FINAL_STAGE="complete"
echo "P2.06 delegated probe exit status: ${STATUS}"
echo "No runtime result is promoted by this wrapper itself."
exit "${STATUS}"

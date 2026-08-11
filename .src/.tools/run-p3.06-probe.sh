#!/usr/bin/env bash
set -Eeuo pipefail

VERSION="3.5.0.0.0.0"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
P3_MANIFEST="${APPLESILICON_P3_06_MANIFEST:-${ROOT_DIR}/.build/p3.06/platform-integration-manifest.json}"
P2_MANIFEST="${APPLESILICON_P2_06_MANIFEST:-${ROOT_DIR}/.build/p2.06/integration-manifest.json}"
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

fail() {
    CLASSIFICATION="$1"
    shift
    printf '%s\n' "$@" >&2
    exit 1
}

echo "AppleSilicon version: ${VERSION}"
echo "Objective: P3.06 final runtime wrapper"
echo "Started UTC: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"

FINAL_STAGE="platform-manifest-validation"
[[ -f "${P3_MANIFEST}" ]] ||
    fail "P3_06_MANIFEST_MISSING" "P3.06 platform integration manifest is missing: ${P3_MANIFEST}"
[[ -f "${P2_MANIFEST}" ]] ||
    fail "P2_06_MANIFEST_MISSING" "P2.06 CPU integration manifest is missing: ${P2_MANIFEST}"

python3 - "${P3_MANIFEST}" "${P2_MANIFEST}" <<'PY'
import json
from pathlib import Path
import sys

p3 = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
p2 = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))

if p3.get("classification") != "P3_06_INTEGRATION_PASS":
    raise SystemExit("P3.06 integration manifest did not pass")
if p3.get("part_status") != "closed_implementation_complete":
    raise SystemExit("Part 03 integration manifest is not closed")
if p3.get("guest_execution") is not False:
    raise SystemExit("P3.06 preparation manifest unexpectedly records guest execution")
if p3.get("integrated_machine") != {
    "machine": "vmapple",
    "accelerator": "tcg",
    "cpu": "apple-gxf",
    "control_cpu": "max",
}:
    raise SystemExit("P3.06 integrated machine contract mismatch")
if p3.get("cross_contracts", {}).get("fake_gpu_allowed") is not False:
    raise SystemExit("P3.06 fake-GPU policy drift")
if p3.get("cross_contracts", {}).get("layout_discrepancy") != "unresolved":
    raise SystemExit("P3.02 layout discrepancy unexpectedly resolved")
if p3.get("cross_contracts", {}).get("power_semantics") != "evidence_gated":
    raise SystemExit("P3.03 power semantics lost evidence gate")
if p3.get("p2_06", {}).get("live_sysreg_policy_count") != 0:
    raise SystemExit("live Apple sysreg policy count drift")

p3fp = p3.get("platform_integration_fingerprint")
if not isinstance(p3fp, str) or len(p3fp) != 64:
    raise SystemExit("P3.06 platform integration fingerprint invalid")

if p2.get("classification") != "P2_06_INTEGRATION_PASS":
    raise SystemExit("P2.06 integration manifest did not pass")
p2fp = p2.get("integration_fingerprint")
if p3.get("p2_06", {}).get("integration_fingerprint") != p2fp:
    raise SystemExit("P3.06 is not bound to the supplied P2.06 manifest")

print(f"Platform integration fingerprint: {p3fp}")
print(f"CPU integration fingerprint: {p2fp}")
PY

FINAL_STAGE="runner-validation"
[[ -x "${P2_RUNNER}" ]] ||
    fail "P2_06_RUNNER_MISSING" "P2.06 runtime wrapper is not executable: ${P2_RUNNER}"

echo "P3.06 platform contract gate: PASS"
echo "Delegating observational runtime probe to P2.06, which delegates to the locked P1.07 harness."
echo "Runtime evidence remains subject to P1.09 manifest pairing and P1.10 divergence promotion."

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

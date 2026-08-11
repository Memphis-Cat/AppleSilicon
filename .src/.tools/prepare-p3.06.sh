#!/usr/bin/env bash
set -Eeuo pipefail

VERSION="3.5.0.0.0.0"
EXPECTED_INFERNO_REVISION="cc4302a99167abec69b714cfd00c38caece7e7de"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SOURCE_DIR="${APPLESILICON_INFERNO_SOURCE:-${ROOT_DIR}/.src/.upstream/.inferno}"
WORK_ROOT="${APPLESILICON_P3_06_WORK_ROOT:-${ROOT_DIR}/.build/p3.06}"
POLICY="${ROOT_DIR}/.src/.configs/p3.06-integration-policy.json"
GATE_TOOL="${ROOT_DIR}/.src/.tools/platform-integration-gate.py"
P2_06_PREP="${ROOT_DIR}/.src/.tools/prepare-p2.06.sh"
P2_06_MANIFEST="${APPLESILICON_P2_06_MANIFEST:-${ROOT_DIR}/.build/p2.06/integration-manifest.json}"
MANIFEST="${WORK_ROOT}/platform-integration-manifest.json"
MANIFEST_2="${WORK_ROOT}/platform-integration-manifest.second.json"
LOG_DIR="${APPLESILICON_LOG_DIR:-${ROOT_DIR}/.logs}"

CLASSIFICATION="UNCLASSIFIED"
FINAL_STAGE="startup"

mkdir -p "${LOG_DIR}"
TIMESTAMP="$(date -u +"%Y%m%d-%H%M%S")"
LOG_FILE="${LOG_DIR}/AppleSilicon-p3.06-${TIMESTAMP}-$$.log"
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
            fail "P3_06_UNSAFE_WORK_ROOT" "Refusing unsafe work-root reset: ${WORK_ROOT}"
            ;;
    esac
    [[ "${WORK_ROOT}" == "${ROOT_DIR}/.build/"* ]] ||
        fail "P3_06_UNSAFE_WORK_ROOT" "Work root must remain below ${ROOT_DIR}/.build"
    rm -rf "${WORK_ROOT}"
    mkdir -p "${WORK_ROOT}"
}

echo "AppleSilicon version: ${VERSION}"
echo "Objective: P3.06"
echo "Started UTC: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
echo "Inferno source: ${SOURCE_DIR}"
echo "Platform integration manifest: ${MANIFEST}"

FINAL_STAGE="tool-preflight"
for command in git python3 cmp; do
    command -v "${command}" >/dev/null 2>&1 ||
        fail "P3_06_TOOL_MISSING" "Missing required command: ${command}"
done
for path in "${POLICY}" "${GATE_TOOL}" "${P2_06_PREP}"; do
    [[ -f "${path}" ]] || fail "P3_06_INPUT_MISSING" "Missing integration input: ${path}"
done

FINAL_STAGE="syntax-validation"
python3 - "${GATE_TOOL}" "${POLICY}" <<'PY'
import json
from pathlib import Path
import sys
script = Path(sys.argv[1])
policy = Path(sys.argv[2])
compile(script.read_text(encoding="utf-8"), str(script), "exec")
json.loads(policy.read_text(encoding="utf-8"))
print(f"Python syntax: PASS: {script}")
print(f"JSON syntax: PASS: {policy}")
PY
bash -n "${P2_06_PREP}"

FINAL_STAGE="source-preflight"
[[ -d "${SOURCE_DIR}" ]] || fail "SOURCE_UNAVAILABLE" "Inferno source directory does not exist"
git -C "${SOURCE_DIR}" rev-parse --is-inside-work-tree >/dev/null 2>&1 ||
    fail "SOURCE_INVALID" "Inferno source is not a Git work tree"
OBSERVED_REVISION="$(git -C "${SOURCE_DIR}" rev-parse HEAD)"
[[ "${OBSERVED_REVISION}" == "${EXPECTED_INFERNO_REVISION}" ]] ||
    fail "SOURCE_REVISION_MISMATCH" "Expected ${EXPECTED_INFERNO_REVISION}; observed ${OBSERVED_REVISION}"
[[ -z "$(git -C "${SOURCE_DIR}" status --porcelain --untracked-files=no)" ]] ||
    fail "SOURCE_DIRTY" "Pinned Inferno source contains tracked modifications"

FINAL_STAGE="work-root-reset"
safe_reset_work_root

FINAL_STAGE="p2.06-integration"
APPLESILICON_INFERNO_SOURCE="${SOURCE_DIR}" \
APPLESILICON_LOG_DIR="${LOG_DIR}" \
"${P2_06_PREP}"
[[ -f "${P2_06_MANIFEST}" ]] ||
    fail "P2_06_MANIFEST_MISSING" "P2.06 integration manifest was not produced: ${P2_06_MANIFEST}"

FINAL_STAGE="platform-integration-first"
python3 "${GATE_TOOL}" \
    --policy "${POLICY}" \
    --p2-06-manifest "${P2_06_MANIFEST}" \
    --output "${MANIFEST}"

FINAL_STAGE="platform-integration-second"
python3 "${GATE_TOOL}" \
    --policy "${POLICY}" \
    --p2-06-manifest "${P2_06_MANIFEST}" \
    --output "${MANIFEST_2}" >/dev/null

cmp -s "${MANIFEST}" "${MANIFEST_2}" ||
    fail "P3_06_NONDETERMINISTIC_MANIFEST" "Repeated P3.06 platform integration manifests differ"
rm -f "${MANIFEST_2}"

FINAL_STAGE="manifest-validation"
python3 - "${MANIFEST}" <<'PY'
import json
from pathlib import Path
import sys

data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
if data.get("classification") != "P3_06_INTEGRATION_PASS":
    raise SystemExit("P3.06 classification mismatch")
if data.get("guest_execution") is not False:
    raise SystemExit("P3.06 preparation must not execute a guest")
if data.get("part_status") != "closed_implementation_complete":
    raise SystemExit("P3.06 must close Part 03")
if data.get("next_part") != "Part 04" or data.get("next_objective") != "P4.01":
    raise SystemExit("P3.06 next-part transition mismatch")
if data.get("cross_contracts", {}).get("fake_gpu_allowed") is not False:
    raise SystemExit("fake GPU policy drift")
if data.get("p2_06", {}).get("live_sysreg_policy_count") != 0:
    raise SystemExit("live Apple sysreg policy drift")
fingerprint = data.get("platform_integration_fingerprint")
if not isinstance(fingerprint, str) or len(fingerprint) != 64:
    raise SystemExit("P3.06 platform integration fingerprint missing")
print(f"Platform integration fingerprint: {fingerprint}")
PY

echo "P3.01-P3.05 contract validators: PASS"
echo "Part 02 CPU integration binding: PASS"
echo "Part 01 runtime evidence/promotion binding: PASS"
echo "Part 03 patch series remains 0001 through 0005: PASS"
echo "Part 03 implementation state: CLOSED"
echo "No QEMU/macOS/HVF/TCG guest or m1n1 runtime was launched."

CLASSIFICATION="P3_06_INTEGRATION_PASS"
FINAL_STAGE="complete"
echo "P3.06 integration gate: PASS"

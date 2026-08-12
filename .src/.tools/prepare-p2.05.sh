#!/usr/bin/env bash
set -Eeuo pipefail

VERSION="2.4.0.0.0.0"
EXPECTED_INFERNO_REVISION="cc4302a99167abec69b714cfd00c38caece7e7de"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SOURCE_DIR="${APPLESILICON_INFERNO_SOURCE:-${ROOT_DIR}/.src/.upstream/.inferno}"
WORK_ROOT="${APPLESILICON_P2_05_WORK_ROOT:-${ROOT_DIR}/.build/p2.05}"
PREPARED_SOURCE="${WORK_ROOT}/inferno-src"
RESULT_FILE="${WORK_ROOT}/cpu-contract-regression.json"
RESULT_FILE_2="${WORK_ROOT}/cpu-contract-regression.second.json"
LOG_DIR="${APPLESILICON_LOG_DIR:-${ROOT_DIR}/.logs}"

P2_01_TOOL="${ROOT_DIR}/.src/.tools/cpu-contract.py"
REGRESSION_TOOL="${ROOT_DIR}/.src/.tools/cpu-contract-regression.py"
P2_01_CONTRACT="${ROOT_DIR}/.src/.configs/p2.01-cpu-contract.json"
REGRESSION_POLICY="${ROOT_DIR}/.src/.configs/p2.05-regression-policy.json"

PATCHES=(
    "${ROOT_DIR}/.src/.patches/0001-vmapple-decouple-build-from-hvf.patch"
    "${ROOT_DIR}/.src/.patches/0002-vmapple-optional-apple-pvg.patch"
    "${ROOT_DIR}/.src/.patches/0003-arm-apple-sysreg-framework.patch"
    "${ROOT_DIR}/.src/.patches/0004-arm-apple-sysreg-policy-model.patch"
    "${ROOT_DIR}/.src/.patches/0005-arm-vmapple-feature-contract.patch"
)

CLASSIFICATION="UNCLASSIFIED"
FINAL_STAGE="startup"

mkdir -p "${LOG_DIR}"
TIMESTAMP="$(date -u +"%Y%m%d-%H%M%S")"
LOG_FILE="${LOG_DIR}/AppleSilicon-p2.05-${TIMESTAMP}-$$.log"
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
)" || fail "P2_05_UNSAFE_WORK_ROOT" "Could not canonicalize P2.05 work root: ${WORK_ROOT}"
    normalized_build_root="$(python3 - "${ROOT_DIR}/.build" <<'PY'
from pathlib import Path
import sys
print(Path(sys.argv[1]).resolve(strict=False))
PY
)" || fail "P2_05_UNSAFE_WORK_ROOT" "Could not canonicalize project build root"
    case "${normalized_root}" in
        ""|"/"|"${ROOT_DIR}"|"${HOME}"|"${normalized_build_root}")
            fail "P2_05_UNSAFE_WORK_ROOT" "Refusing unsafe work-root reset: ${WORK_ROOT}"
            ;;
    esac
    [[ "${normalized_root}" == "${normalized_build_root}/"* ]] ||
        fail "P2_05_UNSAFE_WORK_ROOT" "Work root must remain below ${normalized_build_root}"
    WORK_ROOT="${normalized_root}"
    PREPARED_SOURCE="${WORK_ROOT}/inferno-src"
    RESULT_FILE="${WORK_ROOT}/cpu-contract-regression.json"
    RESULT_FILE_2="${WORK_ROOT}/cpu-contract-regression.second.json"
    rm -rf -- "${WORK_ROOT}"
    mkdir -p "${WORK_ROOT}"
}

echo "AppleSilicon version: ${VERSION}"
echo "Objective: P2.05"
echo "Started UTC: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
echo "Host OS: $(uname -s 2>/dev/null || echo unknown)"
echo "Host architecture: $(uname -m 2>/dev/null || echo unknown)"
echo "Inferno source: ${SOURCE_DIR}"
echo "Expected Inferno revision: ${EXPECTED_INFERNO_REVISION}"
echo "Regression output: ${RESULT_FILE}"

FINAL_STAGE="tool-preflight"
for command in git python3 cmp; do
    command -v "${command}" >/dev/null 2>&1 ||
        fail "P2_05_TOOL_MISSING" "Missing required command: ${command}"
done

for path in "${P2_01_TOOL}" "${REGRESSION_TOOL}" "${P2_01_CONTRACT}" "${REGRESSION_POLICY}"; do
    [[ -f "${path}" ]] || fail "P2_05_INPUT_MISSING" "Missing required P2.05 input: ${path}"
done

FINAL_STAGE="python-syntax"
python3 - "${P2_01_TOOL}" "${REGRESSION_TOOL}" <<'PY'
from pathlib import Path
import sys
for raw in sys.argv[1:]:
    path = Path(raw)
    compile(path.read_text(encoding="utf-8"), str(path), "exec")
    print(f"Python syntax: PASS: {path}")
PY

FINAL_STAGE="contract-regressions"
python3 "${P2_01_TOOL}" validate --contract "${P2_01_CONTRACT}"
python3 "${P2_01_TOOL}" self-check --contract "${P2_01_CONTRACT}"
python3 "${REGRESSION_TOOL}" --root "${ROOT_DIR}" --policy "${REGRESSION_POLICY}" validate-policy
python3 "${REGRESSION_TOOL}" --root "${ROOT_DIR}" --policy "${REGRESSION_POLICY}" self-check

FINAL_STAGE="source-validation"
[[ -d "${SOURCE_DIR}" ]] || fail "SOURCE_UNAVAILABLE" "Inferno source directory does not exist"
git -C "${SOURCE_DIR}" rev-parse --is-inside-work-tree >/dev/null 2>&1 ||
    fail "SOURCE_INVALID" "Inferno source is not a Git work tree"
OBSERVED_REVISION="$(git -C "${SOURCE_DIR}" rev-parse HEAD)"
[[ "${OBSERVED_REVISION}" == "${EXPECTED_INFERNO_REVISION}" ]] ||
    fail "SOURCE_REVISION_MISMATCH" "Expected ${EXPECTED_INFERNO_REVISION}; observed ${OBSERVED_REVISION}"
[[ -z "$(git -C "${SOURCE_DIR}" status --porcelain --untracked-files=no)" ]] ||
    fail "SOURCE_DIRTY" "Pinned Inferno source contains tracked modifications"

for patch in "${PATCHES[@]}"; do
    [[ -f "${patch}" ]] || fail "PATCH_MISSING" "Required patch is missing: ${patch}"
done

FINAL_STAGE="work-root-reset"
safe_reset_work_root

FINAL_STAGE="source-clone"
git clone --quiet --no-hardlinks "${SOURCE_DIR}" "${PREPARED_SOURCE}"
git -C "${PREPARED_SOURCE}" checkout --quiet --detach "${EXPECTED_INFERNO_REVISION}"

FINAL_STAGE="inferno-submodules"
git -C "${PREPARED_SOURCE}" submodule update --init --recursive -- util/mlib

[[ -f "${PREPARED_SOURCE}/util/mlib/m-algo.h" ]] ||
    fail "INFERNO_MLIB_MISSING" "Required Inferno util/mlib submodule was not initialized"


FINAL_STAGE="patch-series"
for patch in "${PATCHES[@]}"; do
    echo "Checking patch: ${patch}"
    git -C "${PREPARED_SOURCE}" apply --check "${patch}" ||
        fail "PATCH_CHECK_FAILED" "Patch does not apply cleanly: ${patch}"
    git -C "${PREPARED_SOURCE}" apply "${patch}" ||
        fail "PATCH_APPLY_FAILED" "Patch failed to apply: ${patch}"
done

git -C "${PREPARED_SOURCE}" diff --check ||
    fail "PATCH_DIFF_CHECK_FAILED" "Patched source fails git diff --check"

FINAL_STAGE="deterministic-regression-first"
python3 "${REGRESSION_TOOL}" \
    --root "${ROOT_DIR}" \
    --policy "${REGRESSION_POLICY}" \
    run \
    --prepared-source "${PREPARED_SOURCE}" \
    --output "${RESULT_FILE}"

FINAL_STAGE="deterministic-regression-second"
python3 "${REGRESSION_TOOL}" \
    --root "${ROOT_DIR}" \
    --policy "${REGRESSION_POLICY}" \
    run \
    --prepared-source "${PREPARED_SOURCE}" \
    --output "${RESULT_FILE_2}" >/dev/null

cmp -s "${RESULT_FILE}" "${RESULT_FILE_2}" ||
    fail "P2_05_NONDETERMINISTIC_RESULT" "Repeated CPU contract regression produced different JSON"

FINAL_STAGE="result-validation"
python3 - "${RESULT_FILE}" "${EXPECTED_INFERNO_REVISION}" <<'PY'
import json
from pathlib import Path
import sys
result = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
expected_inferno = sys.argv[2]
if result.get("classification") != "P2_05_REGRESSION_PASS":
    raise SystemExit("P2.05 result classification mismatch")
if result.get("guest_execution") is not False:
    raise SystemExit("P2.05 regression must remain non-guest")
if result.get("cross_contracts", {}).get("live_sysreg_policy_count") != 0:
    raise SystemExit("P2.03 live sysreg policy count drifted")
if result.get("cross_contracts", {}).get("inferno_revision") != expected_inferno:
    raise SystemExit("P2.05 Inferno source lock mismatch")
if result.get("prepared_source", {}).get("max_control_isolated") is not True:
    raise SystemExit("max control CPU isolation failed")
if result.get("prepared_source", {}).get("apple_gxf_tcg_wiring") is not True:
    raise SystemExit("apple-gxf TCG wiring failed")
fingerprint = result.get("suite_fingerprint")
if not isinstance(fingerprint, str) or len(fingerprint) != 64:
    raise SystemExit("P2.05 suite fingerprint missing or invalid")
print(f"Suite fingerprint: {fingerprint}")
print("Repeated deterministic result: PASS")
PY

rm -f "${RESULT_FILE_2}"

echo "P2.01 inventory validator: PASS"
echo "P2.02 representative/fail-closed contract: PASS"
echo "P2.03 empty semantic policy/fail-closed invariants: PASS"
echo "P2.04 architectural feature contract: PASS"
echo "Patched apple-gxf source invariants: PASS"
echo "No QEMU/macOS/HVF/TCG guest or m1n1 runtime was launched."

CLASSIFICATION="P2_05_REGRESSION_PASS"
FINAL_STAGE="complete"
echo "P2.05 deterministic CPU contract regression: PASS"

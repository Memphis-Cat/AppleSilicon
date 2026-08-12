#!/usr/bin/env bash
set -Eeuo pipefail

VERSION="2.5.0.0.0.0"
EXPECTED_INFERNO_REVISION="cc4302a99167abec69b714cfd00c38caece7e7de"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SOURCE_DIR="${APPLESILICON_INFERNO_SOURCE:-${ROOT_DIR}/.src/.upstream/.inferno}"
WORK_ROOT="${APPLESILICON_P2_06_WORK_ROOT:-${ROOT_DIR}/.build/p2.06}"
PREPARED_SOURCE="${WORK_ROOT}/inferno-src"
P2_05_WORK="${WORK_ROOT}/p2.05"
P2_05_RESULT="${P2_05_WORK}/cpu-contract-regression.json"
MANIFEST="${WORK_ROOT}/integration-manifest.json"
MANIFEST_2="${WORK_ROOT}/integration-manifest.second.json"
POLICY="${ROOT_DIR}/.src/.configs/p2.06-integration-policy.json"
GATE_TOOL="${ROOT_DIR}/.src/.tools/integration-gate.py"
P2_05_PREP="${ROOT_DIR}/.src/.tools/prepare-p2.05.sh"
LOG_DIR="${APPLESILICON_LOG_DIR:-${ROOT_DIR}/.logs}"

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
LOG_FILE="${LOG_DIR}/AppleSilicon-p2.06-${TIMESTAMP}-$$.log"
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
)" || fail "P2_06_UNSAFE_WORK_ROOT" "Could not canonicalize P2.06 work root: ${WORK_ROOT}"
    normalized_build_root="$(python3 - "${ROOT_DIR}/.build" <<'PY'
from pathlib import Path
import sys
print(Path(sys.argv[1]).resolve(strict=False))
PY
)" || fail "P2_06_UNSAFE_WORK_ROOT" "Could not canonicalize project build root"
    case "${normalized_root}" in
        ""|"/"|"${ROOT_DIR}"|"${HOME}"|"${normalized_build_root}")
            fail "P2_06_UNSAFE_WORK_ROOT" "Refusing unsafe work-root reset: ${WORK_ROOT}"
            ;;
    esac
    [[ "${normalized_root}" == "${normalized_build_root}/"* ]] ||
        fail "P2_06_UNSAFE_WORK_ROOT" "Work root must remain below ${normalized_build_root}"
    WORK_ROOT="${normalized_root}"
    PREPARED_SOURCE="${WORK_ROOT}/inferno-src"
    P2_05_WORK="${WORK_ROOT}/p2.05"
    P2_05_RESULT="${P2_05_WORK}/cpu-contract-regression.json"
    MANIFEST="${WORK_ROOT}/integration-manifest.json"
    MANIFEST_2="${WORK_ROOT}/integration-manifest.second.json"
    rm -rf -- "${WORK_ROOT}"
    mkdir -p "${WORK_ROOT}"
}

echo "AppleSilicon version: ${VERSION}"
echo "Objective: P2.06"
echo "Started UTC: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
echo "Inferno source: ${SOURCE_DIR}"
echo "Integration manifest: ${MANIFEST}"

FINAL_STAGE="tool-preflight"
for command in git python3 cmp; do
    command -v "${command}" >/dev/null 2>&1 ||
        fail "P2_06_TOOL_MISSING" "Missing required command: ${command}"
done
for path in "${POLICY}" "${GATE_TOOL}" "${P2_05_PREP}"; do
    [[ -f "${path}" ]] || fail "P2_06_INPUT_MISSING" "Missing integration input: ${path}"
done

FINAL_STAGE="syntax-validation"
python3 - "${GATE_TOOL}" <<'PY'
from pathlib import Path
import sys
path = Path(sys.argv[1])
compile(path.read_text(encoding="utf-8"), str(path), "exec")
print(f"Python syntax: PASS: {path}")
PY

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

FINAL_STAGE="p2.05-regression"
APPLESILICON_P2_05_WORK_ROOT="${P2_05_WORK}" \
APPLESILICON_LOG_DIR="${LOG_DIR}" \
APPLESILICON_INFERNO_SOURCE="${SOURCE_DIR}" \
"${P2_05_PREP}"
[[ -f "${P2_05_RESULT}" ]] ||
    fail "P2_05_RESULT_MISSING" "P2.05 regression result was not produced"

FINAL_STAGE="integrated-source-clone"
git clone --quiet --no-hardlinks "${SOURCE_DIR}" "${PREPARED_SOURCE}"
git -C "${PREPARED_SOURCE}" checkout --quiet --detach "${EXPECTED_INFERNO_REVISION}"

FINAL_STAGE="integrated-patch-series"
for patch in "${PATCHES[@]}"; do
    git -C "${PREPARED_SOURCE}" apply --check "${patch}" ||
        fail "PATCH_CHECK_FAILED" "Patch does not apply cleanly: ${patch}"
    git -C "${PREPARED_SOURCE}" apply "${patch}" ||
        fail "PATCH_APPLY_FAILED" "Patch failed to apply: ${patch}"
done
git -C "${PREPARED_SOURCE}" diff --check ||
    fail "PATCH_DIFF_CHECK_FAILED" "Integrated prepared source fails git diff --check"

FINAL_STAGE="integration-manifest-first"
python3 "${GATE_TOOL}" \
    --policy "${POLICY}" \
    --p2-05-result "${P2_05_RESULT}" \
    --prepared-source "${PREPARED_SOURCE}" \
    --output "${MANIFEST}"

FINAL_STAGE="integration-manifest-second"
python3 "${GATE_TOOL}" \
    --policy "${POLICY}" \
    --p2-05-result "${P2_05_RESULT}" \
    --prepared-source "${PREPARED_SOURCE}" \
    --output "${MANIFEST_2}" >/dev/null

cmp -s "${MANIFEST}" "${MANIFEST_2}" ||
    fail "P2_06_NONDETERMINISTIC_MANIFEST" "Repeated integration manifests differ"
rm -f "${MANIFEST_2}"

FINAL_STAGE="manifest-validation"
python3 - "${MANIFEST}" <<'PY'
import json
from pathlib import Path
import sys
data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
if data.get("classification") != "P2_06_INTEGRATION_PASS":
    raise SystemExit("P2.06 classification mismatch")
if data.get("guest_execution") is not False:
    raise SystemExit("P2.06 must remain non-guest during development")
if data.get("part_status") != "closed_implementation_complete":
    raise SystemExit("P2.06 must close Part 02")
if data.get("next_part") != "Part 03" or data.get("next_objective") != "P3.01":
    raise SystemExit("P2.06 next-part transition mismatch")
fingerprint = data.get("integration_fingerprint")
if not isinstance(fingerprint, str) or len(fingerprint) != 64:
    raise SystemExit("P2.06 integration fingerprint missing")
print(f"Integration fingerprint: {fingerprint}")
PY

echo "P2.05 deterministic CPU regression: PASS"
echo "Part 01 probe/evidence contract binding: PASS"
echo "Pinned integrated source and patch series: PASS"
echo "apple-gxf + TCG + vmapple integration contract: PASS"
echo "Part 02 implementation state: CLOSED"
echo "No QEMU/macOS/HVF/TCG guest or m1n1 runtime was launched."

CLASSIFICATION="P2_06_INTEGRATION_PASS"
FINAL_STAGE="complete"
echo "P2.06 integration gate: PASS"

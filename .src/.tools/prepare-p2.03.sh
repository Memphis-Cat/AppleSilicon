#!/usr/bin/env bash

set -Eeuo pipefail

VERSION="2.2.0.0.0.0"
EXPECTED_INFERNO_REVISION="cc4302a99167abec69b714cfd00c38caece7e7de"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SOURCE_DIR="${APPLESILICON_INFERNO_SOURCE:-${ROOT_DIR}/.src/.upstream/.inferno}"
PATCH_0001="${ROOT_DIR}/.src/.patches/0001-vmapple-decouple-build-from-hvf.patch"
PATCH_0002="${ROOT_DIR}/.src/.patches/0002-vmapple-optional-apple-pvg.patch"
PATCH_0003="${ROOT_DIR}/.src/.patches/0003-arm-apple-sysreg-framework.patch"
PATCH_0004="${ROOT_DIR}/.src/.patches/0004-arm-apple-sysreg-policy-model.patch"
P2_01_TOOL="${ROOT_DIR}/.src/.tools/cpu-contract.py"
P2_01_CONTRACT="${ROOT_DIR}/.src/.configs/p2.01-cpu-contract.json"
P2_03_POLICY="${ROOT_DIR}/.src/.configs/p2.03-sysreg-policy.json"
WORK_ROOT="${APPLESILICON_P2_03_WORK_ROOT:-${ROOT_DIR}/.build/p2.03}"
PREPARED_SOURCE="${WORK_ROOT}/inferno-src"
LOG_DIR="${APPLESILICON_LOG_DIR:-${ROOT_DIR}/.logs}"
CLASSIFICATION="UNCLASSIFIED"
FINAL_STAGE="startup"

mkdir -p "${LOG_DIR}"
TIMESTAMP="$(date -u +"%Y%m%d-%H%M%S")"
LOG_FILE="${LOG_DIR}/AppleSilicon-p2.03-${TIMESTAMP}-$$.log"

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
)" || fail "P2_03_UNSAFE_WORK_ROOT" "Could not canonicalize P2.03 work root: ${WORK_ROOT}"
    normalized_build_root="$(python3 - "${ROOT_DIR}/.build" <<'PY'
from pathlib import Path
import sys
print(Path(sys.argv[1]).resolve(strict=False))
PY
)" || fail "P2_03_UNSAFE_WORK_ROOT" "Could not canonicalize project build root"
    case "${normalized_root}" in
        ""|"/"|"${ROOT_DIR}"|"${HOME}"|"${normalized_build_root}")
            fail "P2_03_UNSAFE_WORK_ROOT" "Refusing unsafe work-root reset: ${WORK_ROOT}"
            ;;
    esac
    [[ "${normalized_root}" == "${normalized_build_root}/"* ]] || \
        fail "P2_03_UNSAFE_WORK_ROOT" "Work root must remain below ${normalized_build_root}"
    WORK_ROOT="${normalized_root}"
    PREPARED_SOURCE="${WORK_ROOT}/inferno-src"
    rm -rf -- "${WORK_ROOT}"
    mkdir -p "${WORK_ROOT}"
}

echo "AppleSilicon version: ${VERSION}"
echo "Objective: P2.03"
echo "Started UTC: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
echo "Host OS: $(uname -s 2>/dev/null || echo unknown)"
echo "Host architecture: $(uname -m 2>/dev/null || echo unknown)"
echo "Inferno source: ${SOURCE_DIR}"
echo "Expected Inferno revision: ${EXPECTED_INFERNO_REVISION}"
echo "P2.03 policy contract: ${P2_03_POLICY}"
echo "Prepared source: ${PREPARED_SOURCE}"

FINAL_STAGE="tool-preflight"
for command in git grep python3; do
    command -v "${command}" >/dev/null 2>&1 || \
        fail "P2_03_TOOL_MISSING" "Missing required command: ${command}"
done

FINAL_STAGE="p2.01-contract-validation"
[[ -f "${P2_01_TOOL}" ]] || fail "P2_01_TOOL_MISSING" "Missing P2.01 validator: ${P2_01_TOOL}"
[[ -f "${P2_01_CONTRACT}" ]] || fail "P2_01_CONTRACT_MISSING" "Missing P2.01 contract: ${P2_01_CONTRACT}"
python3 "${P2_01_TOOL}" validate --contract "${P2_01_CONTRACT}"

FINAL_STAGE="p2.03-policy-validation"
[[ -f "${P2_03_POLICY}" ]] || fail "P2_03_POLICY_MISSING" "Missing P2.03 policy contract: ${P2_03_POLICY}"
python3 - "${P2_01_CONTRACT}" "${P2_03_POLICY}" "${VERSION}" <<'PY'
import json
import pathlib
import sys

contract = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
policy = json.loads(pathlib.Path(sys.argv[2]).read_text(encoding="utf-8"))
version = sys.argv[3]

if policy.get("schema") != 1:
    raise SystemExit("P2.03 policy schema must be 1")
if policy.get("project_version") != version:
    raise SystemExit("P2.03 project_version mismatch")
if policy.get("objective") != "P2.03":
    raise SystemExit("P2.03 objective mismatch")
if policy.get("next_objective") != "P2.04":
    raise SystemExit("P2.03 must point to P2.04")

scope = policy.get("cpu_scope", {})
expected_scope = {
    "enabled_cpu": "apple-gxf",
    "accelerator": "tcg",
    "control_cpu": "max",
    "control_cpu_must_remain_untouched": True,
}
for key, expected in expected_scope.items():
    if scope.get(key) != expected:
        raise SystemExit(f"P2.03 cpu_scope mismatch for {key}")

expected_kinds = {
    "read": ["undefined", "stored", "zero", "constant", "callback"],
    "write": ["undefined", "store", "ignore", "callback"],
    "reset": ["none", "value", "callback"],
    "access": ["allow", "undefined", "trap_el1", "trap_el2", "trap_el3", "callback"],
}
if policy.get("policy_kinds") != expected_kinds:
    raise SystemExit("P2.03 policy kind set changed unexpectedly")

requirements = policy.get("policy_requirements", {})
for key in (
    "evidence_required",
    "scope_required",
    "unknown_read_must_undef",
    "unknown_write_must_undef",
    "duplicate_encodings_forbidden",
    "stored_state_requires_explicit_field",
    "stored_state_requires_explicit_reset_policy",
    "constant_read_requires_write_ignore",
    "callback_kind_requires_callback",
    "non_callback_kind_forbids_dormant_callback",
):
    if requirements.get(key) is not True:
        raise SystemExit(f"P2.03 requirement must be true: {key}")

mapping = policy.get("qemu_mapping", {})
expected_mapping = {
    "undefined": "CP_ACCESS_UNDEFINED",
    "read_zero": "arm_cp_read_zero",
    "write_ignore": "arm_cp_write_ignore",
    "constant": "ARM_CP_CONST",
    "stored_state": "ARMCPRegInfo.fieldoffset",
    "reset_value": "ARMCPRegInfo.resetvalue",
    "reset_none_with_state": "arm_cp_reset_ignore",
    "policy_opaque": "define_one_arm_cp_reg_with_opaque",
    "gdb_exposed": False,
}
if mapping != expected_mapping:
    raise SystemExit("P2.03 QEMU mapping changed unexpectedly")

if policy.get("live_policy_count") != 0:
    raise SystemExit("P2.03 must not invent live register policies")
if policy.get("live_policies") != []:
    raise SystemExit("P2.03 live_policies must remain empty without promoted evidence")

registers = contract.get("registers", [])
if not registers:
    raise SystemExit("P2.01 register inventory is unexpectedly empty")
for entry in registers:
    if entry.get("runtime_priority") != "unknown":
        raise SystemExit(f"P2.01 runtime priority unexpectedly promoted: {entry.get('name')}")
    if entry.get("implementation_state") != "inventory_only":
        raise SystemExit(f"P2.01 implementation state unexpectedly promoted: {entry.get('name')}")

print("P2.03 policy contract: PASS")
print("P2.01 no-promotion invariant: PASS")
print("P2.03 live policy count: 0")
PY

FINAL_STAGE="source-validation"
[[ -d "${SOURCE_DIR}" ]] || fail "SOURCE_UNAVAILABLE" "Inferno source directory does not exist: ${SOURCE_DIR}"
git -C "${SOURCE_DIR}" rev-parse --is-inside-work-tree >/dev/null 2>&1 || \
    fail "SOURCE_INVALID" "Inferno source path is not a Git work tree"
OBSERVED_REVISION="$(git -C "${SOURCE_DIR}" rev-parse HEAD)"
[[ "${OBSERVED_REVISION}" == "${EXPECTED_INFERNO_REVISION}" ]] || \
    fail "SOURCE_REVISION_MISMATCH" "Expected ${EXPECTED_INFERNO_REVISION}; observed ${OBSERVED_REVISION}"
[[ -z "$(git -C "${SOURCE_DIR}" status --porcelain --untracked-files=no)" ]] || \
    fail "SOURCE_DIRTY" "Pinned Inferno source contains tracked modifications"

CPREGS="${SOURCE_DIR}/target/arm/cpregs.h"
[[ -f "${CPREGS}" ]] || fail "CPREG_API_MISSING" "Missing pinned QEMU cpreg header"
for symbol in \
    'CP_ACCESS_UNDEFINED' \
    'CP_ACCESS_TRAP_EL1' \
    'ARM_CP_CONST' \
    'arm_cp_read_zero' \
    'arm_cp_write_ignore' \
    'arm_cp_reset_ignore' \
    'fieldoffset' \
    'resetvalue' \
    'define_one_arm_cp_reg_with_opaque'; do
    grep -Fq "${symbol}" "${CPREGS}" || \
        fail "CPREG_POLICY_API_MISSING" "Pinned cpreg API lacks required P2.03 symbol: ${symbol}"
done

for patch in "${PATCH_0001}" "${PATCH_0002}" "${PATCH_0003}" "${PATCH_0004}"; do
    [[ -f "${patch}" ]] || fail "PATCH_MISSING" "Required patch is missing: ${patch}"
done

FINAL_STAGE="work-root-reset"
safe_reset_work_root

FINAL_STAGE="source-clone"
git clone --quiet --no-hardlinks "${SOURCE_DIR}" "${PREPARED_SOURCE}"
git -C "${PREPARED_SOURCE}" checkout --quiet --detach "${EXPECTED_INFERNO_REVISION}"

FINAL_STAGE="patch-series"
for patch in "${PATCH_0001}" "${PATCH_0002}" "${PATCH_0003}" "${PATCH_0004}"; do
    git -C "${PREPARED_SOURCE}" apply --check "${patch}" || \
        fail "PATCH_CHECK_FAILED" "Patch does not apply cleanly: ${patch}"
    git -C "${PREPARED_SOURCE}" apply "${patch}" || \
        fail "PATCH_APPLY_FAILED" "Patch failed to apply: ${patch}"
done

FRAMEWORK_C="${PREPARED_SOURCE}/target/arm/apple-sysregs.c"
FRAMEWORK_H="${PREPARED_SOURCE}/target/arm/apple-sysregs.h"

FINAL_STAGE="policy-model-structure"
for symbol in \
    'AppleSysRegReadPolicy' \
    'AppleSysRegWritePolicy' \
    'AppleSysRegResetPolicy' \
    'AppleSysRegAccessPolicy' \
    'AppleSysRegPolicy' \
    'apple_sysreg_register_policy' \
    'apple_sysreg_register_policies'; do
    grep -Fq "${symbol}" "${FRAMEWORK_H}" || \
        fail "POLICY_HEADER_SYMBOL_MISSING" "P2.03 header lacks: ${symbol}"
done

for symbol in \
    'apple_sysreg_validate_policy' \
    'define_one_arm_cp_reg_with_opaque' \
    'arm_cp_read_zero' \
    'arm_cp_write_ignore' \
    'arm_cp_reset_ignore' \
    'ARM_CP_CONST' \
    '.fieldoffset =' \
    '.resetvalue =' \
    'CP_ACCESS_TRAP_EL1' \
    'CP_ACCESS_TRAP_EL2' \
    'CP_ACCESS_TRAP_EL3'; do
    grep -Fq "${symbol}" "${FRAMEWORK_C}" || \
        fail "POLICY_IMPLEMENTATION_MISSING" "P2.03 implementation lacks: ${symbol}"
done

FINAL_STAGE="evidence-and-fail-closed-validation"
grep -Fq 'g_assert(apple_sysreg_has_text(policy->evidence));' "${FRAMEWORK_C}" || \
    fail "EVIDENCE_REQUIRED_MISSING" "Policy registration does not require evidence metadata"
grep -Fq 'g_assert(apple_sysreg_has_text(policy->scope));' "${FRAMEWORK_C}" || \
    fail "SCOPE_REQUIRED_MISSING" "Policy registration does not require scope metadata"
grep -Fq 'return apple_sysreg_undefined_access(env, ri, true);' "${FRAMEWORK_C}" || \
    fail "READ_FAIL_CLOSED_MISSING" "Unknown read no longer fails closed"
grep -Fq 'return apple_sysreg_undefined_access(env, ri, false);' "${FRAMEWORK_C}" || \
    fail "WRITE_FAIL_CLOSED_MISSING" "Unknown write no longer fails closed"
grep -Fq 'apple_sysreg_same_encoding' "${FRAMEWORK_C}" || \
    fail "DUPLICATE_ENCODING_GUARD_MISSING" "Policy table lacks duplicate encoding validation"

FINAL_STAGE="live-policy-zero"
python3 - "${FRAMEWORK_C}" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
if "static const size_t live_policy_count = 0;" not in text:
    raise SystemExit("P2.03 live policy count is not explicitly zero")
if "static const AppleSysRegPolicy *const live_policies = NULL;" not in text:
    raise SystemExit("P2.03 live policy table is not explicitly empty")
if "apple_sysreg_register_policies(cpu, live_policies, live_policy_count);" not in text:
    raise SystemExit("P2.03 framework does not route live policies through the policy table")
print("Live policy table: empty")
print("Default guest-visible semantic policy count: 0")
PY

FINAL_STAGE="p2.02-regression"
grep -Fq 'return CP_ACCESS_UNDEFINED;' "${FRAMEWORK_C}" || \
    fail "P2_02_FAIL_CLOSED_REGRESSION" "P2.02 explicit undefined helper was lost"
grep -Fq 'define_one_arm_cp_reg(cpu, &ri);' "${FRAMEWORK_C}" || \
    fail "P2_02_BRIDGE_REGRESSION" "P2.02 explicit undefined registration bridge was lost"

FINAL_STAGE="patch-integrity"
git -C "${PREPARED_SOURCE}" diff --check || \
    fail "PATCH_DIFF_CHECK_FAILED" "Patched source fails git diff --check"

echo "Policy enums and data model: PASS"
echo "Evidence/scope enforcement: PASS"
echo "QEMU cpreg policy mapping: PASS"
echo "Fail-closed unknown behavior: PASS"
echo "Duplicate encoding guard: PASS"
echo "Live semantic policy count: 0"
echo "No QEMU/macOS/HVF/TCG guest or m1n1 runtime was launched."

CLASSIFICATION="P2_03_PREPARATION_PASS"
FINAL_STAGE="complete"
echo "P2.03 preparation: PASS"

#!/usr/bin/env bash
set -Eeuo pipefail

VERSION="2.3.0.0.0.0"
EXPECTED_INFERNO_REVISION="cc4302a99167abec69b714cfd00c38caece7e7de"
EXPECTED_XNU_REVISION="f6217f891ac0bb64f3d375211650a4c1ff8ca1ea"
EXPECTED_XNU_VMAPPLE_BLOB="08b35780a1dcf187af2ced7839d7045afb433de7"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SOURCE_DIR="${APPLESILICON_INFERNO_SOURCE:-${ROOT_DIR}/.src/.upstream/.inferno}"
P2_01_TOOL="${ROOT_DIR}/.src/.tools/cpu-contract.py"
P2_01_CONTRACT="${ROOT_DIR}/.src/.configs/p2.01-cpu-contract.json"
P2_03_POLICY="${ROOT_DIR}/.src/.configs/p2.03-sysreg-policy.json"
P2_04_CONTRACT="${ROOT_DIR}/.src/.configs/p2.04-feature-contract.json"
WORK_ROOT="${APPLESILICON_P2_04_WORK_ROOT:-${ROOT_DIR}/.build/p2.04}"
PREPARED_SOURCE="${WORK_ROOT}/inferno-src"
LOG_DIR="${APPLESILICON_LOG_DIR:-${ROOT_DIR}/.logs}"
CLASSIFICATION="UNCLASSIFIED"
FINAL_STAGE="startup"

PATCHES=(
    "${ROOT_DIR}/.src/.patches/0001-vmapple-decouple-build-from-hvf.patch"
    "${ROOT_DIR}/.src/.patches/0002-vmapple-optional-apple-pvg.patch"
    "${ROOT_DIR}/.src/.patches/0003-arm-apple-sysreg-framework.patch"
    "${ROOT_DIR}/.src/.patches/0004-arm-apple-sysreg-policy-model.patch"
    "${ROOT_DIR}/.src/.patches/0005-arm-vmapple-feature-contract.patch"
)

mkdir -p "${LOG_DIR}"
TIMESTAMP="$(date -u +"%Y%m%d-%H%M%S")"
LOG_FILE="${LOG_DIR}/AppleSilicon-p2.04-${TIMESTAMP}-$$.log"
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
            fail "P2_04_UNSAFE_WORK_ROOT" "Refusing unsafe work-root reset: ${WORK_ROOT}"
            ;;
    esac
    [[ "${WORK_ROOT}" == "${ROOT_DIR}/.build/"* ]] ||
        fail "P2_04_UNSAFE_WORK_ROOT" "Work root must remain below ${ROOT_DIR}/.build"
    rm -rf "${WORK_ROOT}"
    mkdir -p "${WORK_ROOT}"
}

echo "AppleSilicon version: ${VERSION}"
echo "Objective: P2.04"
echo "Started UTC: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
echo "Host OS: $(uname -s 2>/dev/null || echo unknown)"
echo "Host architecture: $(uname -m 2>/dev/null || echo unknown)"
echo "Inferno source: ${SOURCE_DIR}"
echo "Expected Inferno revision: ${EXPECTED_INFERNO_REVISION}"
echo "P2.04 contract: ${P2_04_CONTRACT}"

FINAL_STAGE="tool-preflight"
for command in git grep python3; do
    command -v "${command}" >/dev/null 2>&1 ||
        fail "P2_04_TOOL_MISSING" "Missing required command: ${command}"
done

FINAL_STAGE="contract-validation"
[[ -f "${P2_01_TOOL}" ]] || fail "P2_01_TOOL_MISSING" "Missing P2.01 validator"
[[ -f "${P2_01_CONTRACT}" ]] || fail "P2_01_CONTRACT_MISSING" "Missing P2.01 contract"
[[ -f "${P2_03_POLICY}" ]] || fail "P2_03_POLICY_MISSING" "Missing P2.03 policy contract"
[[ -f "${P2_04_CONTRACT}" ]] || fail "P2_04_CONTRACT_MISSING" "Missing P2.04 feature contract"
python3 "${P2_01_TOOL}" validate --contract "${P2_01_CONTRACT}"

python3 - "${P2_04_CONTRACT}" "${VERSION}" "${EXPECTED_INFERNO_REVISION}" "${EXPECTED_XNU_REVISION}" "${EXPECTED_XNU_VMAPPLE_BLOB}" <<'PY'
import json
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
version, inferno_rev, xnu_rev, xnu_blob = sys.argv[2:]
data = json.loads(path.read_text(encoding="utf-8"))

if data.get("schema") != 1:
    raise SystemExit("P2.04 schema must be 1")
if data.get("project_version") != version:
    raise SystemExit("P2.04 project_version mismatch")
if data.get("objective") != "P2.04":
    raise SystemExit("P2.04 objective mismatch")
if data.get("next_objective") != "P2.05":
    raise SystemExit("P2.04 must point to P2.05")

expected_scope = {
    "cpu": "apple-gxf",
    "accelerator": "tcg",
    "base_cpu": "max",
    "policy": "minimum_required_preserve_stronger",
}
scope = data.get("scope", {})
for key, expected in expected_scope.items():
    if scope.get(key) != expected:
        raise SystemExit(f"P2.04 scope mismatch: {key}")

locks = data.get("source_locks", {})
if locks.get("inferno", {}).get("revision") != inferno_rev:
    raise SystemExit("P2.04 Inferno source lock mismatch")
xnu = locks.get("xnu_vmapple", {})
if xnu.get("revision") != xnu_rev or xnu.get("blob_sha") != xnu_blob:
    raise SystemExit("P2.04 XNU VMAPPLE source lock mismatch")

expected_ids = ["pauth", "ssbs2", "sme", "sme2", "pan3", "tgran16", "tgran4", "tlbirange"]
requirements = data.get("requirements", [])
if [item.get("id") for item in requirements] != expected_ids:
    raise SystemExit("P2.04 requirement set/order mismatch")
if any(item.get("status") != "enforced" for item in requirements):
    raise SystemExit("Every P2.04 architectural requirement must be enforced")

for key in (
    "do_not_modify_max_cpu",
    "do_not_modify_host_hvf_or_kvm",
    "do_not_mask_stronger_supported_features",
    "do_not_claim_paravirtualized_pac_complete",
    "sysreg_semantics_remain_owned_by_p2_03",
    "guest_runtime_deferred",
):
    if data.get("rules", {}).get(key) is not True:
        raise SystemExit(f"P2.04 safety rule must be true: {key}")

expected_deferred = {
    "HAS_PARAVIRTUALIZED_PAC",
    "HAS_PARAVIRTUALIZED_CTRR",
    "HAS_GIC_V3",
    "NO_ECORE",
    "ARM_PARAMETERIZED_PMAP",
}
deferred = {item.get("xnu_macro") for item in data.get("deferred_non_id_contracts", [])}
if deferred != expected_deferred:
    raise SystemExit("P2.04 deferred non-ID contract set mismatch")

print("P2.04 machine-readable feature contract: PASS")
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

CPU_FEATURES="${SOURCE_DIR}/target/arm/cpu-features.h"
MAX_TCG="${SOURCE_DIR}/target/arm/tcg/cpu64.c"
for source_file in "${CPU_FEATURES}" "${MAX_TCG}"; do
    [[ -f "${source_file}" ]] || fail "SOURCE_FILE_MISSING" "Missing pinned source: ${source_file}"
done

FINAL_STAGE="emulator-capability-validation"
for symbol in \
    isar_feature_aa64_pauth \
    isar_feature_aa64_sme \
    isar_feature_aa64_sme2 \
    isar_feature_aa64_pan3 \
    isar_feature_aa64_tgran4 \
    isar_feature_aa64_tgran16 \
    isar_feature_aa64_tlbirange; do
    grep -Fq "${symbol}" "${CPU_FEATURES}" ||
        fail "FEATURE_TEST_MISSING" "Pinned Inferno lacks feature test: ${symbol}"
done

for required_line in \
    'ID_AA64ISAR0, TLB, 2' \
    'ID_AA64PFR1, SSBS, 2' \
    'ID_AA64PFR1, SME, 2' \
    'ID_AA64MMFR0, TGRAN16, 1' \
    'ID_AA64MMFR1, PAN, 3' \
    'ID_AA64SMFR0, SMEVER, 2'; do
    grep -Fq "${required_line}" "${MAX_TCG}" ||
        fail "MAX_FEATURE_BASELINE_MISSING" "Pinned max CPU lacks expected TCG capability: ${required_line}"
done

for patch in "${PATCHES[@]}"; do
    [[ -f "${patch}" ]] || fail "PATCH_MISSING" "Required patch is missing: ${patch}"
done

FINAL_STAGE="work-root-reset"
safe_reset_work_root

FINAL_STAGE="source-clone"
git clone --quiet --no-hardlinks "${SOURCE_DIR}" "${PREPARED_SOURCE}"
git -C "${PREPARED_SOURCE}" checkout --quiet --detach "${EXPECTED_INFERNO_REVISION}"

FINAL_STAGE="patch-series"
for patch in "${PATCHES[@]}"; do
    git -C "${PREPARED_SOURCE}" apply --check "${patch}" ||
        fail "PATCH_CHECK_FAILED" "Patch does not apply cleanly: ${patch}"
    git -C "${PREPARED_SOURCE}" apply "${patch}" ||
        fail "PATCH_APPLY_FAILED" "Patch failed to apply: ${patch}"
done

FEATURE_C="${PREPARED_SOURCE}/target/arm/apple-cpu-features.c"
FEATURE_H="${PREPARED_SOURCE}/target/arm/apple-cpu-features.h"
CPU64="${PREPARED_SOURCE}/target/arm/cpu64.c"
MESON="${PREPARED_SOURCE}/target/arm/meson.build"
SYSREG_C="${PREPARED_SOURCE}/target/arm/apple-sysregs.c"

FINAL_STAGE="feature-profile-structure"
[[ -f "${FEATURE_C}" ]] || fail "FEATURE_SOURCE_MISSING" "apple-cpu-features.c was not created"
[[ -f "${FEATURE_H}" ]] || fail "FEATURE_HEADER_MISSING" "apple-cpu-features.h was not created"
grep -Fq "'apple-cpu-features.c'" "${MESON}" ||
    fail "FEATURE_BUILD_WIRING_MISSING" "Meson does not compile apple-cpu-features.c"
grep -Fq '#include "apple-cpu-features.h"' "${CPU64}" ||
    fail "FEATURE_CPU_INCLUDE_MISSING" "cpu64.c does not include apple-cpu-features.h"

python3 - "${CPU64}" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
max_start = text.index("static void aarch64_max_initfn(Object *obj)")
apple_start = text.index("static void aarch64_apple_gxf_initfn(Object *obj)")
max_body = text[max_start:apple_start]
apple_body = text[apple_start:]

if "apple_cpu_feature_profile_init" in max_body:
    raise SystemExit("max control CPU was contaminated by the VMApple feature profile")

needle = """if (tcg_enabled()) {
        object_property_set_bool(obj, "pauth-noop", true, NULL);
        apple_cpu_feature_profile_init(cpu);
        apple_sysreg_framework_init(cpu);
    }"""
if needle not in apple_body:
    raise SystemExit("VMApple feature profile is not scoped to the TCG apple-gxf block")

print("TCG-only apple-gxf feature wiring: PASS")
print("max control CPU isolation: PASS")
PY

FINAL_STAGE="feature-profile-semantics"
for required_line in \
    'ID_AA64PFR1, SSBS, 2' \
    'ID_AA64PFR1, SME, 2' \
    'ID_AA64SMFR0, SMEVER, 1' \
    'ID_AA64MMFR1, PAN, 3' \
    'ID_AA64MMFR0, TGRAN4, 0' \
    'ID_AA64MMFR0, TGRAN16, 1' \
    'ID_AA64ISAR0, TLB, 2'; do
    grep -Fq "${required_line}" "${FEATURE_C}" ||
        fail "FEATURE_REQUIREMENT_MISSING" "Feature profile does not enforce: ${required_line}"
done

for required_test in \
    'cpu_isar_feature(aa64_pauth, cpu)' \
    'cpu_isar_feature(aa64_sme, cpu)' \
    'cpu_isar_feature(aa64_sme2, cpu)' \
    'cpu_isar_feature(aa64_pan3, cpu)' \
    'cpu_isar_feature(aa64_tgran4, cpu)' \
    'cpu_isar_feature(aa64_tgran16, cpu)' \
    'cpu_isar_feature(aa64_tlbirange, cpu)'; do
    grep -Fq "${required_test}" "${FEATURE_C}" ||
        fail "FEATURE_POSTCONDITION_MISSING" "Feature profile lacks postcondition: ${required_test}"
done

if grep -Fq 'PauthFeat_' "${FEATURE_C}"; then
    fail "PAUTH_POLICY_LEAK" "P2.04 must not invent a PAuth algorithm"
fi
grep -Fq 'live_policy_count = 0' "${SYSREG_C}" ||
    fail "P2_03_POLICY_DRIFT" "P2.04 must not add Apple implementation-defined sysreg semantics"

FINAL_STAGE="patch-integrity"
git -C "${PREPARED_SOURCE}" diff --check ||
    fail "PATCH_DIFF_CHECK_FAILED" "Patched source fails git diff --check"

echo "XNU VMAPPLE architectural contract: PASS"
echo "Pinned TCG max capability baseline: PASS"
echo "apple-gxf minimum feature profile: PASS"
echo "P2.03 live Apple sysreg policy count remains 0."
echo "No QEMU/macOS/HVF/TCG guest or m1n1 runtime was launched."

CLASSIFICATION="P2_04_PREPARATION_PASS"
FINAL_STAGE="complete"
echo "P2.04 preparation: PASS"

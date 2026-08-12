#!/usr/bin/env bash

set -Eeuo pipefail

VERSION="2.1.0.0.0.0"
EXPECTED_INFERNO_REVISION="cc4302a99167abec69b714cfd00c38caece7e7de"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SOURCE_DIR="${APPLESILICON_INFERNO_SOURCE:-${ROOT_DIR}/.src/.upstream/.inferno}"
PATCH_0001="${ROOT_DIR}/.src/.patches/0001-vmapple-decouple-build-from-hvf.patch"
PATCH_0002="${ROOT_DIR}/.src/.patches/0002-vmapple-optional-apple-pvg.patch"
PATCH_0003="${ROOT_DIR}/.src/.patches/0003-arm-apple-sysreg-framework.patch"
P2_01_TOOL="${ROOT_DIR}/.src/.tools/cpu-contract.py"
P2_01_CONTRACT="${ROOT_DIR}/.src/.configs/p2.01-cpu-contract.json"
P2_02_POLICY="${ROOT_DIR}/.src/.configs/p2.02-framework-policy.json"
WORK_ROOT="${APPLESILICON_P2_02_WORK_ROOT:-${ROOT_DIR}/.build/p2.02}"
PREPARED_SOURCE="${WORK_ROOT}/inferno-src"
LOG_DIR="${APPLESILICON_LOG_DIR:-${ROOT_DIR}/.logs}"
CLASSIFICATION="UNCLASSIFIED"
FINAL_STAGE="startup"

mkdir -p "${LOG_DIR}"
TIMESTAMP="$(date -u +"%Y%m%d-%H%M%S")"
LOG_FILE="${LOG_DIR}/AppleSilicon-p2.02-${TIMESTAMP}-$$.log"

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
)" || fail "P2_02_UNSAFE_WORK_ROOT" "Could not canonicalize P2.02 work root: ${WORK_ROOT}"
    normalized_build_root="$(python3 - "${ROOT_DIR}/.build" <<'PY'
from pathlib import Path
import sys
print(Path(sys.argv[1]).resolve(strict=False))
PY
)" || fail "P2_02_UNSAFE_WORK_ROOT" "Could not canonicalize project build root"
    case "${normalized_root}" in
        ""|"/"|"${ROOT_DIR}"|"${HOME}"|"${normalized_build_root}")
            fail "P2_02_UNSAFE_WORK_ROOT" "Refusing unsafe work-root reset: ${WORK_ROOT}"
            ;;
    esac
    [[ "${normalized_root}" == "${normalized_build_root}/"* ]] || \
        fail "P2_02_UNSAFE_WORK_ROOT" "Work root must remain below ${normalized_build_root}"
    WORK_ROOT="${normalized_root}"
    PREPARED_SOURCE="${WORK_ROOT}/inferno-src"
    rm -rf -- "${WORK_ROOT}"
    mkdir -p "${WORK_ROOT}"
}

echo "AppleSilicon version: ${VERSION}"
echo "Objective: P2.02"
echo "Started UTC: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
echo "Host OS: $(uname -s 2>/dev/null || echo unknown)"
echo "Host architecture: $(uname -m 2>/dev/null || echo unknown)"
echo "Inferno source: ${SOURCE_DIR}"
echo "Expected Inferno revision: ${EXPECTED_INFERNO_REVISION}"
echo "P2.02 policy: ${P2_02_POLICY}"
echo "Prepared source: ${PREPARED_SOURCE}"

FINAL_STAGE="tool-preflight"
for command in git grep python3; do
    command -v "${command}" >/dev/null 2>&1 || \
        fail "P2_02_TOOL_MISSING" "Missing required command: ${command}"
done

FINAL_STAGE="p2.01-contract-validation"
[[ -f "${P2_01_TOOL}" ]] || fail "P2_01_TOOL_MISSING" "Missing P2.01 validator: ${P2_01_TOOL}"
[[ -f "${P2_01_CONTRACT}" ]] || fail "P2_01_CONTRACT_MISSING" "Missing P2.01 contract: ${P2_01_CONTRACT}"
python3 "${P2_01_TOOL}" validate --contract "${P2_01_CONTRACT}"

FINAL_STAGE="p2.02-policy-validation"
[[ -f "${P2_02_POLICY}" ]] || fail "P2_02_POLICY_MISSING" "Missing P2.02 framework policy: ${P2_02_POLICY}"
python3 - "${P2_01_CONTRACT}" "${P2_02_POLICY}" "${VERSION}" <<'PY'
import json
import pathlib
import sys

contract_path = pathlib.Path(sys.argv[1])
policy_path = pathlib.Path(sys.argv[2])
version = sys.argv[3]

contract = json.loads(contract_path.read_text(encoding="utf-8"))
policy = json.loads(policy_path.read_text(encoding="utf-8"))

if policy.get("schema") != 1:
    raise SystemExit("P2.02 policy schema must be 1")
if policy.get("project_version") != version:
    raise SystemExit("P2.02 policy project_version mismatch")
if policy.get("objective") != "P2.02":
    raise SystemExit("P2.02 policy objective mismatch")
if policy.get("next_objective") != "P2.03":
    raise SystemExit("P2.02 policy must point to P2.03")

scope = policy.get("cpu_scope", {})
expected_scope = {
    "enabled_cpu": "apple-gxf",
    "accelerator": "tcg",
    "control_cpu": "max",
    "control_cpu_must_remain_untouched": True,
}
for key, expected in expected_scope.items():
    if scope.get(key) != expected:
        raise SystemExit(f"P2.02 cpu_scope mismatch for {key}")

unresolved = policy.get("unresolved_policy", {})
if unresolved.get("qemu_access_result") != "CP_ACCESS_UNDEFINED":
    raise SystemExit("P2.02 unresolved policy must use CP_ACCESS_UNDEFINED")
for key in (
    "gdb_exposed",
    "migration_state",
    "invent_read_values",
    "invent_write_side_effects",
    "invent_reset_values",
):
    if unresolved.get(key) is not False:
        raise SystemExit(f"P2.02 unresolved policy must keep {key}=false")

registers = {entry["name"]: entry for entry in contract.get("registers", [])}
representatives = policy.get("representative_registers")
if not isinstance(representatives, list) or len(representatives) != 6:
    raise SystemExit("P2.02 policy must contain exactly six validation representatives")

seen_groups = set()
for item in representatives:
    name = item.get("name")
    source = registers.get(name)
    if source is None:
        raise SystemExit(f"P2.02 representative missing from P2.01: {name}")
    if source.get("group") != item.get("group"):
        raise SystemExit(f"P2.02 group mismatch for {name}")
    if source.get("architectural_name") != item.get("architectural_name"):
        raise SystemExit(f"P2.02 encoding mismatch for {name}")
    if source.get("runtime_priority") != "unknown":
        raise SystemExit(f"P2.01 representative priority changed unexpectedly: {name}")
    if source.get("implementation_state") != "inventory_only":
        raise SystemExit(f"P2.01 representative implementation state changed unexpectedly: {name}")
    seen_groups.add(item.get("group"))

expected_groups = {
    "hid_ehid",
    "timer",
    "amx",
    "gxf_sprr",
    "pauth_control",
    "control_hypervisor",
}
if seen_groups != expected_groups:
    raise SystemExit("P2.02 representatives do not cover the six P2.01 register groups")

print("P2.02 framework policy: PASS")
print("Representative P2.01 encoding cross-check: PASS")
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
CPU64_SOURCE="${SOURCE_DIR}/target/arm/cpu64.c"
[[ -f "${CPREGS}" ]] || fail "CPREG_API_MISSING" "Missing pinned QEMU cpreg header"
[[ -f "${CPU64_SOURCE}" ]] || fail "CPU64_SOURCE_MISSING" "Missing pinned AArch64 CPU source"
grep -Fq 'CP_ACCESS_UNDEFINED' "${CPREGS}" || fail "CPREG_UNDEFINED_RESULT_MISSING" "Pinned cpreg API lacks CP_ACCESS_UNDEFINED"
grep -Fq 'define_one_arm_cp_reg(ARMCPU *cpu' "${CPREGS}" || fail "CPREG_REGISTER_API_MISSING" "Pinned cpreg API lacks define_one_arm_cp_reg"
grep -Fq 'static void aarch64_apple_gxf_initfn(Object *obj)' "${CPU64_SOURCE}" || fail "APPLE_GXF_INIT_MISSING" "Pinned Inferno no longer contains apple-gxf initializer"
grep -Fq '{ .name = "max",' "${CPU64_SOURCE}" || fail "MAX_CONTROL_CPU_MISSING" "Pinned Inferno no longer contains max control CPU"

for patch in "${PATCH_0001}" "${PATCH_0002}" "${PATCH_0003}"; do
    [[ -f "${patch}" ]] || fail "PATCH_MISSING" "Required patch is missing: ${patch}"
done

FINAL_STAGE="work-root-reset"
safe_reset_work_root

FINAL_STAGE="source-clone"
git clone --quiet --no-hardlinks "${SOURCE_DIR}" "${PREPARED_SOURCE}"
git -C "${PREPARED_SOURCE}" checkout --quiet --detach "${EXPECTED_INFERNO_REVISION}"

FINAL_STAGE="patch-series"
for patch in "${PATCH_0001}" "${PATCH_0002}" "${PATCH_0003}"; do
    git -C "${PREPARED_SOURCE}" apply --check "${patch}" || \
        fail "PATCH_CHECK_FAILED" "Patch does not apply cleanly: ${patch}"
    git -C "${PREPARED_SOURCE}" apply "${patch}" || \
        fail "PATCH_APPLY_FAILED" "Patch failed to apply: ${patch}"
done

FRAMEWORK_C="${PREPARED_SOURCE}/target/arm/apple-sysregs.c"
FRAMEWORK_H="${PREPARED_SOURCE}/target/arm/apple-sysregs.h"
CPU64="${PREPARED_SOURCE}/target/arm/cpu64.c"
MESON="${PREPARED_SOURCE}/target/arm/meson.build"

FINAL_STAGE="framework-structure"
[[ -f "${FRAMEWORK_C}" ]] || fail "FRAMEWORK_SOURCE_MISSING" "apple-sysregs.c was not created"
[[ -f "${FRAMEWORK_H}" ]] || fail "FRAMEWORK_HEADER_MISSING" "apple-sysregs.h was not created"
grep -Fq "'apple-sysregs.c'" "${MESON}" || fail "FRAMEWORK_BUILD_WIRING_MISSING" "Meson does not compile apple-sysregs.c"
grep -Fq '#include "apple-sysregs.h"' "${CPU64}" || fail "FRAMEWORK_CPU_INCLUDE_MISSING" "cpu64.c does not include apple-sysregs.h"

python3 - "${CPU64}" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
needle = '''if (tcg_enabled()) {
        object_property_set_bool(obj, "pauth-noop", true, NULL);
        apple_sysreg_framework_init(cpu);
    }'''
if needle not in text:
    raise SystemExit("apple sysreg framework is not wired inside the TCG-only apple-gxf block")

max_start = text.index("static void aarch64_max_initfn(Object *obj)")
apple_start = text.index("static void aarch64_apple_gxf_initfn(Object *obj)")
max_body = text[max_start:apple_start]
if "apple_sysreg_framework_init" in max_body:
    raise SystemExit("max control CPU was contaminated by Apple sysreg framework wiring")

print("TCG-only apple-gxf wiring: PASS")
print("max control CPU isolation: PASS")
PY

FINAL_STAGE="fail-closed-contract"
grep -Fq 'return CP_ACCESS_UNDEFINED;' "${FRAMEWORK_C}" || \
    fail "FAIL_CLOSED_ACCESS_MISSING" "Undefined Apple sysreg access does not return CP_ACCESS_UNDEFINED"
grep -Fq '.type = ARM_CP_NO_RAW | ARM_CP_NO_GDB' "${FRAMEWORK_C}" || \
    fail "FAIL_CLOSED_STATE_FLAGS_MISSING" "Undefined registrations are not excluded from raw state/GDB exposure"
grep -Fq 'define_one_arm_cp_reg(cpu, &ri);' "${FRAMEWORK_C}" || \
    fail "CPREG_BRIDGE_MISSING" "Framework does not bridge into QEMU cpreg registration"
grep -Fq 'g_assert_not_reached();' "${FRAMEWORK_C}" || \
    fail "UNREACHABLE_IO_GUARD_MISSING" "Undefined register read/write callbacks are not guarded"

for forbidden in 'arm_cp_read_zero' 'arm_cp_write_ignore' 'ARM_CP_CONST' '.resetvalue'; do
    if grep -Fq "${forbidden}" "${FRAMEWORK_C}"; then
        fail "P2_03_POLICY_LEAK" "P2.02 contains behavior reserved for P2.03: ${forbidden}"
    fi
done

python3 - "${FRAMEWORK_C}" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
start = text.index("void apple_sysreg_framework_init(ARMCPU *cpu)")
body = text[start:]
if "apple_sysreg_register_undefined(cpu" in body:
    raise SystemExit("P2.02 must not install guest-visible register policies by default")
print("Default registered policy count: 0")
PY

FINAL_STAGE="patch-integrity"
git -C "${PREPARED_SOURCE}" diff --check || fail "PATCH_DIFF_CHECK_FAILED" "Patched source fails git diff --check"

echo "Framework files: PASS"
echo "QEMU ARMCPRegInfo bridge: PASS"
echo "Fail-closed undefined path: PASS"
echo "Default guest-visible policy count: 0"
echo "No read-as-zero/write-ignore/constant/reset policy was introduced."
echo "No QEMU/macOS/HVF/TCG guest or m1n1 runtime was launched."

CLASSIFICATION="P2_02_PREPARATION_PASS"
FINAL_STAGE="complete"
echo "P2.02 preparation: PASS"

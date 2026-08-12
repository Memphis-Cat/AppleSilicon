#!/usr/bin/env bash
set -Eeuo pipefail

VERSION="3.1.0.0.0.0"
EXPECTED_INFERNO_REVISION="cc4302a99167abec69b714cfd00c38caece7e7de"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SOURCE_DIR="${APPLESILICON_INFERNO_SOURCE:-${ROOT_DIR}/.src/.upstream/.inferno}"
CONTRACT="${ROOT_DIR}/.src/.configs/p3.02-identity-contract.json"
PROFILE="${ROOT_DIR}/.src/.configs/p3.02-identity.example.json"
TOOL="${ROOT_DIR}/.src/.tools/platform-identity.py"
WORK_ROOT="${APPLESILICON_P3_02_WORK_ROOT:-${ROOT_DIR}/.build/p3.02}"
OUT_A="${WORK_ROOT}/identity-profile-a.json"
OUT_B="${WORK_ROOT}/identity-profile-b.json"
LOG_DIR="${APPLESILICON_LOG_DIR:-${ROOT_DIR}/.logs}"
CLASSIFICATION="UNCLASSIFIED"
FINAL_STAGE="startup"

mkdir -p "${LOG_DIR}"
TIMESTAMP="$(date -u +"%Y%m%d-%H%M%S")"
LOG_FILE="${LOG_DIR}/AppleSilicon-p3.02-${TIMESTAMP}-$$.log"
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
)" || fail "P3_02_UNSAFE_WORK_ROOT" "Could not canonicalize P3.02 work root: ${WORK_ROOT}"
    normalized_build_root="$(python3 - "${ROOT_DIR}/.build" <<'PY'
from pathlib import Path
import sys
print(Path(sys.argv[1]).resolve(strict=False))
PY
)" || fail "P3_02_UNSAFE_WORK_ROOT" "Could not canonicalize project build root"
    case "${normalized_root}" in
        ""|"/"|"${ROOT_DIR}"|"${HOME}"|"${normalized_build_root}")
            fail "P3_02_UNSAFE_WORK_ROOT" "Refusing unsafe work-root reset: ${WORK_ROOT}"
            ;;
    esac
    [[ "${normalized_root}" == "${normalized_build_root}/"* ]] ||
        fail "P3_02_UNSAFE_WORK_ROOT" "Work root must remain below ${normalized_build_root}"
    WORK_ROOT="${normalized_root}"
    OUT_A="${WORK_ROOT}/identity-profile-a.json"
    OUT_B="${WORK_ROOT}/identity-profile-b.json"
    rm -rf -- "${WORK_ROOT}"
    mkdir -p "${WORK_ROOT}"
}

echo "AppleSilicon version: ${VERSION}"
echo "Objective: P3.02"
echo "Started UTC: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
echo "Inferno source: ${SOURCE_DIR}"

FINAL_STAGE="tool-preflight"
for command in git python3 cmp grep; do
    command -v "${command}" >/dev/null 2>&1 ||
        fail "P3_02_TOOL_MISSING" "Missing required command: ${command}"
done
for path in "${CONTRACT}" "${PROFILE}" "${TOOL}"; do
    [[ -f "${path}" ]] || fail "P3_02_INPUT_MISSING" "Missing P3.02 input: ${path}"
done

FINAL_STAGE="syntax"
python3 - "${TOOL}" <<'PY'
from pathlib import Path
import sys
path = Path(sys.argv[1])
compile(path.read_text(encoding="utf-8"), str(path), "exec")
print("Python syntax: PASS")
PY
python3 -m json.tool "${CONTRACT}" >/dev/null
python3 -m json.tool "${PROFILE}" >/dev/null
echo "JSON syntax: PASS"

FINAL_STAGE="contract-validation"
python3 "${TOOL}" --contract "${CONTRACT}" validate-contract
python3 "${TOOL}" --contract "${CONTRACT}" validate-profile --profile "${PROFILE}"
python3 "${TOOL}" --contract "${CONTRACT}" self-check --profile "${PROFILE}"

FINAL_STAGE="source-validation"
[[ -d "${SOURCE_DIR}" ]] || fail "SOURCE_UNAVAILABLE" "Inferno source directory does not exist"
git -C "${SOURCE_DIR}" rev-parse --is-inside-work-tree >/dev/null 2>&1 ||
    fail "SOURCE_INVALID" "Inferno source is not a Git work tree"
OBSERVED_REVISION="$(git -C "${SOURCE_DIR}" rev-parse HEAD)"
[[ "${OBSERVED_REVISION}" == "${EXPECTED_INFERNO_REVISION}" ]] ||
    fail "SOURCE_REVISION_MISMATCH" "Expected ${EXPECTED_INFERNO_REVISION}; observed ${OBSERVED_REVISION}"
[[ -z "$(git -C "${SOURCE_DIR}" status --porcelain --untracked-files=no)" ]] ||
    fail "SOURCE_DIRTY" "Pinned Inferno source contains tracked modifications"

FINAL_STAGE="source-locks"
check_blob() {
    local rel="$1"
    local expected="$2"
    local observed
    observed="$(git -C "${SOURCE_DIR}" hash-object "${rel}")"
    [[ "${observed}" == "${expected}" ]] ||
        fail "P3_02_SOURCE_BLOB_DRIFT" "${rel}: expected ${expected}, observed ${observed}"
    echo "source lock: PASS: ${rel} ${observed}"
}
check_blob "hw/vmapple/cfg.c" "3d58a29f69d7b6090436afbe9609ee9370a6c115"
check_blob "hw/vmapple/vmapple.c" "89c04c09f705d987ee96c11c1f5f4fc79713bf2e"
check_blob "include/hw/vmapple/vmapple.h" "1154c10d0f4f30cb339a7ee9470578d441acbd10"

FINAL_STAGE="config-invariants"
CFG="${SOURCE_DIR}/hw/vmapple/cfg.c"
MACHINE="${SOURCE_DIR}/hw/vmapple/vmapple.c"
HEADER="${SOURCE_DIR}/include/hw/vmapple/vmapple.h"
QOPTS="${SOURCE_DIR}/qemu-options.hx"

grep -Fq '#define TYPE_VMAPPLE_CFG "vmapple-cfg"' "${HEADER}" ||
    fail "P3_02_CFG_TYPE_DRIFT" "VMApple cfg QOM type drifted"
grep -Fq 'uint32_t cpu_ids[0x80];' "${CFG}" ||
    fail "P3_02_CPU_ID_DECL_DRIFT" "cpu_ids declaration drifted"
grep -Fq 'uint8_t scratch[0x200];   /* 0x180 */' "${CFG}" ||
    fail "P3_02_LAYOUT_COMMENT_DRIFT" "scratch declaration/comment discrepancy changed"
grep -Fq 'char serial[32];          /* 0x380 */' "${CFG}" ||
    fail "P3_02_LAYOUT_COMMENT_DRIFT" "serial declaration/comment discrepancy changed"
grep -Fq 'mc->max_cpus = 32;' "${MACHINE}" ||
    fail "P3_02_MAX_CPU_DRIFT" "VMApple max CPU count drifted"
grep -Fq 'qdev_prop_set_uint64(vms->cfg, "ecid", vms->uuid);' "${MACHINE}" ||
    fail "P3_02_ECID_WIRING_DRIFT" "ECID no longer comes from VMApple machine uuid"
grep -Fq 'qdev_prop_set_uint32(vms->cfg, "nr-cpus", machine->smp.cpus);' "${MACHINE}" ||
    fail "P3_02_CPU_COUNT_WIRING_DRIFT" "config CPU count wiring drifted"
grep -Fq 'qdev_prop_set_uint64(vms->cfg, "ram-size", machine->ram_size);' "${MACHINE}" ||
    fail "P3_02_RAM_WIRING_DRIFT" "config RAM size wiring drifted"
grep -Fq 'qemu_guest_getrandom_nofail(&rnd, sizeof(rnd));' "${MACHINE}" ||
    fail "P3_02_RANDOM_WIRING_DRIFT" "config random field wiring drifted"
grep -Fq 's->cfg.cpu_ids[i] = i;' "${CFG}" ||
    fail "P3_02_CPU_ID_POLICY_DRIFT" "config CPU ID derivation drifted"
grep -Fq 'g_strdup("1234")' "${CFG}" ||
    fail "P3_02_REFERENCE_DEFAULT_DRIFT" "reference serial default drifted"
grep -Fq 'g_strdup("VM0001")' "${CFG}" ||
    fail "P3_02_REFERENCE_DEFAULT_DRIFT" "reference model default drifted"
grep -Fq 'g_strdup("Apple M1 (Virtual)")' "${CFG}" ||
    fail "P3_02_REFERENCE_DEFAULT_DRIFT" "reference SoC-name default drifted"
grep -Fq -- '-global driver.property=value' "${QOPTS}" ||
    fail "P3_02_GLOBAL_OPTION_MISSING" "QEMU global device-property option missing"

echo "Source contract invariants: PASS"
echo "Layout discrepancy preserved for evidence: cpu_ids[0x80] vs scratch comment 0x180"

FINAL_STAGE="deterministic-compile"
safe_reset_work_root
python3 "${TOOL}" --contract "${CONTRACT}" compile --profile "${PROFILE}" --output "${OUT_A}"
python3 "${TOOL}" --contract "${CONTRACT}" compile --profile "${PROFILE}" --output "${OUT_B}"
cmp -s "${OUT_A}" "${OUT_B}" ||
    fail "P3_02_NONDETERMINISTIC_COMPILE" "Compiled identity profile differs across identical runs"
echo "Deterministic compile: PASS"

FINAL_STAGE="compiled-output-validation"
python3 - "${OUT_A}" <<'PY'
import json
from pathlib import Path
import sys
data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
if data.get("classification") != "P3_02_IDENTITY_PROFILE_COMPILED":
    raise SystemExit("compiled profile classification mismatch")
if data.get("guest_execution") is not False:
    raise SystemExit("P3.02 must remain non-guest")
if data.get("machine") != "vmapple":
    raise SystemExit("compiled machine mismatch")
if data.get("layout_discrepancy_status") != "unresolved_source_layout_discrepancy":
    raise SystemExit("layout discrepancy was incorrectly resolved")
argv = data.get("qemu_argv", [])
if "-M" not in argv or not any(str(x).startswith("vmapple,uuid=") for x in argv):
    raise SystemExit("compiled VMApple uuid argument missing")
if any("nr-cpus=" in str(x) or "ram-size=" in str(x) or ".rnd=" in str(x) for x in argv):
    raise SystemExit("compiled profile attempted to override machine-derived fields")
print("Compiled output policy: PASS")
print("Compiled fingerprint:", data["compiled_fingerprint"])
PY

echo "No QEMU/macOS/HVF/TCG guest or real identity profile was launched."
echo "No real serial, ECID or MAC identity was committed or logged by this synthetic validation."
CLASSIFICATION="P3_02_PREPARATION_PASS"
FINAL_STAGE="complete"
echo "P3.02 configuration and identity preparation: PASS"

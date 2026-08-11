#!/usr/bin/env bash
set -Eeuo pipefail

VERSION="4.0.0.0.0.0"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
POLICY="${ROOT_DIR}/.src/.configs/p4.01-runtime-session-policy.json"
TOOL="${ROOT_DIR}/.src/.tools/runtime-session.py"
PLAN_WRAPPER="${ROOT_DIR}/.src/.tools/plan-p4.01-session.sh"
WORK_ROOT="${APPLESILICON_P4_01_WORK_ROOT:-${ROOT_DIR}/.build/p4.01}"
LOG_DIR="${APPLESILICON_LOG_DIR:-${ROOT_DIR}/.logs}"
SUMMARY="${WORK_ROOT}/policy-summary.json"
CLASSIFICATION="UNCLASSIFIED"
FINAL_STAGE="startup"

mkdir -p "${LOG_DIR}" "${WORK_ROOT}"
TIMESTAMP="$(date -u +"%Y%m%d-%H%M%S")"
LOG_FILE="${LOG_DIR}/AppleSilicon-p4.01-prepare-${TIMESTAMP}-$$.log"
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
echo "Objective: P4.01"
echo "Started UTC: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"

FINAL_STAGE="tool-preflight"
for command in python3 bash; do
    command -v "${command}" >/dev/null 2>&1 || fail "P4_01_TOOL_MISSING" "Missing command: ${command}"
done
for path in "${POLICY}" "${TOOL}" "${PLAN_WRAPPER}"; do
    [[ -f "${path}" ]] || fail "P4_01_INPUT_MISSING" "Missing P4.01 input: ${path}"
done

FINAL_STAGE="syntax-validation"
python3 - "${POLICY}" "${TOOL}" <<'PY'
import json
from pathlib import Path
import sys
json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
compile(Path(sys.argv[2]).read_text(encoding="utf-8"), sys.argv[2], "exec")
print("P4.01 JSON/Python syntax: PASS")
PY
bash -n "${PLAN_WRAPPER}"

FINAL_STAGE="policy-validation"
python3 "${TOOL}" --policy "${POLICY}" validate-policy

FINAL_STAGE="negative-self-checks"
python3 "${TOOL}" --policy "${POLICY}" self-check

FINAL_STAGE="patch-boundary"
if compgen -G "${ROOT_DIR}/.src/.patches/0006-*.patch" >/dev/null; then
    fail "P4_01_UNREVIEWED_PATCH" "P4.01 does not permit a new 0006 patch"
fi

FINAL_STAGE="deterministic-summary"
python3 - "${POLICY}" "${SUMMARY}" <<'PY'
import hashlib, json
from pathlib import Path
import sys
p = Path(sys.argv[1])
data = json.loads(p.read_text(encoding="utf-8"))
summary = {
    "schema": 1,
    "classification": "P4_01_POLICY_PREPARE_PASS",
    "project_version": data["project_version"],
    "objective": data["objective"],
    "roles": data["roles"],
    "part_04_objectives": data["part_04_objectives"],
    "next_objective": data["next_objective"],
    "policy_sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
    "guest_execution": False,
}
out = Path(sys.argv[2])
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(summary, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
print(out.read_text(encoding="utf-8").strip())
PY

echo "P4.01 policy contract: PASS"
echo "Guest execution: NONE"
echo "Real runtime session planning remains local and requires QEMU + local VM inputs."
CLASSIFICATION="P4_01_POLICY_PREPARE_PASS"
FINAL_STAGE="complete"

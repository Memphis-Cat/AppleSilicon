#!/usr/bin/env bash
set -Eeuo pipefail

VERSION="4.5.0.0.0.0"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
POLICY="${ROOT_DIR}/.src/.configs/p4.06-runtime-evidence-gate-policy.json"
TOOL="${ROOT_DIR}/.src/.tools/runtime-evidence-gate.py"
WORK_DIR="${APPLESILICON_P4_06_WORK_DIR:-${ROOT_DIR}/.build/p4.06}"
LOG_DIR="${APPLESILICON_LOG_DIR:-${ROOT_DIR}/.logs}"
OUTPUT="${APPLESILICON_P4_06_OUTPUT:-${WORK_DIR}/runtime-evidence-gate.json}"
RUN1="${WORK_DIR}/.runtime-gate-run-1-$$"
RUN2="${WORK_DIR}/.runtime-gate-run-2-$$"
TMP1="${WORK_DIR}/.runtime-gate-1-$$.json"
TMP2="${WORK_DIR}/.runtime-gate-2-$$.json"
CLASSIFICATION="UNCLASSIFIED"
FINAL_STAGE="startup"

mkdir -p "${WORK_DIR}" "${LOG_DIR}"
TIMESTAMP="$(date -u +"%Y%m%d-%H%M%S")"
LOG_FILE="${LOG_DIR}/AppleSilicon-p4.06-evaluate-${TIMESTAMP}-$$.log"
exec > >(tee "${LOG_FILE}") 2>&1

cleanup() {
  rm -rf "${RUN1}" "${RUN2}"
  rm -f "${TMP1}" "${TMP2}"
}
on_exit() {
  local rc=$?
  cleanup
  printf 'P4.06 runtime classification=%s stage=%s rc=%d log=%s\n' \
    "${CLASSIFICATION}" "${FINAL_STAGE}" "${rc}" "${LOG_FILE}"
}
trap on_exit EXIT

if [[ "$#" -eq 0 ]]; then
  echo "usage: $0 --reproduction AB_SESSION REFERENCE_MANIFEST PROBE_MANIFEST REFERENCE_TRACE PROBE_TRACE [--reproduction ...] [--promotion P4_05_PROMOTION]" >&2
  exit 2
fi

printf 'AppleSilicon P4.06 runtime evidence evaluation\n'
printf 'version=%s\n' "${VERSION}"

FINAL_STAGE="evaluate-first"
python3 "${TOOL}" --policy "${POLICY}" evaluate \
  "$@" --work-dir "${RUN1}" --output "${TMP1}" >/dev/null

FINAL_STAGE="evaluate-second"
python3 "${TOOL}" --policy "${POLICY}" evaluate \
  "$@" --work-dir "${RUN2}" --output "${TMP2}" >/dev/null

FINAL_STAGE="determinism"
cmp -s "${TMP1}" "${TMP2}"
mkdir -p "$(dirname "${OUTPUT}")"
cp "${TMP1}" "${OUTPUT}"

CLASSIFICATION="$(python3 - "${OUTPUT}" <<'PY'
import json, sys
with open(sys.argv[1], "r", encoding="utf-8") as f:
    print(json.load(f)["classification"])
PY
)"

FINAL_STAGE="complete"
printf 'runtime_gate=%s\n' "${OUTPUT}"
printf 'classification=%s\n' "${CLASSIFICATION}"

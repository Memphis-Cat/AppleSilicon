#!/usr/bin/env bash
set -Eeuo pipefail

VERSION="4.5.0.0.0.0"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
POLICY="${ROOT_DIR}/.src/.configs/p4.06-runtime-evidence-gate-policy.json"
TOOL="${ROOT_DIR}/.src/.tools/runtime-evidence-gate.py"
BUILD_DIR="${APPLESILICON_P4_06_BUILD_DIR:-${ROOT_DIR}/.build/p4.06}"
LOG_DIR="${APPLESILICON_LOG_DIR:-${ROOT_DIR}/.logs}"
OUTPUT="${BUILD_DIR}/implementation-state.json"
TMP1="${BUILD_DIR}/.implementation-1-$$.json"
TMP2="${BUILD_DIR}/.implementation-2-$$.json"
CLASSIFICATION="UNCLASSIFIED"
FINAL_STAGE="startup"

mkdir -p "${BUILD_DIR}" "${LOG_DIR}"
TIMESTAMP="$(date -u +"%Y%m%d-%H%M%S")"
LOG_FILE="${LOG_DIR}/AppleSilicon-p4.06-prepare-${TIMESTAMP}-$$.log"
exec > >(tee "${LOG_FILE}") 2>&1

cleanup() {
  rm -f "${TMP1}" "${TMP2}"
}
on_exit() {
  local rc=$?
  cleanup
  printf 'P4.06 prepare classification=%s stage=%s rc=%d log=%s\n' \
    "${CLASSIFICATION}" "${FINAL_STAGE}" "${rc}" "${LOG_FILE}"
}
trap on_exit EXIT

printf 'AppleSilicon P4.06 preparation\n'
printf 'version=%s\n' "${VERSION}"
printf 'root=%s\n' "${ROOT_DIR}"

FINAL_STAGE="syntax"
python3 -m py_compile "${TOOL}"
bash -n "${ROOT_DIR}/.src/.tools/evaluate-p4.06.sh"
python3 -m json.tool "${POLICY}" >/dev/null

FINAL_STAGE="policy"
python3 "${TOOL}" --policy "${POLICY}" validate-policy

FINAL_STAGE="self-check"
python3 "${TOOL}" --policy "${POLICY}" self-check

FINAL_STAGE="part-04-self-checks"
for item in \
  "p4.01-runtime-session-policy.json runtime-session.py" \
  "p4.02-probe-capture-policy.json probe-capture.py" \
  "p4.03-reference-capture-policy.json reference-capture.py" \
  "p4.04-ab-session-policy.json ab-session.py" \
  "p4.05-divergence-promotion-policy.json divergence-promotion.py"
do
  set -- ${item}
  python3 "${ROOT_DIR}/.src/.tools/$2" \
    --policy "${ROOT_DIR}/.src/.configs/$1" self-check
done

FINAL_STAGE="deterministic-implementation-state"
python3 "${TOOL}" --policy "${POLICY}" implementation --output "${TMP1}" >/dev/null
python3 "${TOOL}" --policy "${POLICY}" implementation --output "${TMP2}" >/dev/null
cmp -s "${TMP1}" "${TMP2}"
cp "${TMP1}" "${OUTPUT}"

FINAL_STAGE="repository-integrity"
PATCH_COUNT="$(find "${ROOT_DIR}/.src/.patches" -maxdepth 1 -type f -name '*.patch' | wc -l | tr -d ' ')"
[[ "${PATCH_COUNT}" == "5" ]]
[[ ! -e "${ROOT_DIR}/.src/.patches/0006-"* ]]
README_BLOB="$(git -C "${ROOT_DIR}" hash-object README.md)"
[[ "${README_BLOB}" == "5f056dadbac5d814b9ffb287ec786a559774f953" ]]
INFERNO_ENTRY="$(git -C "${ROOT_DIR}" ls-files -s .src/.upstream/.inferno)"
[[ "${INFERNO_ENTRY}" == 160000\ cc4302a99167abec69b714cfd00c38caece7e7de* ]]

CLASSIFICATION="P4_06_IMPLEMENTATION_COMPLETE_RUNTIME_EVIDENCE_PENDING"
FINAL_STAGE="complete"
printf 'implementation_state=%s\n' "${OUTPUT}"
printf 'runtime_evidence=deferred\n'
printf 'planned_roadmap=complete\n'

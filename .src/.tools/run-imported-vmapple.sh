#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
IMPORT_DIR="${ROOT_DIR}/.build/runtime/imported"

VALIDATOR="${ROOT_DIR}/.src/.tools/validate-vmapple-storage.py"
INTEGRITY="${ROOT_DIR}/.src/.tools/runtime_integrity.py"
RUNNER="${ROOT_DIR}/.src/.tools/run-p1.07-probe.sh"

AUX="${IMPORT_DIR}/aux.img"
ROOT="${IMPORT_DIR}/root.img"

MACHINE_ID_FILE="${IMPORT_DIR}/machine-id.txt"
IDENTITY="${IMPORT_DIR}/machine-identity.json"
MANIFEST="${IMPORT_DIR}/storage-manifest.txt"

fail() {
    printf 'ERROR: %s\n' "$*" >&2
    exit 1
}

[[ -x "$RUNNER" ]] ||
    fail "P1.07 runtime harness unavailable: $RUNNER"

[[ -x "$VALIDATOR" ]] ||
    fail "storage validator unavailable: $VALIDATOR"

[[ -f "$AUX" ]] ||
    fail "no staged AUX image; run import-vmapple-storage.sh first"

[[ -f "$ROOT" ]] ||
    fail "no staged root image; run import-vmapple-storage.sh first"

[[ -f "$MACHINE_ID_FILE" ]] ||
    fail "imported machine ID is missing"

[[ -f "$IDENTITY" ]] ||
    fail "imported machine identity is missing"

[[ -f "$MANIFEST" ]] ||
    fail "import manifest is missing"

MACHINE_ID="$(cat "$MACHINE_ID_FILE")"

MACHINE_ID="$(
    python3 "$INTEGRITY" machine-id "$MACHINE_ID"
)" || fail "imported machine ID is invalid"

python3 "$INTEGRITY" \
    identity \
    --compiled "$IDENTITY" \
    --machine-id "$MACHINE_ID" \
    >/dev/null ||
    fail "imported machine identity does not match imported machine ID"

MACHINE_ID_HASH="$(
    printf '%s' "$MACHINE_ID" |
    shasum -a 256 |
    awk '{print $1}'
)"

echo "===== IMPORTED VMAPPLE STORAGE ====="
echo "AUX working image: $AUX"
echo "ROOT working image: $ROOT"
echo "Machine ID SHA-256: $MACHINE_ID_HASH"
echo "Machine identity: $IDENTITY"
echo

python3 "$VALIDATOR" \
    --aux "$AUX" \
    --root "$ROOT"

export APPLESILICON_VMAPPLE_AUX="$AUX"
export APPLESILICON_VMAPPLE_DISK="$ROOT"

export APPLESILICON_VMAPPLE_UUID="$MACHINE_ID"
export APPLESILICON_VMAPPLE_MACHINE_IDENTITY="$IDENTITY"

echo
echo "===== STARTING VMAPPLE RUNTIME ====="
echo "Only staged working images and their matching imported identity are used."
echo

exec bash "$RUNNER"

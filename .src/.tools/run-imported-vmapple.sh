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

hash_file() {
    shasum -a 256 "$1" | awk '{print $1}'
}

hash_text() {
    printf '%s' "$1" | shasum -a 256 | awk '{print $1}'
}

manifest_value() {
    local key="$1"

    awk -v key="$key" '
        index($0, key ": ") == 1 {
            print substr($0, length(key) + 3)
            found = 1
            exit
        }

        END {
            if (!found)
                exit 1
        }
    ' "$MANIFEST"
}

require_sha256() {
    local label="$1"
    local value="$2"

    [[ "$value" =~ ^[0-9a-f]{64}$ ]] ||
        fail "$label in import manifest is not a valid lowercase SHA-256"
}

[[ -x "$RUNNER" ]] ||
    fail "P1.07 runtime harness unavailable: $RUNNER"

[[ -f "$VALIDATOR" ]] ||
    fail "storage validator unavailable: $VALIDATOR"

[[ -f "$INTEGRITY" ]] ||
    fail "runtime integrity helper unavailable: $INTEGRITY"

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

echo "===== IMPORTED BUNDLE INTEGRITY ====="

EXPECTED_AUX_HASH="$(
    manifest_value "AUX staged SHA-256"
)" || fail "manifest has no AUX staged SHA-256"

EXPECTED_ROOT_HASH="$(
    manifest_value "ROOT staged SHA-256"
)" || fail "manifest has no ROOT staged SHA-256"

EXPECTED_IDENTITY_HASH="$(
    manifest_value "Machine identity SHA-256"
)" || fail "manifest has no machine identity SHA-256"

EXPECTED_MACHINE_ID_HASH="$(
    manifest_value "Machine ID SHA-256"
)" || fail "manifest has no machine ID SHA-256"

require_sha256 "AUX staged SHA-256" "$EXPECTED_AUX_HASH"
require_sha256 "ROOT staged SHA-256" "$EXPECTED_ROOT_HASH"
require_sha256 "Machine identity SHA-256" "$EXPECTED_IDENTITY_HASH"
require_sha256 "Machine ID SHA-256" "$EXPECTED_MACHINE_ID_HASH"

ACTUAL_AUX_HASH="$(hash_file "$AUX")"
ACTUAL_ROOT_HASH="$(hash_file "$ROOT")"
ACTUAL_IDENTITY_HASH="$(hash_file "$IDENTITY")"

[[ "$ACTUAL_AUX_HASH" == "$EXPECTED_AUX_HASH" ]] ||
    fail "staged AUX changed after import"

[[ "$ACTUAL_ROOT_HASH" == "$EXPECTED_ROOT_HASH" ]] ||
    fail "staged root changed after import"

[[ "$ACTUAL_IDENTITY_HASH" == "$EXPECTED_IDENTITY_HASH" ]] ||
    fail "compiled machine identity changed after import"

RAW_MACHINE_ID="$(cat "$MACHINE_ID_FILE")"

MACHINE_ID="$(
    python3 "$INTEGRITY" machine-id "$RAW_MACHINE_ID"
)" || fail "imported machine ID is invalid"

ACTUAL_MACHINE_ID_HASH="$(hash_text "$MACHINE_ID")"

[[ "$ACTUAL_MACHINE_ID_HASH" == "$EXPECTED_MACHINE_ID_HASH" ]] ||
    fail "imported machine ID changed after import"

python3 "$INTEGRITY" \
    identity \
    --compiled "$IDENTITY" \
    --machine-id "$MACHINE_ID" \
    >/dev/null ||
    fail "compiled machine identity does not match imported machine ID"

echo "PASS: AUX matches import manifest"
echo "PASS: root matches import manifest"
echo "PASS: machine identity matches import manifest"
echo "PASS: machine ID matches import manifest"
echo "PASS: compiled identity matches machine ID"

MACHINE_ID_HASH="$ACTUAL_MACHINE_ID_HASH"

echo
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
echo "Only manifest-verified staged images and their matching identity are used."
echo

exec bash "$RUNNER"

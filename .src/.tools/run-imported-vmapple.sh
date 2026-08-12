#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
IMPORT_DIR="${ROOT_DIR}/.build/runtime/imported"

VALIDATOR="${ROOT_DIR}/.src/.tools/validate-vmapple-storage.py"
RUNNER="${ROOT_DIR}/.src/.tools/run-p1.07-probe.sh"

AUX="${IMPORT_DIR}/aux.img"
ROOT="${IMPORT_DIR}/root.img"
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

[[ -f "$MANIFEST" ]] ||
    fail "import manifest missing: $MANIFEST"

echo "===== IMPORTED VMAPPLE STORAGE ====="
echo "AUX working image: $AUX"
echo "ROOT working image: $ROOT"
echo

python3 "$VALIDATOR" \
    --aux "$AUX" \
    --root "$ROOT"

export APPLESILICON_VMAPPLE_AUX="$AUX"
export APPLESILICON_VMAPPLE_DISK="$ROOT"

echo
echo "===== STARTING VMAPPLE RUNTIME ====="
echo "Only staged working images are being passed to QEMU."
echo

exec bash "$RUNNER"

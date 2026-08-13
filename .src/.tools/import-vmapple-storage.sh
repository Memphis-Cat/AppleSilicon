#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
VALIDATOR="${ROOT_DIR}/.src/.tools/validate-vmapple-storage.py"
DEST="${ROOT_DIR}/.build/runtime/imported"

usage() {
    cat >&2 <<EOF
Usage:
  $0 --aux-format vf-full <aux-image> <root-image>
  $0 --aux-format qemu-trimmed <aux-image> <root-image>

AUX formats:
  vf-full        Original Virtualization.framework AUX image.
                 The first 0x4000 bytes are removed from the staged copy.

  qemu-trimmed   AUX image already prepared for QEMU VMApple.
                 The staged copy is byte-identical to the source.
EOF
    exit 2
}

fail() {
    printf 'ERROR: %s\n' "$*" >&2
    exit 1
}

realpath_py() {
    python3 -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "$1"
}

hash_file() {
    shasum -a 256 "$1" | awk '{print $1}'
}

file_size() {
    stat -f '%z' "$1"
}

copy_image() {
    local src="$1"
    local dst="$2"

    if cp -c "$src" "$dst" 2>/dev/null; then
        echo "clone"
    else
        cp "$src" "$dst"
        echo "copy"
    fi
}

[[ $# -eq 4 ]] || usage
[[ "$1" == "--aux-format" ]] || usage

AUX_FORMAT="$2"

case "$AUX_FORMAT" in
    vf-full|qemu-trimmed)
        ;;
    *)
        fail "unknown AUX format: $AUX_FORMAT"
        ;;
esac

AUX_SOURCE="$(realpath_py "$3")"
ROOT_SOURCE="$(realpath_py "$4")"

[[ -f "$AUX_SOURCE" ]] ||
    fail "AUX source does not exist: $AUX_SOURCE"

[[ -f "$ROOT_SOURCE" ]] ||
    fail "root source does not exist: $ROOT_SOURCE"

AUX_SOURCE_SIZE="$(file_size "$AUX_SOURCE")"
ROOT_SOURCE_SIZE="$(file_size "$ROOT_SOURCE")"

(( AUX_SOURCE_SIZE > 0 )) ||
    fail "AUX source is empty"

(( ROOT_SOURCE_SIZE > 0 )) ||
    fail "root source is empty"

if [[ "$AUX_FORMAT" == "vf-full" ]]; then
    (( AUX_SOURCE_SIZE > 0x4000 )) ||
        fail "full VF AUX is too small to contain the 0x4000-byte metadata prefix"
fi

AUX_SOURCE_HASH="$(hash_file "$AUX_SOURCE")"
ROOT_SOURCE_HASH="$(hash_file "$ROOT_SOURCE")"

mkdir -p "$DEST"

TMP_DIR="$(mktemp -d "${DEST}/.import.XXXXXX")"

cleanup() {
    rm -rf "$TMP_DIR"
}
trap cleanup EXIT

AUX_STAGE_TMP="$TMP_DIR/aux.img"
ROOT_STAGE_TMP="$TMP_DIR/root.img"

echo "===== VMAPPLE STORAGE IMPORT ====="
echo "AUX source: $AUX_SOURCE"
echo "ROOT source: $ROOT_SOURCE"
echo "AUX source format: $AUX_FORMAT"
echo

echo "===== STAGING ROOT ====="

ROOT_MODE="$(copy_image "$ROOT_SOURCE" "$ROOT_STAGE_TMP")"

echo "ROOT staging mode: $ROOT_MODE"

echo
echo "===== STAGING AUX ====="

if [[ "$AUX_FORMAT" == "vf-full" ]]; then
    dd \
        if="$AUX_SOURCE" \
        of="$AUX_STAGE_TMP" \
        bs=16384 \
        skip=1 \
        status=none

    AUX_MODE="trim-0x4000"

    EXPECTED_AUX_SIZE=$((AUX_SOURCE_SIZE - 0x4000))
    ACTUAL_AUX_SIZE="$(file_size "$AUX_STAGE_TMP")"

    [[ "$ACTUAL_AUX_SIZE" -eq "$EXPECTED_AUX_SIZE" ]] ||
        fail "trimmed AUX size mismatch: expected $EXPECTED_AUX_SIZE, got $ACTUAL_AUX_SIZE"
else
    AUX_MODE="$(copy_image "$AUX_SOURCE" "$AUX_STAGE_TMP")"

    cmp -s "$AUX_SOURCE" "$AUX_STAGE_TMP" ||
        fail "staged AUX differs from already-trimmed source"
fi

echo "AUX staging mode: $AUX_MODE"

cmp -s "$ROOT_SOURCE" "$ROOT_STAGE_TMP" ||
    fail "staged root differs from source"

echo
echo "===== STAGED STORAGE PREFLIGHT ====="

python3 "$VALIDATOR" \
    --aux "$AUX_STAGE_TMP" \
    --root "$ROOT_STAGE_TMP"

AUX_STAGE_HASH="$(hash_file "$AUX_STAGE_TMP")"
ROOT_STAGE_HASH="$(hash_file "$ROOT_STAGE_TMP")"

[[ "$ROOT_SOURCE_HASH" == "$ROOT_STAGE_HASH" ]] ||
    fail "staged root SHA-256 differs from source"

if [[ "$AUX_FORMAT" == "qemu-trimmed" ]]; then
    [[ "$AUX_SOURCE_HASH" == "$AUX_STAGE_HASH" ]] ||
        fail "staged AUX SHA-256 differs from source"
fi

AUX_FINAL="$DEST/aux.img"
ROOT_FINAL="$DEST/root.img"
MANIFEST_TMP="$TMP_DIR/storage-manifest.txt"
MANIFEST_FINAL="$DEST/storage-manifest.txt"

cat > "$MANIFEST_TMP" <<EOF
Imported UTC: $(date -u +'%Y-%m-%dT%H:%M:%SZ')
AUX source: $AUX_SOURCE
ROOT source: $ROOT_SOURCE
AUX source format: $AUX_FORMAT
AUX transformation: $AUX_MODE
ROOT staging mode: $ROOT_MODE
AUX source size: $AUX_SOURCE_SIZE
AUX staged size: $(file_size "$AUX_STAGE_TMP")
ROOT source size: $ROOT_SOURCE_SIZE
ROOT staged size: $(file_size "$ROOT_STAGE_TMP")
AUX source SHA-256: $AUX_SOURCE_HASH
AUX staged SHA-256: $AUX_STAGE_HASH
ROOT source SHA-256: $ROOT_SOURCE_HASH
ROOT staged SHA-256: $ROOT_STAGE_HASH
EOF

rm -f "$AUX_FINAL" "$ROOT_FINAL" "$MANIFEST_FINAL"

mv "$AUX_STAGE_TMP" "$AUX_FINAL"
mv "$ROOT_STAGE_TMP" "$ROOT_FINAL"
mv "$MANIFEST_TMP" "$MANIFEST_FINAL"

echo
echo "===== IMPORT COMPLETE ====="
echo "AUX working image: $AUX_FINAL"
echo "ROOT working image: $ROOT_FINAL"
echo "Manifest: $MANIFEST_FINAL"
echo
echo "Original source images were not modified."

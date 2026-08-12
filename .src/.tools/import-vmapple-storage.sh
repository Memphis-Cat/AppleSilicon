#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
VALIDATOR="${ROOT_DIR}/.src/.tools/validate-vmapple-storage.py"
DEST="${ROOT_DIR}/.build/runtime/imported"

if [[ $# -ne 2 ]]; then
    echo "Usage: $0 <aux-image> <root-image>" >&2
    exit 2
fi

realpath_py() {
    python3 -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "$1"
}

hash_file() {
    shasum -a 256 "$1" | awk '{print $1}'
}

stage_image() {
    local src="$1"
    local dst="$2"

    rm -f "$dst"

    if cp -c "$src" "$dst" 2>/dev/null; then
        echo "clone"
    else
        cp "$src" "$dst"
        echo "copy"
    fi
}

AUX_SOURCE="$(realpath_py "$1")"
ROOT_SOURCE="$(realpath_py "$2")"

echo "===== SOURCE STORAGE PREFLIGHT ====="

python3 "$VALIDATOR" \
    --aux "$AUX_SOURCE" \
    --root "$ROOT_SOURCE"

mkdir -p "$DEST"

AUX_STAGE="$DEST/aux.img"
ROOT_STAGE="$DEST/root.img"

echo
echo "===== STAGING WORKING COPIES ====="

AUX_MODE="$(stage_image "$AUX_SOURCE" "$AUX_STAGE")"
ROOT_MODE="$(stage_image "$ROOT_SOURCE" "$ROOT_STAGE")"

echo "AUX staging mode: $AUX_MODE"
echo "ROOT staging mode: $ROOT_MODE"

echo
echo "===== STAGED STORAGE PREFLIGHT ====="

python3 "$VALIDATOR" \
    --aux "$AUX_STAGE" \
    --root "$ROOT_STAGE"

AUX_SOURCE_HASH="$(hash_file "$AUX_SOURCE")"
ROOT_SOURCE_HASH="$(hash_file "$ROOT_SOURCE")"
AUX_STAGE_HASH="$(hash_file "$AUX_STAGE")"
ROOT_STAGE_HASH="$(hash_file "$ROOT_STAGE")"

[[ "$AUX_SOURCE_HASH" == "$AUX_STAGE_HASH" ]] || {
    echo "ERROR: staged AUX differs from source" >&2
    exit 1
}

[[ "$ROOT_SOURCE_HASH" == "$ROOT_STAGE_HASH" ]] || {
    echo "ERROR: staged root differs from source" >&2
    exit 1
}

cat > "$DEST/storage-manifest.txt" <<EOF
Imported UTC: $(date -u +'%Y-%m-%dT%H:%M:%SZ')
AUX source: $AUX_SOURCE
ROOT source: $ROOT_SOURCE
AUX staging mode: $AUX_MODE
ROOT staging mode: $ROOT_MODE
AUX source SHA-256: $AUX_SOURCE_HASH
ROOT source SHA-256: $ROOT_SOURCE_HASH
AUX staged SHA-256: $AUX_STAGE_HASH
ROOT staged SHA-256: $ROOT_STAGE_HASH
EOF

echo
echo "Storage staged successfully."
echo "Original files will not be passed to QEMU."
echo "AUX working image: $AUX_STAGE"
echo "ROOT working image: $ROOT_STAGE"
echo "Manifest: $DEST/storage-manifest.txt"

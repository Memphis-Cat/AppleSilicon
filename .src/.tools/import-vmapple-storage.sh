#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

VALIDATOR="${ROOT_DIR}/.src/.tools/validate-vmapple-storage.py"
PLATFORM_IDENTITY="${ROOT_DIR}/.src/.tools/platform-identity.py"
INTEGRITY="${ROOT_DIR}/.src/.tools/runtime_integrity.py"

DEST="${ROOT_DIR}/.build/runtime/imported"

usage() {
    cat >&2 <<EOF
Usage:
  $0 --aux-format vf-full --machine-json <macosvm.json> <aux-image> <root-image>
  $0 --aux-format qemu-trimmed --machine-json <macosvm.json> <aux-image> <root-image>

  $0 --aux-format vf-full --machine-id <uint64> <aux-image> <root-image>
  $0 --aux-format qemu-trimmed --machine-id <uint64> <aux-image> <root-image>

AUX formats:
  vf-full
      Original Virtualization.framework AUX.
      Removes the first 0x4000 bytes from the staged working copy.

  qemu-trimmed
      AUX already prepared for QEMU VMApple.
      Preserved byte-for-byte.

Machine identity:
  --machine-json
      Extract ECID from a macosvm-style machineId object.

  --machine-id
      Supply the VMApple ECID/machine ID directly.
EOF
    exit 2
}

fail() {
    printf 'ERROR: %s\n' "$*" >&2
    exit 1
}

realpath_py() {
    python3 -c \
        'import os,sys; print(os.path.realpath(sys.argv[1]))' \
        "$1"
}

hash_file() {
    shasum -a 256 "$1" | awk '{print $1}'
}

hash_text() {
    printf '%s' "$1" | shasum -a 256 | awk '{print $1}'
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

extract_macosvm_ecid() {
    python3 - "$1" <<'PY'
from pathlib import Path
import base64
import json
import plistlib
import sys

path = Path(sys.argv[1])

try:
    config = json.loads(path.read_text())
except Exception as exc:
    raise SystemExit(f"could not read machine JSON: {exc}")

encoded = config.get("machineId")

if not isinstance(encoded, str) or not encoded:
    raise SystemExit("machine JSON has no valid machineId string")

try:
    payload = base64.b64decode(encoded, validate=True)
except Exception as exc:
    raise SystemExit(f"machineId is not valid base64: {exc}")

try:
    machine = plistlib.loads(payload)
except Exception as exc:
    raise SystemExit(f"machineId does not contain a valid plist: {exc}")

ecid = machine.get("ECID")

if isinstance(ecid, bool) or not isinstance(ecid, int):
    raise SystemExit("machineId plist has no integer ECID")

if not 0 <= ecid <= 0xFFFFFFFFFFFFFFFF:
    raise SystemExit("ECID does not fit uint64")

print(ecid)
PY
}

AUX_FORMAT=""
MACHINE_JSON=""
MACHINE_ID_INPUT=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --aux-format)
            [[ $# -ge 2 ]] || usage
            AUX_FORMAT="$2"
            shift 2
            ;;

        --machine-json)
            [[ $# -ge 2 ]] || usage
            MACHINE_JSON="$2"
            shift 2
            ;;

        --machine-id)
            [[ $# -ge 2 ]] || usage
            MACHINE_ID_INPUT="$2"
            shift 2
            ;;

        --)
            shift
            break
            ;;

        -*)
            fail "unknown option: $1"
            ;;

        *)
            break
            ;;
    esac
done

[[ -n "$AUX_FORMAT" ]] ||
    fail "--aux-format is required"

case "$AUX_FORMAT" in
    vf-full|qemu-trimmed)
        ;;
    *)
        fail "unknown AUX format: $AUX_FORMAT"
        ;;
esac

if [[ -n "$MACHINE_JSON" && -n "$MACHINE_ID_INPUT" ]]; then
    fail "use either --machine-json or --machine-id, not both"
fi

if [[ -z "$MACHINE_JSON" && -z "$MACHINE_ID_INPUT" ]]; then
    fail "machine identity is required: use --machine-json or --machine-id"
fi

[[ $# -eq 2 ]] || usage

AUX_SOURCE="$(realpath_py "$1")"
ROOT_SOURCE="$(realpath_py "$2")"

[[ -f "$AUX_SOURCE" ]] ||
    fail "AUX source does not exist: $AUX_SOURCE"

[[ -f "$ROOT_SOURCE" ]] ||
    fail "root source does not exist: $ROOT_SOURCE"

MACHINE_METADATA_SOURCE="explicit-machine-id"

if [[ -n "$MACHINE_JSON" ]]; then
    MACHINE_JSON="$(realpath_py "$MACHINE_JSON")"

    [[ -f "$MACHINE_JSON" ]] ||
        fail "machine JSON does not exist: $MACHINE_JSON"

    MACHINE_ID_INPUT="$(extract_macosvm_ecid "$MACHINE_JSON")" ||
        fail "could not extract ECID from machine JSON"

    MACHINE_METADATA_SOURCE="$MACHINE_JSON"
fi

MACHINE_ID="$(
    python3 "$INTEGRITY" machine-id "$MACHINE_ID_INPUT"
)" || fail "invalid VMApple machine ID"

MACHINE_ID_HASH="$(hash_text "$MACHINE_ID")"

AUX_SOURCE_SIZE="$(file_size "$AUX_SOURCE")"
ROOT_SOURCE_SIZE="$(file_size "$ROOT_SOURCE")"

(( AUX_SOURCE_SIZE > 0 )) ||
    fail "AUX source is empty"

(( ROOT_SOURCE_SIZE > 0 )) ||
    fail "root source is empty"

if [[ "$AUX_FORMAT" == "vf-full" ]]; then
    (( AUX_SOURCE_SIZE > 0x4000 )) ||
        fail "full VF AUX is too small for its 0x4000-byte metadata prefix"
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

PROFILE_TMP="$TMP_DIR/machine-profile.json"
IDENTITY_TMP="$TMP_DIR/machine-identity.json"
MACHINE_ID_TMP="$TMP_DIR/machine-id.txt"
MANIFEST_TMP="$TMP_DIR/storage-manifest.txt"

echo "===== VMAPPLE STORAGE IMPORT ====="
echo "AUX source: $AUX_SOURCE"
echo "ROOT source: $ROOT_SOURCE"
echo "AUX source format: $AUX_FORMAT"
echo "Machine ID SHA-256: $MACHINE_ID_HASH"
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
        fail "trimmed AUX size mismatch"
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

echo
echo "===== MACHINE IDENTITY ====="

python3 - "$MACHINE_ID" "$PROFILE_TMP" <<'PY'
from pathlib import Path
import json
import sys

machine_id = int(sys.argv[1])

profile = {
    "schema": 1,
    "project_version": "3.1.0.0.0.0",
    "objective": "P3.02",
    "synthetic": False,
    "example_only": False,
    "machine_uuid": machine_id,
    "identity": {},
    "installer": {
        "run_installer1": 0,
        "run_installer2": 0,
    },
}

Path(sys.argv[2]).write_text(
    json.dumps(profile, indent=2, sort_keys=True) + "\n"
)
PY

python3 "$PLATFORM_IDENTITY" \
    compile \
    --profile "$PROFILE_TMP" \
    --output "$IDENTITY_TMP"

python3 "$INTEGRITY" \
    identity \
    --compiled "$IDENTITY_TMP" \
    --machine-id "$MACHINE_ID"

printf '%s\n' "$MACHINE_ID" > "$MACHINE_ID_TMP"

IDENTITY_HASH="$(hash_file "$IDENTITY_TMP")"

cat > "$MANIFEST_TMP" <<EOF
Imported UTC: $(date -u +'%Y-%m-%dT%H:%M:%SZ')
AUX source: $AUX_SOURCE
ROOT source: $ROOT_SOURCE
AUX source format: $AUX_FORMAT
AUX transformation: $AUX_MODE
ROOT staging mode: $ROOT_MODE
Machine metadata source: $MACHINE_METADATA_SOURCE
Machine ID SHA-256: $MACHINE_ID_HASH
Machine identity SHA-256: $IDENTITY_HASH
AUX source size: $AUX_SOURCE_SIZE
AUX staged size: $(file_size "$AUX_STAGE_TMP")
ROOT source size: $ROOT_SOURCE_SIZE
ROOT staged size: $(file_size "$ROOT_STAGE_TMP")
AUX source SHA-256: $AUX_SOURCE_HASH
AUX staged SHA-256: $AUX_STAGE_HASH
ROOT source SHA-256: $ROOT_SOURCE_HASH
ROOT staged SHA-256: $ROOT_STAGE_HASH
EOF

AUX_FINAL="$DEST/aux.img"
ROOT_FINAL="$DEST/root.img"
PROFILE_FINAL="$DEST/machine-profile.json"
IDENTITY_FINAL="$DEST/machine-identity.json"
MACHINE_ID_FINAL="$DEST/machine-id.txt"
MANIFEST_FINAL="$DEST/storage-manifest.txt"

rm -f \
    "$AUX_FINAL" \
    "$ROOT_FINAL" \
    "$PROFILE_FINAL" \
    "$IDENTITY_FINAL" \
    "$MACHINE_ID_FINAL" \
    "$MANIFEST_FINAL"

mv "$AUX_STAGE_TMP" "$AUX_FINAL"
mv "$ROOT_STAGE_TMP" "$ROOT_FINAL"
mv "$PROFILE_TMP" "$PROFILE_FINAL"
mv "$IDENTITY_TMP" "$IDENTITY_FINAL"
mv "$MACHINE_ID_TMP" "$MACHINE_ID_FINAL"
mv "$MANIFEST_TMP" "$MANIFEST_FINAL"

echo
echo "===== IMPORT COMPLETE ====="
echo "AUX working image: $AUX_FINAL"
echo "ROOT working image: $ROOT_FINAL"
echo "Machine identity: $IDENTITY_FINAL"
echo "Manifest: $MANIFEST_FINAL"
echo
echo "Original source files were not modified."

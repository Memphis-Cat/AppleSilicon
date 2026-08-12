#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

PROFILE="${ROOT_DIR}/.build/runtime/p1.07-runtime.env"

QEMU="${ROOT_DIR}/.build/runtime-inferno/qemu-system-aarch64"
IDENTITY="${ROOT_DIR}/.build/runtime/machine-identity-runtime.json"

SYSTEM_FIRMWARE="${APPLESILICON_VMAPPLE_FIRMWARE_SOURCE:-/System/Library/Frameworks/Virtualization.framework/Resources/AVPBooter.vmapple2.bin}"
FIRMWARE_DIR="${ROOT_DIR}/.build/runtime/realboot"
FIRMWARE="${FIRMWARE_DIR}/AVPBooter.vmapple2.bin"

fail() {
    printf 'ERROR: %s\n' "$*" >&2
    exit 1
}

file_size() {
    if stat -f '%z' "$1" >/dev/null 2>&1; then
        stat -f '%z' "$1"
    else
        stat -c '%s' "$1"
    fi
}

hash_file() {
    shasum -a 256 "$1" | awk '{print $1}'
}

[[ -x "$QEMU" ]] ||
    fail "QEMU binary missing: $QEMU"

[[ -f "$IDENTITY" ]] ||
    fail "machine identity missing: $IDENTITY"

[[ -f "$SYSTEM_FIRMWARE" && -r "$SYSTEM_FIRMWARE" ]] ||
    fail "local VMApple firmware source missing or unreadable: $SYSTEM_FIRMWARE"

SOURCE_BYTES="$(file_size "$SYSTEM_FIRMWARE")"

(( SOURCE_BYTES > 0 && SOURCE_BYTES <= 1048576 )) ||
    fail "local VMApple firmware must be non-empty and no larger than 1 MiB"

mkdir -p "$FIRMWARE_DIR"

echo "===== VMAPPLE FIRMWARE PROVISIONING ====="
echo "Source: $SYSTEM_FIRMWARE"
echo "Source size: $SOURCE_BYTES bytes"

if [[ -f "$FIRMWARE" ]] && cmp -s "$SYSTEM_FIRMWARE" "$FIRMWARE"; then
    echo "Working copy already matches local system firmware."
else
    TMP="${FIRMWARE}.tmp.$$"

    trap 'rm -f "${TMP:-}"' EXIT

    cp "$SYSTEM_FIRMWARE" "$TMP"

    TMP_BYTES="$(file_size "$TMP")"

    [[ "$TMP_BYTES" == "$SOURCE_BYTES" ]] ||
        fail "firmware copy size mismatch"

    cmp -s "$SYSTEM_FIRMWARE" "$TMP" ||
        fail "firmware copy differs from source"

    mv -f "$TMP" "$FIRMWARE"

    trap - EXIT

    echo "Provisioned local firmware working copy."
fi

[[ -f "$FIRMWARE" && -r "$FIRMWARE" ]] ||
    fail "provisioned firmware is unavailable: $FIRMWARE"

cmp -s "$SYSTEM_FIRMWARE" "$FIRMWARE" ||
    fail "provisioned firmware differs from local source"

FIRMWARE_BYTES="$(file_size "$FIRMWARE")"
FIRMWARE_HASH="$(hash_file "$FIRMWARE")"

echo "Working copy: $FIRMWARE"
echo "Working size: $FIRMWARE_BYTES bytes"
echo "SHA-256: $FIRMWARE_HASH"

mkdir -p "$(dirname "$PROFILE")"

cat > "$PROFILE" <<'EOF'
APPLESILICON_QEMU_BIN="${ROOT_DIR}/.build/runtime-inferno/qemu-system-aarch64"

APPLESILICON_VMAPPLE_ACCEL="tcg"
APPLESILICON_VMAPPLE_CPU_PROFILE="apple-gxf"
APPLESILICON_VMAPPLE_SMP="4"
APPLESILICON_VMAPPLE_RAM="4G"

APPLESILICON_VMAPPLE_UUID="0x13579bdf2468ace0"
APPLESILICON_VMAPPLE_MACHINE_IDENTITY="${ROOT_DIR}/.build/runtime/machine-identity-runtime.json"
APPLESILICON_VMAPPLE_FIRMWARE="${ROOT_DIR}/.build/runtime/realboot/AVPBooter.vmapple2.bin"

APPLESILICON_P1_07_QEMU_SEED="135792468"
EOF

echo
echo "===== P1.07 RUNTIME PROFILE ====="
echo "Profile: $PROFILE"
echo
cat "$PROFILE"
echo
echo "Runtime profile configured."

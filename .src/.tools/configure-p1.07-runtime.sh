#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PROFILE="${ROOT_DIR}/.build/runtime/p1.07-runtime.env"

QEMU="${ROOT_DIR}/.build/runtime-inferno/qemu-system-aarch64"
IDENTITY="${ROOT_DIR}/.build/runtime/machine-identity-runtime.json"
FIRMWARE="${ROOT_DIR}/.build/runtime/realboot/AVPBooter.vmapple2.bin"

fail() {
    printf 'ERROR: %s\n' "$*" >&2
    exit 1
}

[[ -x "$QEMU" ]] ||
    fail "QEMU binary missing: $QEMU"

[[ -f "$IDENTITY" ]] ||
    fail "machine identity missing: $IDENTITY"

[[ -f "$FIRMWARE" ]] ||
    fail "VMApple firmware missing: $FIRMWARE"

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

echo "===== P1.07 RUNTIME PROFILE ====="
echo "Profile: $PROFILE"
echo
cat "$PROFILE"
echo
echo "Runtime profile configured."

# Part 03 — VMApple Platform Contract

Project version: **`3.4.0.0.0.0`**

Status: **Active — P3.01 through P3.05 implemented**

## Purpose

Part 01 established the VMApple/TCG evidence pipeline. Part 02 established the deliberate CPU compatibility contract. Part 03 owns the remaining non-CPU VMApple machine contract.

The goal is to answer, for every guest-visible platform component:

1. Is this ordinary QEMU/Arm infrastructure?
2. Is it VMApple-specific?
3. Is it tied to a host-only Apple framework?
4. Is its runtime requirement still unknown?
5. Which Part 03 objective owns validation or implementation?

Apple-specific source code is not automatically classified as missing or boot-critical.

## Fixed objective count

Part 03 has exactly six objectives:

```text
P3.01 — Platform Contract Inventory and Ownership Map
P3.02 — Configuration and Platform Identity Contract
P3.03 — Interrupt, Timer, Power and Console Contract
P3.04 — Boot Backdoor and Storage Contract
P3.05 — PCIe, Peripheral, Crypto and Graphics Contract
P3.06 — Part 03 Integration Gate
```

There is **no P3.07**.

## Ownership model

P3.01 uses four ownership classes:

```text
generic_qemu
vmapple_specific
host_framework_dependent
unknown_requires_evidence
```

These describe where behavior comes from, not whether it is correct.

### `generic_qemu`

Existing generic QEMU/Arm hardware used by VMApple, such as GICv3, PL011, GPEX PCIe, XHCI and virtio devices.

Default action: preserve or validate.

### `vmapple_specific`

Project/device behavior that intentionally models the VMApple virtual-Mac contract, such as the configuration region, boot backdoor, Apple-flavored virtio block and Apple AES device.

Default action: validate against evidence before changing semantics.

### `host_framework_dependent`

A path whose original implementation relies on host-only Apple frameworks, represented by Apple PVG graphics.

Default action: defer or investigate.

### `unknown_requires_evidence`

A contract boundary whose presence is known but whose exact runtime requirement is not established.

Default action: investigate or defer.

## P3.01 — Platform Contract Inventory and Ownership Map

Status: **Implementation complete — static ownership map**

P3.01 source-locks the pinned Inferno VMApple machine/device files and XNU's public VMApple platform configuration, then creates a machine-readable ownership map for the remaining non-CPU platform.

Project files:

```text
.docs/P3.01.md
.src/.configs/p3.01-platform-contract.json
.src/.tools/platform-contract.py
.src/.tools/prepare-p3.01.sh
```

## P3.02 — Configuration and Platform Identity Contract

Status: **Implementation complete — runtime identity validation deferred**

P3.02 freezes the config-region field ownership model, preserves machine-derived CPU/RAM/random/CPU-ID behavior, adds a privacy-safe local identity-profile compiler, and records the unresolved `cpu_ids[0x80]` versus documented-offset layout discrepancy without guessing a fix.

Project files:

```text
.docs/P3.02.md
.src/.configs/p3.02-identity-contract.json
.src/.configs/p3.02-identity.example.json
.src/.tools/platform-identity.py
.src/.tools/prepare-p3.02.sh
```

## P3.03 — Interrupt, Timer, Power and Console Contract

Status: **Implementation complete — runtime interrupt validation deferred**

P3.03 freezes the stable generic-device wiring used by pinned Inferno and upstream QEMU 11.1.0:

```text
GICv3 distributor       0x10000000
GICv3 redistributors    0x10010000
virtual timer           PPI 27
PL011 UART               0x20010000 / SPI 1
PL031 RTC                0x20050000 / SPI 2
PL061 GPIO/power         0x20060000 / SPI 5 / pin 3
pvpanic MMIO             0x20070000 / no IRQ
```

XNU independently confirms VMApple uses GICv3 and PL011 and defines a `0x20000` GIC redistributor-per-PE size. The `0x400000` VMApple redistributor window therefore covers exactly the machine's 32-vCPU cap.

No P3.03 Inferno patch is added. Generic devices remain preserved until runtime evidence proves a concrete incompatibility. Exact power-button event semantics remain evidence-gated.

Project files:

```text
.docs/P3.03.md
.src/.configs/p3.03-io-contract.json
.src/.tools/platform-io-contract.py
.src/.tools/prepare-p3.03.sh
```

## P3.04 — Boot Backdoor and Storage Contract

Status: **Implementation complete — runtime storage validation deferred**

P3.04 freezes VMApple's two-phase storage model:

```text
pre-boot: BDIF MMIO/DMA reads over AUX/root backends
runtime:  vmapple-virtio-blk-pci variant=aux/root
```

It locks the BDIF window at `0x30000000/0x00200000`, the source-known BDIF register/selector values, 512-byte sector and 128 MiB request limits, read-only observed pre-boot behavior, backend attachment order/fallback, Apple PCI identity `106b:1a00`, AUX/root variant contract, Apple type-field placement and the successful no-op Apple barrier.

No P3.04 Inferno patch is added. BDIF write requirements and real barrier/flush semantics remain runtime-evidence gated.

Project files:

```text
.docs/P3.04.md
.src/.configs/p3.04-storage-contract.json
.src/.tools/platform-storage-contract.py
.src/.tools/prepare-p3.04.sh
```

## P3.05 — PCIe, Peripheral, Crypto and Graphics Contract

Status: **Implementation complete — runtime peripheral/AES/graphics validation deferred**

P3.05 freezes the remaining non-CPU peripheral ownership boundary:

```text
generic QEMU
├── GPEX PCIe
├── disable-legacy virtio PCI transport
├── virtio-net-pci
├── qemu-xhci
├── usb-kbd
└── usb-tablet

VMApple-specific
└── Apple AES MMIO

host-framework-dependent
└── apple-gfx-mmio / Apple PVG
```

The PCIe reference geometry remains ECAM `0x40000000/0x10000000`, MMIO `0x50000000/0x1fff0000`, and 16 GPEX interrupt lines at SPI 32 through 47.

Pinned Inferno already includes VMApple's macOS XHCI compatibility defaults: virtio legacy transport is disabled and `conditional-intr-mapping=on` is applied to XHCI. Therefore no P3.05 USB backport is required.

The Apple AES public model remains partial but explicit. KEY, IV, DATA, STORE_IV and FLAG are implemented; DSB, SKG and WRITE_REG are declared but not implemented and remain runtime-evidence gated. Public builtin-key constants are classified as emulator placeholders, not authentic Apple secrets.

Apple PVG directly depends on Apple's ParavirtualizedGraphics and Metal host frameworks. P1.05's `qdev_try_new` optionalization remains the portability policy: use real PVG when present, otherwise warn and continue without graphics. No fake GPU is introduced and no modern macOS graphics compatibility is claimed.

P3.05 adds no new Inferno patch.

Project files:

```text
.docs/P3.05.md
.src/.configs/p3.05-peripheral-contract.json
.src/.tools/platform-peripheral-contract.py
.src/.tools/prepare-p3.05.sh
```

## P3.06 — Part 03 Integration Gate

Status: **Next — final Part 03 objective**

P3.06 combines the P3.01–P3.05 platform contracts with the closed Part 02 CPU compatibility layer and Part 01 evidence pipeline, verifies ownership/integration invariants, and closes Part 03 without extending the objective count.

After P3.06, Part 03 is closed.

## Evidence rules

The project continues to use this ordering:

1. reproducible Part 01 A/B runtime evidence when available;
2. public XNU source;
3. pinned Inferno/QEMU source and official QEMU documentation;
4. Asahi/m1n1 source and authorized traces where relevant;
5. clearly labeled hypotheses.

Presence in source does not by itself prove boot criticality.

## Testing rule

No manual maintainer test is required for individual Part 03 objectives.

Development-side validation may inspect source locks, contracts and deterministic summaries. Real VMApple/macOS execution remains deferred to final integrated testing.

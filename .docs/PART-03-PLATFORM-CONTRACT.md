# Part 03 — VMApple Platform Contract

Project version: **`3.5.0.0.0.0`**

Status: **Closed — P3.01 through P3.06 implementation complete; real guest/runtime validation remains deferred**

## Purpose

Part 01 established the VMApple/TCG evidence pipeline. Part 02 established the deliberate CPU compatibility contract. Part 03 owns the remaining non-CPU VMApple machine contract.

For every guest-visible platform component, Part 03 distinguishes ordinary QEMU/Arm infrastructure, VMApple-specific behavior, host-only Apple framework dependencies and behavior that still requires runtime evidence.

Apple-specific source code is not automatically classified as missing or boot-critical.

## Fixed objective count

Part 03 contains exactly six objectives:

```text
P3.01 — Platform Contract Inventory and Ownership Map
P3.02 — Configuration and Platform Identity Contract
P3.03 — Interrupt, Timer, Power and Console Contract
P3.04 — Boot Backdoor and Storage Contract
P3.05 — PCIe, Peripheral, Crypto and Graphics Contract
P3.06 — Part 03 Integration Gate
```

There is **no P3.07**.

All six objectives are complete.

## Ownership model

Part 03 uses four ownership classes:

```text
generic_qemu
vmapple_specific
host_framework_dependent
unknown_requires_evidence
```

These describe where behavior comes from, not whether it is correct.

### `generic_qemu`

Existing generic QEMU/Arm hardware used by VMApple, including GICv3, PL011, PL031, PL061, GPEX PCIe, XHCI and ordinary virtio infrastructure.

Default action: preserve or validate.

### `vmapple_specific`

Behavior that intentionally models the VMApple virtual-Mac contract, including the configuration region, BDIF boot backdoor, Apple-flavored virtio block and Apple AES device.

Default action: validate against evidence before changing semantics.

### `host_framework_dependent`

Behavior whose reference implementation relies on host-only Apple frameworks, represented by Apple PVG graphics.

Default action: defer or investigate.

### `unknown_requires_evidence`

A contract boundary whose presence is known but whose exact runtime requirement is not established.

Default action: investigate or defer.

## Completed objectives

### P3.01 — Platform Contract Inventory and Ownership Map

P3.01 source-locks the VMApple machine/device files and XNU VMApple platform configuration, then assigns the remaining non-CPU platform to explicit owners.

Project files:

```text
.docs/P3.01.md
.src/.configs/p3.01-platform-contract.json
.src/.tools/platform-contract.py
.src/.tools/prepare-p3.01.sh
```

### P3.02 — Configuration and Platform Identity Contract

P3.02 freezes the config-region field ownership model, provides privacy-safe local identity-profile tooling and records the unresolved `cpu_ids[0x80]` versus adjacent source-comment layout discrepancy without guessing a fix.

Project files:

```text
.docs/P3.02.md
.src/.configs/p3.02-identity-contract.json
.src/.configs/p3.02-identity.example.json
.src/.tools/platform-identity.py
.src/.tools/prepare-p3.02.sh
```

### P3.03 — Interrupt, Timer, Power and Console Contract

P3.03 freezes the generic-device wiring:

```text
GICv3 distributor       0x10000000
GICv3 redistributors    0x10010000
virtual timer           PPI 27
PL011 UART               0x20010000 / SPI 1
PL031 RTC                0x20050000 / SPI 2
PL061 GPIO/power         0x20060000 / SPI 5 / pin 3
pvpanic MMIO             0x20070000 / no IRQ
```

Exact power-button event semantics remain evidence-gated.

Project files:

```text
.docs/P3.03.md
.src/.configs/p3.03-io-contract.json
.src/.tools/platform-io-contract.py
.src/.tools/prepare-p3.03.sh
```

### P3.04 — Boot Backdoor and Storage Contract

P3.04 freezes VMApple's two-stage storage model:

```text
pre-boot: BDIF MMIO/DMA reads over AUX/root backends
runtime:  vmapple-virtio-blk-pci variant=aux/root
```

BDIF writes remain unsupported pending evidence and the current Apple barrier remains a successful no-op with real flush semantics unresolved.

Project files:

```text
.docs/P3.04.md
.src/.configs/p3.04-storage-contract.json
.src/.tools/platform-storage-contract.py
.src/.tools/prepare-p3.04.sh
```

### P3.05 — PCIe, Peripheral, Crypto and Graphics Contract

P3.05 freezes the remaining peripheral boundary:

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

Pinned Inferno already contains VMApple's macOS XHCI conditional-interrupter workaround. Apple AES DSB/SKG/WRITE_REG remain unimplemented/evidence-gated. P1.05 keeps real PVG optional and no fake GPU is introduced.

Project files:

```text
.docs/P3.05.md
.src/.configs/p3.05-peripheral-contract.json
.src/.tools/platform-peripheral-contract.py
.src/.tools/prepare-p3.05.sh
```

### P3.06 — Part 03 Integration Gate

P3.06 closes Part 03 by binding all five preceding platform contracts to the passing P2.06 CPU integration state and the Part 01 runtime evidence/promotion path.

It requires:

```text
machine       vmapple
accelerator   tcg
CPU           apple-gxf
control CPU   max
live Apple sysreg policies  0
```

The gate runs all P3.01–P3.05 validators, checks cross-contract fail-closed invariants, verifies the exact patch series still stops at `0005`, and produces a deterministic platform integration manifest/fingerprint.

Project files:

```text
.docs/P3.06.md
.src/.configs/p3.06-integration-policy.json
.src/.tools/platform-integration-gate.py
.src/.tools/prepare-p3.06.sh
.src/.tools/run-p3.06-probe.sh
```

The runtime wrapper deliberately delegates through:

```text
P3.06 -> P2.06 -> P1.07
```

rather than creating another launch implementation. P1.09/P1.10 remain authoritative for real evidence and divergence promotion.

## Final patch state

Part 03 adds no new source patch. The complete ordered compatibility series remains:

```text
0001-vmapple-decouple-build-from-hvf.patch
0002-vmapple-optional-apple-pvg.patch
0003-arm-apple-sysreg-framework.patch
0004-arm-apple-sysreg-policy-model.patch
0005-arm-vmapple-feature-contract.patch
```

There is no Part 03 `0006` patch.

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

P3.06 provides the final deterministic preparation and delegated runtime gate, but Part 03 itself does not claim a successful macOS guest boot.

## Next progression point

Part 03 is closed.

```text
NEXT:
Part 04
P4.01
```

Part 04 begins from the integrated CPU + platform contract and moves into runtime evidence rather than extending Part 03's static machine-contract inventory.

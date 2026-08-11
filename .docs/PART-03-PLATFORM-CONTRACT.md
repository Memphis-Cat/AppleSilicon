# Part 03 — VMApple Platform Contract

Project version: **`3.0.0.0.0.0`**

Status: **Active — P3.01 implemented**

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

Existing generic QEMU/Arm hardware used by VMApple, such as GICv3, PL011, PL031 and PL061.

Default action: preserve or validate.

### `vmapple_specific`

Project/device behavior that intentionally models the VMApple virtual-Mac contract, such as the configuration region, boot backdoor and Apple-flavored virtio block device.

Default action: validate against evidence before changing semantics.

### `host_framework_dependent`

A path whose original implementation relies on host-only Apple frameworks, currently represented by Apple PVG graphics.

Default action: defer or investigate.

### `unknown_requires_evidence`

A contract boundary whose presence is known but whose exact runtime requirement is not established.

Default action: investigate or defer.

## P3.01 — Platform Contract Inventory and Ownership Map

Status: **Implementation complete — static ownership map**

P3.01 source-locks the pinned Inferno VMApple machine/device files and XNU's public VMApple platform configuration, then creates a machine-readable map covering:

```text
machine memory map
pre-boot firmware window
configuration and identity
GICv3
virtual timer
PL011 console
PL031 RTC
PL061 GPIO/power
pvpanic
VMApple BDIF boot backdoor
VMApple virtio block
PCIe
XHCI/USB
virtio networking
VMApple AES
Apple PVG graphics
```

The inventory records ownership, Part 03 owner, current source state, evidence and the allowed next action.

Project files:

```text
.docs/P3.01.md
.src/.configs/p3.01-platform-contract.json
.src/.tools/platform-contract.py
.src/.tools/prepare-p3.01.sh
```

## P3.02 — Configuration and Platform Identity Contract

Status: **Next**

P3.02 owns the VMApple configuration region and the guest-visible semantics of CPU count, RAM size, ECID/UUID linkage, random field, MAC identities, CPU IDs, serial, model and SoC-name fields.

It must distinguish fields that merely exist in the reference implementation from fields whose exact value or behavior is actually required.

## P3.03 — Interrupt, Timer, Power and Console Contract

Status: **Planned**

P3.03 owns GICv3 layout/wiring, generic virtual timer routing, PL011 console, PL031 RTC, PL061 GPIO/power and diagnostic pvpanic behavior.

## P3.04 — Boot Backdoor and Storage Contract

Status: **Planned**

P3.04 owns the VMApple BDIF pre-boot backdoor and VMApple-specific virtio block extensions for AUX/root storage.

## P3.05 — PCIe, Peripheral, Crypto and Graphics Contract

Status: **Planned**

P3.05 owns generic PCIe/peripheral validation plus Apple-specific AES and the host-framework-dependent Apple PVG graphics path.

## P3.06 — Part 03 Integration Gate

Status: **Planned — final Part 03 objective**

P3.06 combines validated Part 03 platform contracts with the closed Part 02 CPU compatibility layer and Part 01 evidence pipeline.

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

No manual maintainer test is required for P3.01.

Development-side validation may inspect source locks, contracts and deterministic summaries. Real VMApple/macOS execution remains deferred to final integrated testing.

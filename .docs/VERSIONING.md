# Versioning

AppleSilicon uses a six-field version number:

```text
MAJOR.UPDATE.EMERGENCY.FIX.RESERVED.HOTFIX
```

## Fields

1. **MAJOR** — very large project update or subsystem generation.
2. **UPDATE** — normal meaningful project update.
3. **EMERGENCY** — critically urgent release of any size.
4. **FIX** — small corrective release larger than a hotfix.
5. **RESERVED** — not assigned; remains `0` until formally defined.
6. **HOTFIX** — extremely small correction.

## Current version

```text
3.3.0.0.0.0
```

This normal update implements P3.04, **Boot Backdoor and Storage Contract**.

P3.04 freezes VMApple's two-phase storage path: the BDIF MMIO/DMA pre-boot backdoor and the later Apple-flavored `vmapple-virtio-blk-pci` AUX/root devices. It locks the BDIF window/register/selectors, 512-byte sector and 128 MiB request limits, read-only observed pre-boot behavior, reference backend topology, Apple PCI identity `106b:1a00`, AUX/root variants, Apple type-field placement and the current successful no-op Apple barrier.

Pinned Inferno and upstream QEMU 11.1.0 retain the same relevant semantics, so P3.04 adds no new Inferno patch. BDIF write requirements and real barrier/flush ordering remain runtime-evidence gated rather than inferred.

Part 03 remains fixed at exactly six objectives:

```text
P3.01 — Platform Contract Inventory and Ownership Map
P3.02 — Configuration and Platform Identity Contract
P3.03 — Interrupt, Timer, Power and Console Contract
P3.04 — Boot Backdoor and Storage Contract
P3.05 — PCIe, Peripheral, Crypto and Graphics Contract
P3.06 — Part 03 Integration Gate
```

There is no P3.07.

P3.05 is next.

No real macOS/HVF/TCG guest execution is claimed for P3.04. The repository root `README.md` remains intentionally unchanged.

## Reset behavior

When a higher-order field increments, lower non-reserved fields normally reset to zero unless an emergency release requires preserving a specific lineage.

Examples:

```text
0.1.0.0.0.7 -> 0.1.0.1.0.0
0.1.0.4.0.3 -> 0.2.0.0.0.0
0.9.0.0.0.0 -> 1.0.0.0.0.0
1.9.0.0.0.0 -> 2.0.0.0.0.0
2.3.0.0.0.0 -> 2.4.0.0.0.0
2.4.0.0.0.0 -> 2.5.0.0.0.0
2.5.0.0.0.0 -> 3.0.0.0.0.0
3.0.0.0.0.0 -> 3.1.0.0.0.0
3.1.0.0.0.0 -> 3.2.0.0.0.0
3.2.0.0.0.0 -> 3.3.0.0.0.0
```

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
3.2.0.0.0.0
```

This normal update implements P3.03, **Interrupt, Timer, Power and Console Contract**.

P3.03 freezes the stable VMApple generic-device wiring for GICv3, per-vCPU virtual timer PPI 27, PL011 UART, PL031 RTC, PL061 GPIO/power and MMIO pvpanic. XNU's source-locked VMApple configuration independently confirms GICv3 and PL011 and defines the `0x20000` GIC redistributor-per-PE size.

Pinned Inferno and upstream QEMU 11.1.0 retain the same relevant VMApple address/interrupt wiring, so P3.03 adds no new Inferno patch. Generic devices are preserved until runtime evidence proves a concrete incompatibility. Exact power-button event semantics remain evidence-gated.

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

P3.04 is next.

No real macOS/HVF/TCG guest execution is claimed for P3.03. The repository root `README.md` remains intentionally unchanged.

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
```

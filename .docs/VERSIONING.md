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
3.0.0.0.0.0
```

This major update starts Part 03, **VMApple Platform Contract**, and implements P3.01, **Platform Contract Inventory and Ownership Map**.

P3.01 source-locks the non-CPU VMApple machine/device baseline, creates a machine-readable inventory of the platform contract, and assigns each component to one later Part 03 objective using four ownership classes:

```text
generic_qemu
vmapple_specific
host_framework_dependent
unknown_requires_evidence
```

The inventory deliberately has no automatic `implement` action. Apple-specific presence does not by itself prove a missing or boot-critical behavior.

Part 03 is fixed at exactly six objectives:

```text
P3.01 — Platform Contract Inventory and Ownership Map
P3.02 — Configuration and Platform Identity Contract
P3.03 — Interrupt, Timer, Power and Console Contract
P3.04 — Boot Backdoor and Storage Contract
P3.05 — PCIe, Peripheral, Crypto and Graphics Contract
P3.06 — Part 03 Integration Gate
```

There is no P3.07.

P3.02 is next.

No real macOS/HVF/TCG guest execution is claimed for P3.01. The repository root `README.md` remains intentionally unchanged.

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
```

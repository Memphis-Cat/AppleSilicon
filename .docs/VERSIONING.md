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
3.1.0.0.0.0
```

This normal update implements P3.02, **Configuration and Platform Identity Contract**.

P3.02 source-locks the VMApple configuration-region behavior, records the structural versus reference-default identity fields, adds a privacy-safe local identity profile compiler, and preserves machine-derived CPU count, RAM size, random value and CPU-ID generation.

It also records an unresolved source-layout discrepancy between the declared `uint32_t cpu_ids[0x80]` array and the adjacent offsets documented for `scratch`, `serial`, `model` and `soc_name`. The discrepancy remains evidence-gated; P3.02 does not patch the layout from inference alone.

No Inferno source patch is required for P3.02 because existing QEMU device properties and `-global` configuration are sufficient to express controlled identity experiments.

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

P3.03 is next.

No real macOS/HVF/TCG guest execution or real platform identity is claimed for P3.02. The repository root `README.md` remains intentionally unchanged.

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
```

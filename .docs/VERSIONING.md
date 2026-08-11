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
3.5.0.0.0.0
```

This normal update implements P3.06, **Part 03 Integration Gate**, and closes Part 03.

P3.06 binds the five completed VMApple platform contracts to the closed P2.06 CPU integration manifest and the Part 01 runtime evidence/promotion pipeline. It runs every P3.01–P3.05 validator, enforces machine-wide fail-closed invariants, proves the ordered patch series still ends at `0005`, and emits a deterministic platform integration fingerprint.

Unknown semantics remain unresolved rather than fabricated: P3.02's config-layout discrepancy, P3.03 power-button behavior, P3.04 BDIF writes/barrier flush semantics, and P3.05 AES DSB/SKG/WRITE_REG behavior remain runtime-evidence gated. P1.05's optional real-PVG policy is preserved and no fake GPU is introduced.

Part 03 is now closed at exactly six objectives:

```text
P3.01 — Platform Contract Inventory and Ownership Map
P3.02 — Configuration and Platform Identity Contract
P3.03 — Interrupt, Timer, Power and Console Contract
P3.04 — Boot Backdoor and Storage Contract
P3.05 — PCIe, Peripheral, Crypto and Graphics Contract
P3.06 — Part 03 Integration Gate
```

There is no P3.07.

The next progression point is:

```text
Part 04
P4.01
```

No real macOS/HVF/TCG guest execution is claimed by the P3.06 development-side gate. The repository root `README.md` remains intentionally unchanged.

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
3.3.0.0.0.0 -> 3.4.0.0.0.0
3.4.0.0.0.0 -> 3.5.0.0.0.0
```

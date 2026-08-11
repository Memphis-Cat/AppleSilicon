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
2.5.0.0.0.0
```

This normal update implements P2.06, **Part 02 Integration Gate**, and closes Part 02.

P2.06 binds the validated Part 02 CPU compatibility component to the Part 01 VMApple/TCG probe and evidence pipeline. It requires a passing P2.05 deterministic regression, prepares the exact pinned Inferno source with patches `0001` through `0005`, validates `vmapple + TCG + apple-gxf` integration invariants, and emits:

```text
.build/p2.06/integration-manifest.json
```

The integration manifest has a deterministic SHA-256 integration fingerprint and records that Part 02 is implementation-complete and closed.

The runtime wrapper reuses the P1.07 probe after capability-gating `vmapple`, TCG and `apple-gxf`; observational runtime results remain subject to the Part 01 evidence and promotion gates.

No real macOS/HVF/TCG guest execution is claimed for P2.06 implementation completion.

Part 02 remains fixed at six objectives and is now closed. There is no P2.07.

The next progression point is:

```text
Part 03 — VMApple Platform Contract
P3.01 — Platform Contract Inventory and Ownership Map
```

The repository root `README.md` remains intentionally unchanged.

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
```

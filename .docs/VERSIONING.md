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
4.5.0.0.0.0
```

This update implements P4.06, **Part 04 Runtime Evidence Gate**, the final planned implementation objective.

P4.06 validates P4.01 through P4.05, preserves the five-patch Inferno chain, and distinguishes planned implementation completion from real runtime evidence validation.

Without real runtime artifacts the expected classification is:

```text
P4_06_IMPLEMENTATION_COMPLETE_RUNTIME_EVIDENCE_PENDING
```

This closes the planned implementation roadmap while keeping runtime validation explicitly pending.

The future runtime gate requires at least two independent P4.04 sessions and accepts either reproduced trace equivalence within the configured capture scope or one reproducible divergence backed by the exact P4.05/P1.10 promotion record.

Part 04 is fixed at exactly six objectives:

```text
P4.01 — Runtime Session Provenance and Input Lock
P4.02 — Integrated TCG Probe Capture
P4.03 — Apple Silicon HVF Reference Capture
P4.04 — Comparable A/B Session Assembly
P4.05 — Reproducible Divergence Promotion
P4.06 — Part 04 Runtime Evidence Gate
```

There is no P4.07 and no automatically defined Part 05.

The repository root `README.md` remains intentionally unchanged. P4.06 adds no Inferno patch, and no real runtime pass is claimed during implementation.

## Reset behavior

When a higher-order field increments, lower non-reserved fields normally reset to zero unless an emergency release requires preserving a specific lineage.

Examples:

```text
0.9.0.0.0.0 -> 1.0.0.0.0.0
1.9.0.0.0.0 -> 2.0.0.0.0.0
2.5.0.0.0.0 -> 3.0.0.0.0.0
3.5.0.0.0.0 -> 4.0.0.0.0.0
```

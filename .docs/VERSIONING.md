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
2.4.0.0.0.0
```

This normal update implements P2.05, **Deterministic CPU Contract Regression Harness**.

P2.05 does not add new guest-visible CPU behavior. It locks the exact Part 02 contracts/patches through P2.04, cross-checks their invariants, prepares the complete ordered patch series on the pinned Inferno source, inspects the resulting TCG `apple-gxf` integration, and emits a deterministic CPU-contract regression result with a SHA-256 suite fingerprint.

The canonical result is written to:

```text
.build/p2.05/cpu-contract-regression.json
```

The logged harness runs the regression twice against the same prepared source and requires byte-identical JSON. Unknown Apple implementation-defined sysreg semantics remain fail-closed and P2.03's live semantic policy count remains zero.

Real macOS/HVF/TCG guest execution remains deferred under the final-integration testing rule.

Part 02 remains fixed at six objectives. P2.06 is next and is the final Part 02 objective. There is no P2.07.

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
```

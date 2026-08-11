# Versioning

AppleSilicon uses a six-field version number:

```text
MAJOR.UPDATE.EMERGENCY.FIX.RESERVED.HOTFIX
```

Example:

```text
0.1.0.0.0.0
```

## Fields

### 1 — MAJOR

A very large project update. Increment this when a major subsystem or project generation changes substantially.

Example:

```text
1.0.0.0.0.0
```

### 2 — UPDATE

A normal project update. This is used for meaningful additions that are not large enough to be a major update.

Example:

```text
0.2.0.0.0.0
```

### 3 — EMERGENCY

A critical release that must happen immediately. Its size does not matter: an emergency release may contain a one-line correction or a major architectural repair.

Example:

```text
0.1.1.0.0.0
```

### 4 — FIX

A small corrective release, larger or more meaningful than a hotfix but still primarily a fix.

Example:

```text
0.1.0.1.0.0
```

### 5 — RESERVED

The fifth field has not yet been assigned a release meaning. It remains `0` until the project formally defines it. This avoids inventing a category that was not part of the original versioning rules.

### 6 — HOTFIX

A very, very small correction.

Example:

```text
0.1.0.0.0.1
```

## Current version

```text
0.8.0.0.0.0
```

This update implements P1.08, **VMApple Trace Normalization and Earliest-Divergence Extraction**.

P1.08 adds a standard-library Python trace normalizer/comparator, conservative removal of QEMU host-runtime noise, preservation of guest MMIO semantics, bounded trace resynchronization, first-divergence classification, Markdown/JSON candidate reports, sanitized fixtures, and a mandatory logged development-validation harness.

Real Apple/HVF and TCG VMApple trace collection remains intentionally deferred under the project owner's final-testing-only rule. Synthetic fixture results must never be promoted into a real `P01-DIVERGENCE-0001`.

The root `README.md` is intentionally not version-updated in this release under the project owner's instruction.

## Reset behavior

When a higher-order field increments, lower non-reserved fields normally reset to zero unless an emergency release requires preserving a specific lineage.

Examples:

```text
0.1.0.0.0.7 -> 0.1.0.1.0.0
0.1.0.4.0.3 -> 0.2.0.0.0.0
0.9.0.0.0.0 -> 1.0.0.0.0.0
```

Emergency releases are intentionally allowed to break the normal cadence because urgency is the defining property of that field.

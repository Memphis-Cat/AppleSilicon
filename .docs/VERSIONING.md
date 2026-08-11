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
1.0.0.0.0.0
```

This major update implements P1.10, **Controlled A/B Evidence Bundle and Divergence Promotion Gate**, and closes the Part 01 implementation sequence.

P1.10 connects the P1.09 manifest contract, P1.08 trace comparator, P1.07 probe evidence, and P1.09 HVF reference evidence into a fail-closed candidate/promotion pipeline. It verifies trace-artifact hashes, blocks synthetic/example evidence, fingerprints the full comparison contract, derives a stable earliest-divergence signature, and requires at least two unique matching runtime A/B reproductions before a local `P01-DIVERGENCE-0001` record can be created.

P1.10 also adds a post-run probe collector so an already completed P1.07 runtime can be converted into the P1.09 probe-manifest contract without rerunning QEMU.

Real VM execution and real divergence promotion remain intentionally deferred under the project owner's final-testing-only rule.

The root `README.md` remains intentionally unchanged.

## Reset behavior

When a higher-order field increments, lower non-reserved fields normally reset to zero unless an emergency release requires preserving a specific lineage.

Examples:

```text
0.1.0.0.0.7 -> 0.1.0.1.0.0
0.1.0.4.0.3 -> 0.2.0.0.0.0
0.9.0.0.0.0 -> 1.0.0.0.0.0
```

Emergency releases are intentionally allowed to break the normal cadence because urgency is the defining property of that field.

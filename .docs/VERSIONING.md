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
2.0.0.0.0.0
```

This major update begins **Part 02 — Apple CPU Compatibility Contract** and implements P2.01, **Apple CPU System Register and Feature Inventory**.

P2.01 locks exact XNU, QEMU, m1n1 and Inferno source identities; records a machine-readable CPU-focused Apple implementation-defined register inventory; distinguishes physical-Apple register evidence from VMApple requirements; and adds a deterministic validator plus logged preparation harness.

No register is marked runtime-required and no reset/read/write semantics are invented in P2.01. Real guest execution remains deferred under the maintainer's final-integration testing rule.

Part 02 has a fixed six-objective sequence and ends at P2.06. There is no P2.07.

The root `README.md` remains intentionally unchanged.

## Reset behavior

When a higher-order field increments, lower non-reserved fields normally reset to zero unless an emergency release requires preserving a specific lineage.

Examples:

```text
0.1.0.0.0.7 -> 0.1.0.1.0.0
0.1.0.4.0.3 -> 0.2.0.0.0.0
0.9.0.0.0.0 -> 1.0.0.0.0.0
1.9.0.0.0.0 -> 2.0.0.0.0.0
```

Emergency releases are intentionally allowed to break the normal cadence because urgency is the defining property of that field.

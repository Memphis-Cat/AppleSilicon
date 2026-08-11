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
2.1.0.0.0.0
```

This normal update implements P2.02, **Apple System Register Emulation Framework**.

P2.02 adds the project-owned AArch64 Apple system-register framework patch, uses QEMU/Inferno's real `ARMCPRegInfo` registration path, attaches the framework only to the TCG `apple-gxf` CPU path, and provides an explicit fail-closed undefined-access helper for future evidence-backed policies.

P2.02 intentionally installs zero guest-visible Apple register policies by default. It does not invent reset values, constants, read-as-zero behavior, write-ignore behavior, stored state, or VMApple-required status. Those semantics belong to P2.03.

A logged development-side preparation harness validates the ordered patch series in a disposable Inferno tree. Real guest execution remains deferred under the maintainer's final-integration testing rule.

Part 02 remains fixed at six objectives and ends at P2.06. P2.03 is next.

The root `README.md` remains intentionally unchanged.

## Reset behavior

When a higher-order field increments, lower non-reserved fields normally reset to zero unless an emergency release requires preserving a specific lineage.

Examples:

```text
0.1.0.0.0.7 -> 0.1.0.1.0.0
0.1.0.4.0.3 -> 0.2.0.0.0.0
0.9.0.0.0.0 -> 1.0.0.0.0.0
1.9.0.0.0.0 -> 2.0.0.0.0.0
2.0.0.0.0.0 -> 2.1.0.0.0.0
```

Emergency releases are intentionally allowed to break the normal cadence because urgency is the defining property of that field.

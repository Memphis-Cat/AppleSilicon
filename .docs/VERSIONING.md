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
0.9.0.0.0.0
```

This update implements P1.09, **Reference Trace Manifest and Real-Hardware Trace Preparation**.

P1.09 adds a privacy-safe evidence manifest policy, reference/probe example manifests, a standard-library collector/validator/pairing tool, automatic SHA-256/size recording for local guest inputs and evidence artifacts, a fail-closed Apple-Silicon/HVF reference runner, and a logged development-side validation harness.

The pairing contract makes the pinned Inferno revision, VMApple shape, RAM/SMP, trace/debug sets, and local guest-input hashes equal across the reference and probe while allowing the intended host/accelerator/CPU differences.

m1n1 is documented only as a secondary real-hardware escalation path for behavior that public source and the primary VMApple/HVF reference cannot explain. No real QEMU, macOS, HVF, or m1n1 execution is performed by the P1.09 preparation path.

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

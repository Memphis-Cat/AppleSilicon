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
4.0.0.0.0.0
```

This major update begins Part 04 and implements P4.01, **Runtime Session Provenance and Input Lock**.

Parts 01–03 are closed. P4.01 binds every future runtime session to a passing P3.06 platform integration fingerprint, exact local QEMU executable digest/version/capabilities, local guest-input digests, a redacted machine-UUID digest and the existing Part 01 trace contract before a guest is allowed to run.

The generated session plan is deterministic provenance metadata, not runtime evidence. Raw local paths, UUIDs, machine-identity/hardware-model content and guest artifacts remain local.

Part 04 is fixed at exactly six objectives:

```text
P4.01 — Runtime Session Provenance and Input Lock
P4.02 — Integrated TCG Probe Capture
P4.03 — Apple Silicon HVF Reference Capture
P4.04 — Comparable A/B Session Assembly
P4.05 — Reproducible Divergence Promotion
P4.06 — Part 04 Runtime Evidence Gate
```

There is no P4.07. P4.02 is next.

P4.01 adds no Inferno patch and launches no guest. The repository root `README.md` remains intentionally unchanged.

## Reset behavior

When a higher-order field increments, lower non-reserved fields normally reset to zero unless an emergency release requires preserving a specific lineage.

Examples:

```text
0.9.0.0.0.0 -> 1.0.0.0.0.0
1.9.0.0.0.0 -> 2.0.0.0.0.0
2.5.0.0.0.0 -> 3.0.0.0.0.0
3.5.0.0.0.0 -> 4.0.0.0.0.0
```

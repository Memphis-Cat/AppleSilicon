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
4.2.0.0.0.0
```

This update implements P4.03, **Apple Silicon HVF Reference Capture**.

P4.03 adds a provenance-bound primary reference path for:

```text
vmapple
HVF
host CPU
Darwin arm64
4G RAM
4 vCPUs
30-second observation
```

The reference host requirement is fail-closed. An Intel Mac/Hackintosh or synthetic substitute cannot be accepted as the primary P4.03 reference.

P4.03 reuses the existing P1.09 reference runner and manifest policy; it does not add another HVF launcher or another evidence schema. The P4.03 capture descriptor binds the P1.09 manifest plus the separately hashed launcher log, repeats provenance after execution and cannot promote a divergence.

Part 04 remains fixed at exactly six objectives:

```text
P4.01 — Runtime Session Provenance and Input Lock
P4.02 — Integrated TCG Probe Capture
P4.03 — Apple Silicon HVF Reference Capture
P4.04 — Comparable A/B Session Assembly
P4.05 — Reproducible Divergence Promotion
P4.06 — Part 04 Runtime Evidence Gate
```

There is no P4.07. P4.04 is next.

P4.03 adds no Inferno patch and no real Apple Silicon/HVF guest was launched while implementing it. The repository root `README.md` remains intentionally unchanged.

## Reset behavior

When a higher-order field increments, lower non-reserved fields normally reset to zero unless an emergency release requires preserving a specific lineage.

Examples:

```text
0.9.0.0.0.0 -> 1.0.0.0.0.0
1.9.0.0.0.0 -> 2.0.0.0.0.0
2.5.0.0.0.0 -> 3.0.0.0.0.0
3.5.0.0.0.0 -> 4.0.0.0.0.0
```

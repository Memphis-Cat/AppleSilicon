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
4.3.0.0.0.0
```

This update implements P4.04, **Comparable A/B Session Assembly**.

P4.04 admits one P4.03 Apple-Silicon/HVF reference capture and one P4.02 TCG/`apple-gxf` probe capture only after their P4.01 plans, capture fingerprints and authoritative P1.09 manifests all agree on the comparison contract.

Additional P4.04 equality includes the P3.06 manifest/fingerprint, hashed machine UUID and QEMU version string. Host, accelerator, CPU and host-specific QEMU executable digest/size remain intentional role differences.

The deterministic A/B bundle is assembled twice and must be byte-identical. P4.04 does not compare traces and cannot promote a divergence; P1.08 and P1.10 remain authoritative.

Part 04 remains fixed at exactly six objectives:

```text
P4.01 — Runtime Session Provenance and Input Lock
P4.02 — Integrated TCG Probe Capture
P4.03 — Apple Silicon HVF Reference Capture
P4.04 — Comparable A/B Session Assembly
P4.05 — Reproducible Divergence Promotion
P4.06 — Part 04 Runtime Evidence Gate
```

There is no P4.07. P4.05 is next.

P4.04 adds no Inferno patch and no real A/B pair was assembled while implementing it because runtime P4.02/P4.03 captures remain deferred. The repository root `README.md` remains intentionally unchanged.

## Reset behavior

When a higher-order field increments, lower non-reserved fields normally reset to zero unless an emergency release requires preserving a specific lineage.

Examples:

```text
0.9.0.0.0.0 -> 1.0.0.0.0.0
1.9.0.0.0.0 -> 2.0.0.0.0.0
2.5.0.0.0.0 -> 3.0.0.0.0.0
3.5.0.0.0.0 -> 4.0.0.0.0.0
```

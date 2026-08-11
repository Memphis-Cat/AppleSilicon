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
4.1.0.0.0.0
```

This update implements P4.02, **Integrated TCG Probe Capture**.

P4.02 consumes the P4.01 probe session plan, locks the execution to `vmapple` + TCG + `apple-gxf`, 4 GiB RAM, 4 vCPUs and a 30-second observation window, then reuses the existing P3.06 → P2.06 → P1.07 runtime chain.

After a completed observational run it reuses the Part 01 probe collector to create a validated P1.09 manifest, repeats the provenance preflight, requires byte-identical pre/post results and emits a sanitized P4.02 capture descriptor.

No divergence is promoted by P4.02. P1.10 remains authoritative for promotion.

Part 04 remains fixed at exactly six objectives:

```text
P4.01 — Runtime Session Provenance and Input Lock
P4.02 — Integrated TCG Probe Capture
P4.03 — Apple Silicon HVF Reference Capture
P4.04 — Comparable A/B Session Assembly
P4.05 — Reproducible Divergence Promotion
P4.06 — Part 04 Runtime Evidence Gate
```

There is no P4.07. P4.03 is next.

P4.02 adds no Inferno source patch. Real TCG execution is intentionally deferred to final integrated testing. The repository root `README.md` remains intentionally unchanged.

## Reset behavior

When a higher-order field increments, lower non-reserved fields normally reset to zero unless an emergency release requires preserving a specific lineage.

Examples:

```text
0.9.0.0.0.0 -> 1.0.0.0.0.0
1.9.0.0.0.0 -> 2.0.0.0.0.0
2.5.0.0.0.0 -> 3.0.0.0.0.0
3.5.0.0.0.0 -> 4.0.0.0.0.0
4.0.0.0.0.0 -> 4.1.0.0.0.0
```

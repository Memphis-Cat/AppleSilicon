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
4.4.0.0.0.0
```

This update implements P4.05, **Reproducible Divergence Promotion**.

P4.05 consumes at least two independent P4.04-admitted A/B runtime sessions, regenerates one P1.10 candidate from each exact manifest/trace pair, requires the same divergence signature and P1.09 contract fingerprint, then delegates promotion to the existing P1.10 `promote` command.

Independence is stronger than simple pair uniqueness: the A/B fingerprints, reference run IDs, probe run IDs, reference capture fingerprints and probe capture fingerprints must all differ. The P4.04 shared contract and exact role-specific QEMU binaries must remain fixed across reproductions.

The authoritative promotion remains `P01-DIVERGENCE-0001`; P1.10 auto-commit remains disabled. P4.05 adds no Inferno patch and does not claim a real promoted divergence during implementation because two independent real runtime reproductions have not been supplied.

Part 04 remains fixed at exactly six objectives:

```text
P4.01 — Runtime Session Provenance and Input Lock
P4.02 — Integrated TCG Probe Capture
P4.03 — Apple Silicon HVF Reference Capture
P4.04 — Comparable A/B Session Assembly
P4.05 — Reproducible Divergence Promotion
P4.06 — Part 04 Runtime Evidence Gate
```

There is no P4.07. P4.06 is next and is the final Part 04 objective.

The repository root `README.md` remains intentionally unchanged.

## Reset behavior

When a higher-order field increments, lower non-reserved fields normally reset to zero unless an emergency release requires preserving a specific lineage.

Examples:

```text
0.9.0.0.0.0 -> 1.0.0.0.0.0
1.9.0.0.0.0 -> 2.0.0.0.0.0
2.5.0.0.0.0 -> 3.0.0.0.0.0
3.5.0.0.0.0 -> 4.0.0.0.0.0
```

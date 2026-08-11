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
2.3.0.0.0.0
```

This normal update implements P2.04, **CPU Feature and ID-Register Compatibility**.

P2.04 locks the public XNU VMApple architectural feature declarations and adds a project-owned minimum feature profile for the TCG `apple-gxf` CPU. The profile requires PAuth presence, SSBS2, SME/SME2, PAN3, 4 KiB and 16 KiB stage-1 translation granules, and range TLBI while preserving stronger capabilities inherited from QEMU `max`.

P2.04 does not alter the normal `max`, host/HVF or KVM CPU paths. It does not invent paravirtualized PAC/CTRR/GIC behavior and it does not add Apple implementation-defined sysreg semantics; P2.03's live semantic policy table remains empty.

A logged preparation harness validates the source locks and complete ordered patch series in a disposable Inferno source tree. Real guest execution remains deferred under the final-integration testing rule.

Part 02 remains fixed at six objectives. P2.05 is next and P2.06 is the final Part 02 objective.

The repository root `README.md` remains intentionally unchanged.

## Reset behavior

When a higher-order field increments, lower non-reserved fields normally reset to zero unless an emergency release requires preserving a specific lineage.

Examples:

```text
0.1.0.0.0.7 -> 0.1.0.1.0.0
0.1.0.4.0.3 -> 0.2.0.0.0.0
0.9.0.0.0.0 -> 1.0.0.0.0.0
1.9.0.0.0.0 -> 2.0.0.0.0.0
2.2.0.0.0.0 -> 2.3.0.0.0.0
```

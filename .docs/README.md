# AppleSilicon Documentation

Current project version: **`2.3.0.0.0.0`**

This directory records the research, design decisions, compatibility contracts, experiments and implementation objectives for AppleSilicon.

## Documents

- [VERSIONING.md](VERSIONING.md) — six-field project version format.
- [RESEARCH.md](RESEARCH.md) — research sources and prior-art findings.
- [ARCHITECTURE.md](ARCHITECTURE.md) — intended compatibility-layer architecture.
- [PART-01-BASELINE.md](PART-01-BASELINE.md) — closed Part 01 objective tree.
- [P1.01.md](P1.01.md) through [P1.10.md](P1.10.md) — completed Part 01 sequence.
- [PART-02-CPU-CONTRACT.md](PART-02-CPU-CONTRACT.md) — fixed Part 02 CPU compatibility objective tree.
- [P2.01.md](P2.01.md) — source-locked Apple CPU register/feature inventory.
- [P2.02.md](P2.02.md) — fail-closed Apple sysreg registration framework.
- [P2.03.md](P2.03.md) — evidence-gated read/write/reset/access policy model.
- [P2.04.md](P2.04.md) — VMApple architectural feature and ID-register minimum profile.

## Part boundaries

Part 01 closes at `P1.10`; there is no P1.11.

Part 02 is fixed at exactly P2.01 through P2.06; there is no P2.07.

## Current Part 02 state

```text
P2.01  complete
P2.02  complete
P2.03  complete
P2.04  complete
P2.05  NEXT
P2.06  final Part 02 objective
```

P2.04 derives the architectural CPU-visible minimum from the locked XNU `VMAPPLE.h` contract and scopes it to the TCG `apple-gxf` CPU. It covers PAuth presence, SSBS2, SME/SME2, PAN3, 4 KiB + 16 KiB stage-1 translation granules and range TLBI while preserving stronger QEMU `max` capabilities.

Apple implementation-defined sysreg semantics remain separate and P2.03's live semantic table remains empty until evidence promotes a concrete register behavior.

## Maintainer testing policy

The maintainer will not be asked to manually test individual objectives. Manual testing is reserved for the finished integrated project.

Development-side source inspection, compilation, static checks, automated tests, emulator probes, regression tests and trace comparisons remain expected where practical.

## Logging policy

Every meaningful executable AppleSilicon operation must leave a `.log` artifact under `.logs/` unless a later component explicitly documents another local output contract.

P2.04 adds `.src/.tools/prepare-p2.04.sh`, which validates the source locks, feature contract and ordered patch series without launching a macOS guest.

## Evidence policy

A source-known feature or register is not automatically a proven runtime blocker. VMApple requirements, architectural feature exposure and Apple implementation-defined semantics are kept separate until evidence connects them.

## Root README rule

The repository root `README.md` remains intentionally unchanged during this objective.

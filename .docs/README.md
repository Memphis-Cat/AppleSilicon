# AppleSilicon Documentation

Current project version: **`4.3.0.0.0.0`**

This directory records the research, design decisions, compatibility contracts, experiments and implementation objectives for AppleSilicon.

## Documents

- [VERSIONING.md](VERSIONING.md) — six-field project version format.
- [RESEARCH.md](RESEARCH.md) — research sources and prior-art findings.
- [ARCHITECTURE.md](ARCHITECTURE.md) — intended compatibility-layer architecture.
- [PART-01-BASELINE.md](PART-01-BASELINE.md) — closed Part 01 evidence/baseline tree.
- [P1.01.md](P1.01.md) through [P1.10.md](P1.10.md) — completed Part 01 sequence.
- [PART-02-CPU-CONTRACT.md](PART-02-CPU-CONTRACT.md) — closed Part 02 CPU compatibility tree.
- [P2.01.md](P2.01.md) through [P2.06.md](P2.06.md) — completed Part 02 sequence.
- [PART-03-PLATFORM-CONTRACT.md](PART-03-PLATFORM-CONTRACT.md) — closed Part 03 VMApple platform tree.
- [P3.01.md](P3.01.md) through [P3.06.md](P3.06.md) — completed Part 03 sequence.
- [PART-04-RUNTIME-EVIDENCE.md](PART-04-RUNTIME-EVIDENCE.md) — active fixed Part 04 runtime-evidence tree.
- [P4.01.md](P4.01.md) — runtime session provenance and input lock.
- [P4.02.md](P4.02.md) — integrated TCG probe capture.
- [P4.03.md](P4.03.md) — Apple Silicon HVF reference capture.
- [P4.04.md](P4.04.md) — comparable A/B session assembly.

## Part boundaries

Part 01 closes at `P1.10`; there is no P1.11.
Part 02 closes at `P2.06`; there is no P2.07.
Part 03 closes at `P3.06`; there is no P3.07.
Part 04 is fixed at `P4.01` through `P4.06`; there is no P4.07.

## Current Part 04 state

```text
P4.01  complete
P4.02  complete
P4.03  complete
P4.04  complete
P4.05  NEXT
P4.06  final Part 04 objective
```

P4.04 binds the P4.01 plans, P4.02/P4.03 capture descriptors and P1.09 manifests into one deterministic A/B admission record. It additionally requires equal machine-UUID digest, equal P3.06 state and equal QEMU version string while preserving the expected host/HVF-vs-TCG/CPU differences.

## Maintainer testing policy

The maintainer will not be asked to manually test individual objectives. Manual testing is reserved for the finished integrated project.

Development-side source inspection, compilation, static checks, automated tests, emulator probes, regression tests and trace comparisons remain expected where practical.

## Logging policy

Every meaningful executable AppleSilicon operation must leave a `.log` artifact under `.logs/` unless a later component explicitly documents another local output contract.

P4.04 provides a logged static preparation harness and logged deterministic A/B assembler.

## Evidence policy

P4.02/P4.03 capture descriptors establish runtime provenance. P4.04 establishes pair admissibility. Part 01 remains authoritative for actual trace normalization/comparison and divergence promotion.

## Root README rule

The repository root `README.md` remains intentionally unchanged during these objectives.

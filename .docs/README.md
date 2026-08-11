# AppleSilicon Documentation

Current project version: **`4.1.0.0.0.0`**

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

## Part boundaries

Part 01 closes at `P1.10`; there is no P1.11.
Part 02 closes at `P2.06`; there is no P2.07.
Part 03 closes at `P3.06`; there is no P3.07.
Part 04 is fixed at `P4.01` through `P4.06`; there is no P4.07.

## Current Part 04 state

```text
P4.01  complete
P4.02  complete
P4.03  NEXT
P4.04
P4.05
P4.06  final Part 04 objective
```

P4.01 establishes deterministic pre-execution provenance for both runtime roles.

P4.02 consumes the probe plan, fixes the TCG runtime parameters, delegates through the existing P3.06 → P2.06 → P1.07 chain, creates a validated P1.09 probe manifest, then requires post-run provenance to be byte-identical to pre-run provenance before producing a sanitized capture descriptor.

## Maintainer testing policy

The maintainer will not be asked to manually test individual objectives. Manual testing is reserved for the finished integrated project.

Development-side source inspection, compilation, static checks, automated tests, emulator probes, regression tests and trace comparisons remain expected where practical.

## Logging policy

Every meaningful executable AppleSilicon operation must leave a `.log` artifact under `.logs/` unless a later component explicitly documents another local output contract.

P4.01 provides logged planning. P4.02 provides a logged static preparation harness and logged runtime-capture wrapper. Real P4.02 guest execution remains deferred.

## Evidence policy

P4.02 capture metadata cannot promote a divergence. Part 01 remains authoritative for actual runtime manifests, comparability, trace normalization and divergence promotion.

## Root README rule

The repository root `README.md` remains intentionally unchanged during these objectives.

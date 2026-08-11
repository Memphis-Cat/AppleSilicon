# AppleSilicon Documentation

Current project version: **`4.5.0.0.0.0`**

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
- [PART-04-RUNTIME-EVIDENCE.md](PART-04-RUNTIME-EVIDENCE.md) — closed Part 04 runtime-evidence implementation tree.
- [P4.01.md](P4.01.md) through [P4.06.md](P4.06.md) — completed Part 04 implementation sequence.

## Part boundaries

Part 01 closes at `P1.10`; there is no P1.11.
Part 02 closes at `P2.06`; there is no P2.07.
Part 03 closes at `P3.06`; there is no P3.07.
Part 04 closes at `P4.06`; there is no P4.07.

## Current state

```text
P4.01  complete
P4.02  complete
P4.03  complete
P4.04  complete
P4.05  complete
P4.06  complete

planned implementation roadmap  complete
real runtime evidence validation pending
```

P4.06 does not fabricate a runtime pass. The implementation-only classification is `P4_06_IMPLEMENTATION_COMPLETE_RUNTIME_EVIDENCE_PENDING`.

The real runtime gate requires at least two independent P4.04 sessions and accepts either reproduced trace equivalence or a reproducible divergence promoted by P4.05/P1.10.

No Part 05 is automatically defined; further implementation work must be evidence-driven or explicitly scoped.

## Maintainer testing policy

Manual testing is reserved for the finished integrated project. The implementation roadmap is now complete; the remaining validation work is the real integrated runtime evidence run with the required local environments.

## Logging policy

Every meaningful executable AppleSilicon operation must leave a `.log` artifact under `.logs/` unless a component explicitly documents another local output contract.

P4.06 provides both a logged deterministic implementation-close harness and a logged deterministic runtime evaluator.

## Evidence policy

P4.02/P4.03 establish runtime provenance, P4.04 establishes pair admissibility, P4.05 establishes reproducible promotion, and P4.06 is the final evidence gate. P1.08/P1.09/P1.10 remain authoritative for trace comparison, pair comparability and promotion.

## Root README rule

The repository root `README.md` remains intentionally unchanged during these objectives.

# AppleSilicon Documentation

Current project version: **`3.5.0.0.0.0`**

This directory records the research, design decisions, compatibility contracts, experiments and implementation objectives for AppleSilicon.

## Documents

- [VERSIONING.md](VERSIONING.md) — six-field project version format.
- [RESEARCH.md](RESEARCH.md) — research sources and prior-art findings.
- [ARCHITECTURE.md](ARCHITECTURE.md) — intended compatibility-layer architecture.
- [PART-01-BASELINE.md](PART-01-BASELINE.md) — closed Part 01 evidence/baseline objective tree.
- [P1.01.md](P1.01.md) through [P1.10.md](P1.10.md) — completed Part 01 sequence.
- [PART-02-CPU-CONTRACT.md](PART-02-CPU-CONTRACT.md) — closed Part 02 CPU compatibility objective tree.
- [P2.01.md](P2.01.md) through [P2.06.md](P2.06.md) — completed Part 02 sequence.
- [PART-03-PLATFORM-CONTRACT.md](PART-03-PLATFORM-CONTRACT.md) — closed Part 03 platform-contract tree.
- [P3.01.md](P3.01.md) through [P3.06.md](P3.06.md) — completed Part 03 sequence.

## Part boundaries

Part 01 closes at `P1.10`; there is no P1.11.

Part 02 closes at `P2.06`; there is no P2.07.

Part 03 closes at `P3.06`; there is no P3.07.

## Closed Part 03 state

```text
P3.01  complete
P3.02  complete
P3.03  complete
P3.04  complete
P3.05  complete
P3.06  complete
```

P3.06 binds the source-locked Part 03 platform contracts to the closed P2.06 CPU integration state and the Part 01 evidence pipeline. It runs every Part 03 validator, enforces machine-wide fail-closed invariants, verifies the compatibility patch series still ends at `0005`, and emits a deterministic platform integration fingerprint.

Unknown configuration-layout, power-event, storage-write/barrier, AES-command and modern graphics behavior remains runtime-evidence gated. No fake GPU or speculative `0006` patch is introduced.

The next progression point is:

```text
Part 04
P4.01
```

## Maintainer testing policy

The maintainer will not be asked to manually test individual objectives. Manual testing is reserved for the finished integrated project.

Development-side source inspection, compilation, static checks, automated tests, emulator probes, regression tests and trace comparisons remain expected where practical.

## Logging policy

Every meaningful executable AppleSilicon operation must leave a `.log` artifact under `.logs/` unless a later component explicitly documents another local output contract.

P3.06 adds `.src/.tools/prepare-p3.06.sh` for deterministic non-guest integration validation and `.src/.tools/run-p3.06-probe.sh` as the final Part 03 runtime wrapper. The runtime wrapper delegates to P2.06/P1.07 instead of forking VMApple launch logic.

## Evidence policy

A source-known device, feature or register is not automatically a proven runtime blocker. VMApple reference-machine behavior, guest source requirements and Apple-specific implementation semantics remain separate until evidence connects them.

## Root README rule

The repository root `README.md` remains intentionally unchanged during these objectives.

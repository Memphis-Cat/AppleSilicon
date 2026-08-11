# AppleSilicon Documentation

Current project version: **`3.2.0.0.0.0`**

This directory records the research, design decisions, compatibility contracts, experiments and implementation objectives for AppleSilicon.

## Documents

- [VERSIONING.md](VERSIONING.md) — six-field project version format.
- [RESEARCH.md](RESEARCH.md) — research sources and prior-art findings.
- [ARCHITECTURE.md](ARCHITECTURE.md) — intended compatibility-layer architecture.
- [PART-01-BASELINE.md](PART-01-BASELINE.md) — closed Part 01 evidence/baseline objective tree.
- [P1.01.md](P1.01.md) through [P1.10.md](P1.10.md) — completed Part 01 sequence.
- [PART-02-CPU-CONTRACT.md](PART-02-CPU-CONTRACT.md) — closed Part 02 CPU compatibility objective tree.
- [P2.01.md](P2.01.md) through [P2.06.md](P2.06.md) — completed Part 02 sequence.
- [PART-03-PLATFORM-CONTRACT.md](PART-03-PLATFORM-CONTRACT.md) — active fixed Part 03 platform-contract tree.
- [P3.01.md](P3.01.md) — platform ownership inventory.
- [P3.02.md](P3.02.md) — configuration and platform identity contract.
- [P3.03.md](P3.03.md) — interrupt, timer, power and console contract.

## Part boundaries

Part 01 closes at `P1.10`; there is no P1.11.

Part 02 closes at `P2.06`; there is no P2.07.

Part 03 is fixed at exactly P3.01 through P3.06; there is no P3.07.

## Current Part 03 state

```text
P3.01  complete
P3.02  complete
P3.03  complete
P3.04  NEXT
P3.05  planned
P3.06  planned / final Part 03 objective
```

P3.03 freezes the stable VMApple GICv3, architectural virtual timer, PL011, PL031, PL061/power and pvpanic wiring without replacing generic QEMU devices. Exact power-button event semantics remain evidence-gated.

## Maintainer testing policy

The maintainer will not be asked to manually test individual objectives. Manual testing is reserved for the finished integrated project.

Development-side source inspection, compilation, static checks, automated tests, emulator probes, regression tests and trace comparisons remain expected where practical.

## Logging policy

Every meaningful executable AppleSilicon operation must leave a `.log` artifact under `.logs/` unless a later component explicitly documents another local output contract.

P3.03 adds `.src/.tools/prepare-p3.03.sh`, which writes a logged deterministic platform-I/O validation without launching a macOS guest.

## Evidence policy

A source-known device, feature or register is not automatically a proven runtime blocker. VMApple reference-machine behavior, guest source requirements and Apple-specific implementation semantics remain separate until evidence connects them.

## Root README rule

The repository root `README.md` remains intentionally unchanged during these objectives.

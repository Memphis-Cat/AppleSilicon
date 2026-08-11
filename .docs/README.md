# AppleSilicon Documentation

Current project version: **`2.0.0.0.0.0`**

This directory records the research, design decisions, compatibility contracts, experiments, and implementation objectives for AppleSilicon.

## Documents

- [VERSIONING.md](VERSIONING.md) — six-field project version format.
- [RESEARCH.md](RESEARCH.md) — existing projects, what they already solve, and what remains unsolved for our goal.
- [ARCHITECTURE.md](ARCHITECTURE.md) — intended system layers and where compatibility code belongs.
- [PART-01-BASELINE.md](PART-01-BASELINE.md) — Part 01 objective tree and closure state.
- [P1.01.md](P1.01.md) through [P1.10.md](P1.10.md) — completed Part 01 implementation sequence.
- [PART-02-CPU-CONTRACT.md](PART-02-CPU-CONTRACT.md) — fixed Part 02 CPU compatibility objective tree.
- [P2.01.md](P2.01.md) — Apple CPU system-register and feature inventory.

## Part and objective naming

Large work is divided into parts. Each part is divided into smaller numbered objectives whose count is fixed when that part begins.

Part 01 closes at:

```text
P1.10
```

There is no P1.11.

Part 02 is fixed at exactly:

```text
P2.01
P2.02
P2.03
P2.04
P2.05
P2.06
```

There is no P2.07.

New discoveries after the fixed final objective belong to a later part or an appropriate fix/emergency/hotfix release rather than silently extending the part.

## Current Part 02 state

P2.01 is implementation-complete at the static inventory level.

It records exact source locks and a machine-readable CPU-focused inventory of Apple implementation-defined AArch64 registers while keeping every register's runtime priority unknown until evidence exists.

The next objective is:

```text
P2.02 — Apple System Register Emulation Framework
```

## Maintainer testing policy

The maintainer will not be asked to manually test every part, objective, update, fix, hotfix, or emergency release.

Manual maintainer testing is reserved for the finished integration stage.

Development-side validation is still expected. Source review, compilation, static checks, automated tests, emulator probes, regression tests, synthetic fixtures, and trace comparisons should be used whenever possible so that intermediate defects are discovered without depending on repeated maintainer testing.

## Mandatory logging policy

Every meaningful executable AppleSilicon run must leave a `.log` artifact.

The default path is:

```text
.logs/AppleSilicon-YYYYMMDD-HHMMSS-PID.log
```

Runtime logging must capture stdout and stderr together unless a later component explicitly documents another design. Logs should contain version, time, host information, configuration information where safe, and the final exit state.

Logs must not intentionally contain passwords, Apple account information, authentication tokens, private keys, tickets, raw VM machine identifiers, or other sensitive machine material.

P2.01 continues this rule through `prepare-p2.01.sh`, which validates the CPU contract without launching a guest.

## Evidence policy

A source-known Apple register is not automatically a VMApple requirement.

Part 02 separates:

```text
known physical Apple implementation-defined behavior
from
proven VMApple/macOS guest requirements
```

P2.01 therefore keeps imported register relevance, access behavior, runtime priority and implementation behavior unknown unless stronger evidence exists.

The Part 01 runtime promotion rules remain the strongest evidence path once final integration testing is performed.

## Documentation rules

Every implementation objective should document:

1. The exact guest-visible contract or development capability being implemented.
2. The upstream/reference behavior used to understand it.
3. The automated/development-side validation used where practical.
4. The first failing point before the implementation when relevant.
5. The new failing point after the implementation when relevant.
6. Whether the result used an unmodified guest.
7. Any host-specific assumptions.
8. Which `.log` output proves the runtime result when runtime execution is involved.

A part is not complete because a panic disappeared. It is complete when the behavior is understood and implemented deliberately.

## Research sources

Prefer primary sources wherever possible:

- upstream source code,
- Apple open-source XNU,
- Apple developer/support documentation,
- QEMU source and documentation,
- Asahi Linux/m1n1 documentation and source,
- project source trees and issue trackers,
- direct traces collected from hardware we are authorized to test.

Do not turn unverified forum claims into implementation requirements.

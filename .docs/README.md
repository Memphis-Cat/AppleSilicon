# AppleSilicon Documentation

Current project version: **`0.8.0.0.0.0`**

This directory records the research, design decisions, compatibility contracts, experiments, and implementation objectives for AppleSilicon.

## Documents

- [VERSIONING.md](VERSIONING.md) — six-field project version format.
- [RESEARCH.md](RESEARCH.md) — existing projects, what they already solve, and what remains unsolved for our goal.
- [ARCHITECTURE.md](ARCHITECTURE.md) — intended system layers and where compatibility code belongs.
- [PART-01-BASELINE.md](PART-01-BASELINE.md) — the first engineering part and its objective tree.
- [P1.01.md](P1.01.md) — mandatory logged execution infrastructure.
- [P1.02.md](P1.02.md) — reproducible Inferno build baseline.
- [P1.03.md](P1.03.md) — VMApple capability and build-gate probe.
- [P1.04.md](P1.04.md) — decouple VMApple compilation from HVF.
- [P1.05.md](P1.05.md) — make Apple PVG optional during VMApple machine construction.
- [P1.06.md](P1.06.md) — explicit non-host VMApple CPU selection for TCG experiments.
- [P1.07.md](P1.07.md) — complete logged TCG VMApple pre-boot probe harness.
- [P1.08.md](P1.08.md) — trace normalization and earliest-divergence extraction.

## Part and objective naming

Large work is divided into parts. Each part is then divided into smaller numbered objectives.

Example:

```text
Part 01
├── P1.01
├── P1.02
├── P1.03
└── ...
```

A part may contain as many objectives as necessary. An objective should be small enough to have a specific technical purpose and a clear acceptance condition.

## Maintainer testing policy

The maintainer will not be asked to manually test every part, objective, update, fix, hotfix, or emergency release.

Manual maintainer testing is reserved for the finished integration stage.

Development-side validation is still expected. Source review, compilation, static checks, automated tests, emulator probes, regression tests, and trace comparisons should be used whenever possible so that intermediate defects are discovered without depending on repeated maintainer testing.

P1.08 adds synthetic trace fixtures and a self-check/validation harness specifically so trace-analysis logic can be checked without requiring a macOS guest run.

## Mandatory logging policy

Every meaningful executable AppleSilicon run must leave a `.log` artifact.

The default path is:

```text
.logs/AppleSilicon-YYYYMMDD-HHMMSS-PID.log
```

Runtime logging must capture stdout and stderr together unless a later component explicitly documents another design. Logs should contain version, time, host information, configuration information where safe, and the final exit state.

Logs must not intentionally contain passwords, Apple account information, authentication tokens, private keys, tickets, raw VM machine identifiers, or other sensitive machine material.

P1.01 defines the first implementation of this rule. P1.07 extends it to separate launcher, serial, QEMU debug, and trace-capability logs for the first controlled non-host VMApple probe. P1.08 adds logged trace-analysis validation and keeps generated comparison artifacts under ignored local build/log paths.

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

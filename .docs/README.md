# AppleSilicon Documentation

Current project version: **`2.2.0.0.0.0`**

This directory records research, design decisions, compatibility contracts, experiments and implementation objectives.

## Documents

- [VERSIONING.md](VERSIONING.md) — six-field version format.
- [RESEARCH.md](RESEARCH.md) — existing projects and source research.
- [ARCHITECTURE.md](ARCHITECTURE.md) — intended compatibility layers.
- [PART-01-BASELINE.md](PART-01-BASELINE.md) — closed Part 01 tree.
- [P1.01.md](P1.01.md) through [P1.10.md](P1.10.md) — completed Part 01 sequence.
- [PART-02-CPU-CONTRACT.md](PART-02-CPU-CONTRACT.md) — fixed Part 02 tree.
- [P2.01.md](P2.01.md) — CPU register/feature inventory.
- [P2.02.md](P2.02.md) — fail-closed sysreg framework.
- [P2.03.md](P2.03.md) — explicit read/write/reset/access policy model.

## Objective boundaries

Part 01 ends at P1.10.

Part 02 is fixed at:

```text
P2.01
P2.02
P2.03
P2.04
P2.05
P2.06
```

There is no P2.07.

## Current Part 02 state

P2.01, P2.02 and P2.03 are implementation-complete at the development/static level.

P2.03 adds the semantic policy engine on top of the P2.02 `AppleSysRegSpec`/`ARMCPRegInfo` bridge. Read, write, reset and access behavior are independent and evidence-scoped.

The current live semantic policy count is:

```text
0
```

because P2.01 has not promoted any Apple implementation-defined register semantics.

Next:

```text
P2.04 — CPU Feature and ID-Register Compatibility
```

## Maintainer testing policy

Intermediate objectives use development-side validation rather than repeated manual maintainer testing. Real macOS/HVF/TCG integration testing remains reserved for the finished integration stage.

## Mandatory logging policy

Meaningful executable AppleSilicon tools must leave `.log` artifacts and avoid sensitive material.

P2.03 adds `.src/.tools/prepare-p2.03.sh`, which writes `.logs/AppleSilicon-p2.03-YYYYMMDD-HHMMSS-PID.log`.

## Evidence policy

A known Apple register is not automatically a VMApple requirement or a known semantic contract.

P2.03 requires non-empty evidence and scope metadata before a semantic policy can be registered. Unknown reads/writes remain undefined rather than falling back to zero, ignore or fabricated state.

## Research sources

Prefer primary sources: upstream source, Apple XNU, Apple documentation, QEMU, Asahi/m1n1, project source/issue trackers and authorized hardware traces.

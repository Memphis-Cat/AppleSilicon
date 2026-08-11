# AppleSilicon Documentation

Current project version: **`0.1.0.0.0.0`**

This directory records the research, design decisions, compatibility contracts, experiments, and implementation objectives for AppleSilicon.

## Documents

- [VERSIONING.md](VERSIONING.md) — six-field project version format.
- [RESEARCH.md](RESEARCH.md) — existing projects, what they already solve, and what remains unsolved for our goal.
- [ARCHITECTURE.md](ARCHITECTURE.md) — intended system layers and where compatibility code belongs.
- [PART-01-BASELINE.md](PART-01-BASELINE.md) — the first engineering part and its objectives.

## Documentation rules

Every implementation part should document:

1. The exact guest-visible contract being implemented.
2. The upstream/reference behavior used to understand it.
3. The test used to prove the behavior.
4. The first failing point before the implementation.
5. The new failing point after the implementation.
6. Whether the result used an unmodified guest.
7. Any host-specific assumptions.

A part is not complete because a panic disappeared. It is complete when the behavior is understood, implemented deliberately, and tested reproducibly.

## Research sources

Prefer primary sources wherever possible:

- upstream source code,
- Apple open-source XNU,
- QEMU source and documentation,
- Asahi Linux/m1n1 documentation and source,
- project source trees and issue trackers,
- direct traces collected from hardware we are authorized to test.

Do not turn unverified forum claims into implementation requirements.

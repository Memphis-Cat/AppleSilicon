# Source

Project version: **`0.2.0.0.0.0`**

The source directory remains intentionally small while Part 01 is establishing the VMApple baseline.

The project is not going to invent a fake Apple CPU implementation before we have measured what the guest actually requires.

## Current layout

```text
src/
├── upstream/
│   └── inferno/        # pinned upstream reference/submodule
├── patches/
│   └── README.md       # AppleSilicon patch series
├── tools/
│   ├── README.md       # trace/diff/inspection tooling
│   └── run-logged.sh   # mandatory persistent run logging wrapper
└── configs/
    └── README.md       # non-secret example configurations
```

## Upstream strategy

The preferred initial reference is ChefKiss Inferno because it is an active QEMU derivative containing both Apple ARM emulation work and VMApple code.

Upstream QEMU remains the canonical reference for the clean `vmapple` implementation.

AppleSilicon-specific changes should be kept easy to review against upstream rather than mixed into an unexplained source dump.

## P1.01

The first detailed sub-objective is `docs/P1.01.md`.

P1.01 establishes the run-logging contract. Every meaningful runtime invocation must leave a `.log` artifact, including failed commands.

The generic wrapper is:

```text
src/tools/run-logged.sh
```

Future launchers may replace the wrapper, but they must preserve equivalent persistent logging behavior.

## First VMApple implementation patch

The first planned VMApple compatibility patch remains:

```text
0001-vmapple-allow-explicit-tcg-cpu.patch
```

Its job is not to make macOS boot magically.

Its job is to remove the `host` CPU assumption from the experiment path cleanly enough that we can run VMApple with an explicit TCG CPU model, capture the first deterministic failure, and turn that failure into the next compatibility objective.

See `docs/PART-01-BASELINE.md`.

## Maintainer testing policy

Intermediate source changes must not depend on the maintainer manually testing every part or release. Development-side builds, automated checks, emulator probes, and logs should provide evidence during development. Manual maintainer testing is reserved for the finished integration stage.

## No proprietary Apple artifacts

Do not add Apple firmware, macOS images, installers, device-specific secrets, tickets, keys, or other restricted Apple binaries to `src/`.

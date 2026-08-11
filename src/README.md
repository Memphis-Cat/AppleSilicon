# Source

Project version: **`0.1.0.0.0.0`**

The source directory is intentionally small in the first update.

The project is not going to invent a fake Apple CPU implementation before we have measured what the guest actually requires.

## Planned layout

```text
src/
├── upstream/
│   └── inferno/        # pinned upstream reference/submodule
├── patches/
│   └── README.md       # AppleSilicon patch series
├── tools/
│   └── README.md       # trace/diff/inspection tooling
└── configs/
    └── README.md       # non-secret example configurations
```

## Upstream strategy

The preferred initial reference is ChefKiss Inferno because it is an active QEMU derivative containing both Apple ARM emulation work and VMApple code.

Upstream QEMU remains the canonical reference for the clean `vmapple` implementation.

AppleSilicon-specific changes should be kept easy to review against upstream rather than mixed into an unexplained source dump.

## First implementation patch

The first planned patch is:

```text
0001-vmapple-allow-explicit-tcg-cpu.patch
```

Its job is not to make macOS boot magically.

Its job is to remove the `host` CPU assumption from the experiment path cleanly enough that we can run VMApple with an explicit TCG CPU model, capture the first deterministic failure, and turn that failure into the next compatibility objective.

See `docs/PART-01-BASELINE.md`.

## No proprietary Apple artifacts

Do not add Apple firmware, macOS images, installers, device-specific secrets, tickets, keys, or other restricted Apple binaries to `src/`.

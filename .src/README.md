# Source

Project version: **`1.0.0.0.0.0`**

The source tree now contains the complete Part 01 research/evidence pipeline.

The project still does not invent a broad fake Apple CPU implementation before measuring what the guest actually requires.

## Current layout

```text
.src/
├── .upstream/
│   └── .inferno/       # pinned upstream reference/submodule
├── .patches/           # ordered VMApple compatibility research patches
├── .tools/             # build, probe, trace, manifest, evidence, and promotion tools
├── .configs/           # non-secret experiment configs and policies
└── .fixtures/          # sanitized deterministic development fixtures
```

## Upstream strategy

The active reference remains ChefKiss Inferno, pinned to the exact revision recorded in the project documentation and submodule.

Upstream QEMU remains the canonical reference for the clean `vmapple` implementation and tracing behavior.

AppleSilicon-specific changes stay reviewable as project patches/tools around a pristine upstream checkout rather than being mixed into an unexplained source dump.

## Part 01 source chain

Part 01 now provides:

```text
logged runs
reproducible Inferno build description
VMApple capability probing
HVF build-gate decoupling
optional Apple PVG realization
explicit TCG CPU profiles
finite TCG probe runtime
trace normalization/comparison
privacy-safe A/B manifests
fail-closed HVF reference runtime
post-run probe manifest collection
A/B evidence bundling
reproduced-divergence promotion gate
```

The final Part 01 tool is:

```text
.src/.tools/evidence-bundle.py
```

It cannot promote a synthetic or one-off mismatch into `P01-DIVERGENCE-0001`. At least two unique matching runtime A/B pairs are required.

## Maintainer testing policy

Intermediate source changes do not depend on the maintainer manually testing every objective or release. Development-side source checks, deterministic fixtures, regression tools, and logs provide the intermediate evidence.

Real reference/probe execution is reserved for the finished integration stage.

## Part 01 closure

Part 01 closes at:

```text
P1.10
```

There is no P1.11.

The next source work belongs to Part 02 and should implement the specific hardware/CPU/platform contract identified by the first real promoted Part 01 divergence rather than guessing a large Apple Silicon model in advance.

## No proprietary Apple artifacts

Do not add Apple firmware, macOS images, installers, device-specific secrets, tickets, keys, machine-identity blobs, or other restricted/private Apple material to `.src/`.

# Source

Project version: **`0.9.0.0.0.0`**

The source tree contains the reproducible infrastructure used to discover Apple Silicon compatibility requirements from evidence rather than guessing them in advance.

## Current layout

```text
.src/
├── .upstream/
│   └── .inferno/        # pinned upstream submodule
├── .patches/            # reviewable AppleSilicon changes over the pinned source
├── .tools/              # build, probe, trace, evidence, and validation tooling
├── .configs/            # non-secret experiment contracts/examples
└── .fixtures/           # deliberately sanitized deterministic test evidence
```

Local generated state remains outside version control under:

```text
.build/
.logs/
```

## Upstream strategy

The active reference is the pinned ChefKiss Inferno revision recorded in Part 01. Upstream QEMU remains the canonical clean reference for VMApple behavior.

AppleSilicon-specific changes stay reviewable as ordered patches and project-owned tools around a pristine submodule rather than becoming an unexplained source fork.

## Current Part 01 pipeline

```text
P1.01  persistent logging
P1.02  reproducible pinned build
P1.03  VMApple capability/build-gate probe
P1.04  remove HVF compile gate
P1.05  make Apple PVG optional
P1.06  explicit non-host CPU profiles
P1.07  finite TCG VMApple probe runner
P1.08  normalize/compare traces
P1.09  validate reference/probe evidence pairing
```

The project still does not invent a broad fake Apple CPU model before a concrete guest-visible incompatibility has been measured.

## Evidence rule

A trace difference is not automatically a compatibility difference.

P1.09 requires a reference and probe to prove that their pinned source, VMApple machine shape, RAM/SMP, trace/debug contract, and local guest inputs match before P1.08 output can be considered a real divergence candidate.

Raw local guest firmware, disks, auxiliary storage, VM identifiers, hardware-model serialization, credentials, or Apple account material must not be committed. Versionable manifests use hashes and sizes instead.

## Maintainer testing policy

Intermediate source changes must not depend on the maintainer manually testing every part or release. Development-side source review, automated checks, synthetic fixtures, emulator probes, and logs should provide evidence during development. Manual maintainer testing is reserved for the finished integration stage.

See `.docs/PART-01-BASELINE.md` and `.docs/P1.09.md`.

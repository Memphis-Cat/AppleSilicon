# Source

Project version: **`2.3.0.0.0.0`**

The source tree contains the complete Part 01 evidence pipeline and Part 02 CPU compatibility work through P2.04.

## Layout

```text
.src/
├── .upstream/.inferno/  # pinned Inferno submodule
├── .patches/            # ordered compatibility patches
├── .tools/              # logged preparation/regression/evidence tools
├── .configs/            # non-secret machine-readable contracts/configs
└── .fixtures/           # sanitized deterministic fixtures
```

## Part 01

Part 01 is closed at P1.10. Its evidence pipeline remains available for final integration testing.

## Part 02 source chain

Part 02 is fixed at P2.01 through P2.06.

P2.01 inventories Apple implementation-defined CPU registers and source-backed feature observations without assigning semantics.

P2.02 adds the fail-closed Apple sysreg registration framework.

P2.03 adds the evidence-gated sysreg read/write/reset/access policy engine. The live semantic table remains empty.

P2.04 adds:

```text
.src/.patches/0005-arm-vmapple-feature-contract.patch
.src/.configs/p2.04-feature-contract.json
.src/.tools/prepare-p2.04.sh
```

The P2.04 patch creates, inside disposable patched Inferno trees:

```text
target/arm/apple-cpu-features.c
target/arm/apple-cpu-features.h
```

It attaches a minimum architectural VMApple feature profile only to the TCG `apple-gxf` path. The profile covers PAuth presence, SSBS2, SME/SME2, PAN3, 4 KiB + 16 KiB stage-1 granules and range TLBI while preserving stronger QEMU `max` capabilities.

The standard `max` CPU, host/HVF and KVM paths are not modified by the P2.04 profile.

The next source objective is:

```text
P2.05 — Deterministic CPU Contract Regression Harness
```

## Testing and artifacts

Intermediate objectives rely on development-side validation and persistent `.logs/` artifacts rather than repeated maintainer testing. Real macOS execution remains reserved for final integration.

No proprietary Apple firmware, macOS images, tickets, keys, machine-identity blobs or account secrets belong in `.src/`.

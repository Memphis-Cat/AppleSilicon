# Source

Project version: **`2.0.0.0.0.0`**

The source tree contains the complete Part 01 research/evidence pipeline and now begins Part 02's Apple CPU compatibility layer.

## Current layout

```text
.src/
├── .upstream/
│   └── .inferno/       # pinned upstream reference/submodule
├── .patches/           # ordered VMApple compatibility research patches
├── .tools/             # build, probe, trace, evidence, CPU-contract and validation tools
├── .configs/           # non-secret experiment configs, policies and CPU contracts
└── .fixtures/          # sanitized deterministic development fixtures
```

## Upstream strategy

The active VMApple implementation base remains ChefKiss Inferno at the exact pinned submodule revision.

Upstream QEMU is the reference for the ARM system-register registration API and VMApple implementation behavior.

Apple XNU provides public guest-side ARM64/virtual-platform evidence. Asahi m1n1 provides open source Apple implementation-defined system-register encodings and authorized-hardware research tooling.

AppleSilicon-specific changes stay reviewable as project patches/tools around a pristine upstream checkout rather than being mixed into an unexplained source dump.

## Part 01 closure

Part 01 is closed at P1.10. There is no P1.11.

Its evidence tools remain available to provide real runtime evidence during final integration testing.

## Part 02 source chain

Part 02 is fixed at six objectives and closes at P2.06. There is no P2.07.

P2.01 adds:

```text
.src/.configs/p2.01-cpu-contract.json
.src/.tools/cpu-contract.py
.src/.tools/prepare-p2.01.sh
```

The machine-readable contract currently inventories CPU-focused Apple implementation-defined register groups:

```text
hid_ehid
timer
amx
gxf_sprr
pauth_control
control_hypervisor
```

P2.01 is deliberately inventory-only. Every register starts with unknown runtime priority and unknown XNU relevance. No reset value, read value, writable mask, side effect or trap policy is fabricated.

The next source objective is:

```text
P2.02 — Apple System Register Emulation Framework
```

P2.02 will use QEMU's existing ARM system-register infrastructure rather than creating a parallel instruction decoder.

## Maintainer testing policy

Intermediate source changes do not depend on the maintainer manually testing every objective or release. Development-side source checks, deterministic fixtures, regression tools, and logs provide the intermediate evidence.

Real reference/probe/macOS execution is reserved for the finished integration stage.

## No proprietary Apple artifacts

Do not add Apple firmware, macOS images, installers, device-specific secrets, tickets, keys, machine-identity blobs, or other restricted/private Apple material to `.src/`.

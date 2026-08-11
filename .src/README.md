# Source

Project version: **`2.1.0.0.0.0`**

The source tree contains the complete Part 01 research/evidence pipeline and the first two Part 02 Apple CPU compatibility objectives.

## Current layout

```text
.src/
├── .upstream/
│   └── .inferno/       # pinned upstream reference/submodule
├── .patches/           # ordered VMApple and Apple CPU compatibility patches
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

The machine-readable contract inventories CPU-focused Apple implementation-defined register groups:

```text
hid_ehid
timer
amx
gxf_sprr
pauth_control
control_hypervisor
```

P2.01 is deliberately inventory-only. Every register starts with unknown runtime priority and unknown XNU relevance. No reset value, read value, writable mask, side effect or trap policy is fabricated.

P2.02 adds:

```text
.src/.patches/0003-arm-apple-sysreg-framework.patch
.src/.tools/prepare-p2.02.sh
```

The P2.02 patch adds, inside the disposable patched Inferno tree:

```text
target/arm/apple-sysregs.c
target/arm/apple-sysregs.h
```

It provides an encoding-only `AppleSysRegSpec` to `ARMCPRegInfo` bridge, an explicit fail-closed undefined-access registration helper, Meson integration for AArch64, and TCG-only attachment to Inferno's existing `apple-gxf` CPU model.

P2.02 deliberately installs **zero guest-visible Apple system-register policies by default**. No read-as-zero, write-ignore, constant, reset-value or stored-state behavior is invented.

The next source objective is:

```text
P2.03 — Register Read/Write/Reset Policy Model
```

P2.03 will define the allowed data-driven behavior classes and the evidence required before a P2.01 inventory entry may receive one.

## Maintainer testing policy

Intermediate source changes do not depend on the maintainer manually testing every objective or release. Development-side source checks, deterministic fixtures, regression tools, and logs provide the intermediate evidence.

Real reference/probe/macOS execution is reserved for the finished integration stage.

## No proprietary Apple artifacts

Do not add Apple firmware, macOS images, installers, device-specific secrets, tickets, keys, machine-identity blobs, or other restricted/private Apple material to `.src/`.

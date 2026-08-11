# AppleSilicon

**Version: `0.1.0.0.0.0`**

AppleSilicon is a long-term research and engineering project whose goal is to make unmodified ARM64 macOS run on non-Apple ARM64 hardware by presenting a sufficiently compatible Apple-Silicon-class machine to the guest.

This is not a macOS-themed environment, a reimplementation of macOS, or an identity-spoofing-only Hackintosh. The target is real XNU, real Apple ARM64 userspace, and a machine model that satisfies the hardware and boot contracts macOS expects.

## Current status

`0.1.0.0.0.0` is the research/bootstrap update. No claim is made that macOS currently boots on generic ARM hardware.

The first phase establishes a reproducible upstream baseline, identifies which parts of the current VMApple path depend on an Apple Silicon host, and turns those dependencies into explicit implementation objectives.

## Starting point

Research performed for the first update found several important existing projects:

- [QEMU](https://github.com/qemu/qemu) contains the upstream `vmapple` machine model. It recreates the virtual device model exposed to Apple-Silicon macOS guests by Apple's Virtualization.framework. Upstream currently documents an Apple Silicon/macOS host requirement and macOS 12 guest support.
- [ChefKiss Inferno](https://github.com/ChefKissInc/Inferno) is an active QEMU derivative for emulating Apple ARM devices. It contains Apple device-emulation work and `vmapple`, making it an important reference for this project.
- [qemu-t8030](https://github.com/TrungNguyen1909/qemu-t8030) emulates the T8030/A13 platform and demonstrates that substantial Apple-specific SoC behavior can be modeled in QEMU. It is archived and iPhone/iOS-oriented, so it is research material rather than the main base.
- [xnu-qemu-arm64](https://github.com/alephsecurity/xnu-qemu-arm64) demonstrated ARM64 XNU/iOS bring-up in QEMU, including KVM work, but relies on guest patching and targets older iOS hardware.
- [m1n1](https://github.com/AsahiLinux/m1n1) is the main hardware-research tool for observing real Apple Silicon behavior and tracing macOS/XNU hardware accesses.
- [Apple's open-source XNU](https://github.com/apple-oss-distributions/xnu) is a primary source for the ARM64 kernel-side contracts that are visible in open source.

The project will initially treat upstream QEMU/VMApple and Inferno as references/bases, while keeping AppleSilicon-specific research, patches, tests, traces, and documentation in this repository.

## Repository layout

```text
AppleSilicon/
├── README.md
├── docs/
│   ├── README.md
│   ├── VERSIONING.md
│   ├── RESEARCH.md
│   ├── ARCHITECTURE.md
│   └── PART-01-BASELINE.md
└── src/
    └── README.md
```

The source tree will expand only as each part becomes concrete. We are deliberately avoiding a giant placeholder tree for components that do not exist yet.

## First engineering target

The first target is **not** the graphical macOS desktop.

It is to take the existing VMApple model, reproduce its known-good behavior, then determine precisely what prevents that same guest environment from running when the host CPU is a generic ARM64 CPU rather than Apple Silicon.

The first new compatibility milestone will be reached when an AppleSilicon build can execute the VMApple pre-boot/XNU path using a non-Apple ARM CPU model far enough to produce a deterministic, documented failure that is caused by one known missing Apple CPU/platform contract.

From there, each missing contract becomes its own objective.

## Core rule

Do not hide failures by blindly patching macOS.

Whenever possible, compatibility belongs below the guest:

```text
macOS / XNU
    ↓
Apple-compatible virtual machine contract
    ↓
AppleSilicon compatibility implementation
    ↓
QEMU TCG / KVM / host ARM64
```

Guest patches may be used temporarily for research and instrumentation, but a successful compatibility milestone should be reproducible with original Apple kernel/userspace components unless the milestone explicitly says otherwise.

## Documentation

Start with [docs/README.md](docs/README.md), then read [docs/PART-01-BASELINE.md](docs/PART-01-BASELINE.md).

## Legal and licensing note

This project must respect the licenses of all upstream code and the terms applicable to any Apple software used for research or testing. No Apple firmware, macOS images, keys, proprietary binaries, or other redistributable-restricted Apple material should be committed to this repository.

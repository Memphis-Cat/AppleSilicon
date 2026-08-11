# AppleSilicon

**Version: `0.2.0.0.0.0`**

AppleSilicon is a long-term research and engineering project whose goal is to make unmodified ARM64 macOS run on non-Apple ARM64 hardware while seeing a machine that satisfies the hardware and boot contracts expected from an Apple-Silicon-compatible Mac.

This project is not trying to create a macOS-looking operating system, rename a generic ARM computer, or merely spoof a Mac model identifier. The target is the real XNU kernel, the real Apple ARM64 userspace, and a compatibility layer below macOS that makes the guest interact with hardware interfaces it genuinely accepts as an Apple-Silicon-class platform.

## What is Apple Silicon?

Apple Silicon is the family of Apple-designed system-on-a-chip hardware used in modern Macs. Apple began moving the Mac away from Intel processors in late 2020, starting with the M1 generation. Unlike an older desktop design where the CPU, graphics processor, memory controllers, security devices, media hardware, and other controllers may be separate chips connected through a motherboard, Apple Silicon combines a large amount of the computer into one tightly integrated SoC.

Apple's own system-architecture documentation describes Apple Silicon Macs as combining the CPU and GPU with a unified memory architecture and additional specialized coprocessors and engines. That integration is one of the reasons this project is much more difficult than a traditional Intel Hackintosh.

Primary Apple references:

- <https://support.apple.com/116943>
- <https://developer.apple.com/videos/play/wwdc2020/10686/>
- <https://developer.apple.com/documentation/apple-silicon>

### CPU

The CPU executes macOS itself: XNU, drivers, frameworks, applications, and the ARM64 instructions that make up modern Apple-Silicon software.

Apple Silicon uses the ARM64/AArch64 architecture, but an Apple CPU is not equivalent to an arbitrary ARM64 CPU. A generic ARM64 processor may understand the same basic instruction set while still differing in CPU feature registers, implementation-defined system registers, exception behavior, page-table capabilities, timers, virtualization behavior, pointer authentication, CPU topology, power-management interfaces, and other details visible to low-level software.

That distinction is central to AppleSilicon. We do not only need an ARM64 processor. We need to determine which CPU-visible contracts macOS actually depends on and reproduce the required behavior on a non-Apple ARM64 host or in emulation.

### GPU

Apple Silicon also contains an Apple-designed GPU. The GPU is responsible for far more than simply drawing the desktop: macOS uses its graphics stack for WindowServer composition, Metal, application rendering, video workflows, compute workloads, and many effects throughout the operating system.

A Qualcomm, AMD, NVIDIA, ARM Mali, or other GPU does not automatically become compatible just because the CPU is ARM64. macOS contains drivers and firmware expectations for the graphics hardware it supports. A future usable AppleSilicon system will therefore need either a compatible virtual graphics contract, a translation layer, or sufficiently complete emulation of the interfaces expected by macOS.

GPU acceleration is not required for the earliest kernel milestones, but it will become one of the largest later parts of the project.

### Unified memory

Apple Silicon Macs use a unified memory architecture. The CPU, GPU, and other engines can operate on the same high-bandwidth memory rather than requiring the traditional model where a discrete GPU keeps its own separate VRAM and data must repeatedly be copied between CPU and GPU memory.

For this project, that does not mean the host machine must physically copy Apple's memory design. It means the virtual machine and compatibility layer must expose memory behavior that is valid for the macOS guest and for every emulated or translated device that shares that memory.

### More than CPU and GPU

An Apple-Silicon Mac is an entire platform. Depending on the machine and operating-system path, macOS can interact with many additional blocks and services, including:

- interrupt and timer infrastructure,
- memory-management and IOMMU facilities,
- storage controllers and boot storage,
- USB and PCIe-facing devices,
- display and framebuffer services,
- media encode/decode engines,
- the Neural Engine and machine-learning accelerators,
- security and boot-policy components,
- firmware and coprocessors,
- power-management hardware,
- device-tree/platform information,
- Apple-specific virtual-machine devices.

We do **not** need to implement every physical M-series component before XNU can execute. Our first route is based on Apple's virtual-Mac contract and QEMU's VMApple work, which is much smaller than emulating a complete physical M-series SoC. If a future stage requires physical Apple-device behavior, it becomes its own part and its own objectives.

## The end of the traditional Hackintosh path

Traditional Hackintosh systems were possible largely because Macs used Intel x86-64 processors for many years. A non-Apple PC could use a compatible x86-64 CPU and, with projects such as OpenCore plus suitable hardware and drivers, provide enough of the environment expected by Intel macOS to boot the real operating system.

That path now has a hard architectural ending.

Apple states that **macOS Tahoe is the final macOS release for Intel-based Mac computers**. macOS 27 belongs to the Apple-Silicon era rather than continuing the normal Intel-Mac boot target. This is bigger than a model-number check or a single firmware restriction: the operating system is moving away from the x86-64 Mac platform that made the traditional Hackintosh possible.

Apple reference:

- <https://developer.apple.com/documentation/apple-silicon/about-the-rosetta-translation-environment>

An Intel or AMD Hackintosh cannot solve that transition by changing an SMBIOS value. An x86-64 processor cannot natively execute an ARM64 XNU kernel, and even a generic ARM64 computer does not automatically provide the Apple platform surrounding that kernel.

That is where this project begins.

> The traditional Hackintosh tried to make compatible PC hardware look enough like an Intel Mac. AppleSilicon aims to make non-Apple ARM64 hardware provide a sufficiently complete Apple-Silicon-compatible machine contract for modern macOS.

The goal is not for macOS to be told a lie and then immediately encounter incompatible hardware. The compatibility implementation must respond correctly when macOS actually uses the CPU features, memory behavior, interrupts, timers, virtual devices, boot interfaces, storage, graphics, and later platform services that it expects.

## Current status

`0.2.0.0.0.0` is still an early research/bootstrap update. No claim is made that macOS currently boots on generic ARM64 hardware.

The first engineering part establishes a reproducible upstream baseline, identifies which pieces of the current VMApple path depend on an Apple Silicon host, and converts those dependencies into small implementation objectives.

The first detailed sub-objective is [P1.01](docs/P1.01.md).

## Starting point

Research performed for the project found several important existing projects:

- [QEMU](https://github.com/qemu/qemu) contains the upstream `vmapple` machine model. It recreates the virtual device model exposed to Apple-Silicon macOS guests by Apple's Virtualization.framework. Upstream currently documents an Apple Silicon/macOS host requirement and a restricted known guest path.
- [ChefKiss Inferno](https://github.com/ChefKissInc/Inferno) is an active QEMU derivative for emulating Apple ARM devices. It contains Apple device-emulation work and `vmapple`, making it the closest active reference/base found for this project.
- [qemu-t8030](https://github.com/TrungNguyen1909/qemu-t8030) emulates the T8030/A13 platform and demonstrates that substantial Apple-specific SoC behavior can be modeled in QEMU. It is archived and iPhone/iOS-oriented, so it is research material rather than the main base.
- [xnu-qemu-arm64](https://github.com/alephsecurity/xnu-qemu-arm64) demonstrated ARM64 XNU/iOS bring-up in QEMU, including KVM work, but relies on guest patching and targets older iOS hardware.
- [m1n1](https://github.com/AsahiLinux/m1n1) is the main hardware-research tool for observing real Apple Silicon behavior and tracing macOS/XNU hardware accesses.
- [Apple's open-source XNU](https://github.com/apple-oss-distributions/xnu) is a primary source for ARM64 kernel-side contracts that are visible in open source.

The project uses a pinned Inferno source reference while keeping AppleSilicon-specific research, patches, tools, logs, and documentation in this repository.

## Project rules

### Rule 1 — No intermediate user testing

The project is developed part by part and objective by objective, but the maintainer will **not be asked to manually test every part, update, fix, hotfix, or intermediate build**.

Manual end-user testing happens only when the project reaches its finished integration stage.

This does not prohibit development-side validation. Builds, static checks, unit tests, emulator self-tests, trace comparisons, and reproducibility checks should still be created and used whenever possible so that errors are not deliberately accumulated until the end. The rule is specifically that intermediate progress must not depend on repeatedly asking the maintainer to boot or test unfinished builds.

### Rule 2 — Every executable run produces a `.log`

Every AppleSilicon launcher, probe, emulator run, compatibility test, or final boot path must produce a persistent `.log` file.

The default format is:

```text
logs/AppleSilicon-YYYYMMDD-HHMMSS.log
```

A useful log must include, when available:

```text
AppleSilicon version
UTC timestamp
host OS and architecture
selected accelerator
selected CPU model
machine model
command/configuration summary with secrets redacted
boot stage
warnings
unimplemented features
exceptions/panics
exit code or shutdown reason
```

Console-only errors are not sufficient. If something fails, the project must leave enough information in a `.log` file to determine what happened later.

Generated runtime logs are local diagnostic artifacts and should not contain private machine identifiers, Apple account information, cryptographic material, tickets, firmware secrets, or other sensitive data.

The first generic logging wrapper lives at `src/tools/run-logged.sh`; future launchers must either use it or implement equivalent logging themselves.

### Rule 3 — Do not hide incompatibilities

Do not blindly patch macOS until a failure disappears.

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

## Clone

Clone the project and its pinned upstream source together:

```bash
git clone --recurse-submodules https://github.com/Memphis-Cat/AppleSilicon.git
```

If the repository was already cloned without submodules:

```bash
git submodule update --init --recursive
```

The Inferno reference is pinned rather than following `master` automatically, so experiments remain reproducible until we deliberately update the baseline.

## Repository layout

```text
AppleSilicon/
├── .gitmodules
├── .gitignore
├── README.md
├── docs/
│   ├── README.md
│   ├── VERSIONING.md
│   ├── RESEARCH.md
│   ├── ARCHITECTURE.md
│   ├── PART-01-BASELINE.md
│   └── P1.01.md
└── src/
    ├── README.md
    ├── upstream/
    │   └── inferno/       # pinned Git submodule
    ├── patches/
    │   └── README.md
    ├── tools/
    │   ├── README.md
    │   └── run-logged.sh
    └── configs/
        └── README.md
```

The source tree expands only when a part becomes concrete. We deliberately avoid a giant placeholder tree for components that do not exist yet.

## First engineering target

The first target is **not** the graphical macOS desktop.

It is to take the existing VMApple model, preserve a known reference baseline, and determine precisely what prevents the same Apple virtual-Mac contract from progressing when its CPU path is no longer backed by a real Apple Silicon host CPU.

The first compatibility milestone is reached when a non-Apple/generic CPU path produces a deterministic and well-logged incompatibility that can be reduced to one known missing CPU or platform contract.

Then that contract becomes the next objective.

## Documentation

Start with [docs/README.md](docs/README.md), then read [docs/RESEARCH.md](docs/RESEARCH.md), [docs/PART-01-BASELINE.md](docs/PART-01-BASELINE.md), and [docs/P1.01.md](docs/P1.01.md).

## Legal and licensing note

This project must respect the licenses of all upstream code and the terms applicable to any Apple software used for research or testing. No Apple firmware, macOS images, keys, proprietary binaries, or other redistribution-restricted Apple material should be committed to this repository.

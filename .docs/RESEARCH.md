# Existing Project Research

Research date: **2026-08-11**

Project version: **`0.1.0.0.0.0`**

## Exact target searched for

The target is not merely ARM64 XNU emulation and not merely macOS virtualization on an Apple Silicon Mac.

The target searched for was:

> Run real ARM64 macOS on a non-Apple ARM64 host while presenting a machine contract compatible enough with Apple Silicon / Apple's virtual Mac platform that the guest boots without requiring the host to contain an Apple CPU.

GitHub and public project documentation were checked for active projects covering Apple Silicon emulation, VMApple/vmapple, ARM64 XNU under QEMU, macOS on generic ARM, and prior Apple SoC emulators.

## Result

**No completed project was found that currently achieves the exact target.**

There are, however, multiple projects that solve major pieces of the problem. We should reuse those pieces instead of reimplementing them blindly.

---

## 1. QEMU `vmapple`

Repository: <https://github.com/qemu/qemu>

Documentation: <https://www.qemu.org/docs/master/system/arm/vmapple.html>

Important source:

- `hw/vmapple/vmapple.c`
- `hw/vmapple/cfg.c`
- `hw/vmapple/bdif.c`
- `hw/vmapple/virtio-blk.c`
- `hw/vmapple/aes.c`
- `include/hw/vmapple/vmapple.h`

### What it already does

Upstream QEMU implements the VMApple device model used by Apple's Virtualization.framework for Apple-Silicon macOS guests without directly using Virtualization.framework code for the device model.

The current machine includes or wires models for:

- ARM GICv3,
- generic ARM timers,
- PL011 UART,
- RTC,
- PCIe,
- XHCI,
- VMApple configuration region,
- VMApple backdoor interface,
- Apple-specific virtio block behavior,
- Apple AES device,
- Apple paravirtual graphics,
- networking and basic virtual peripherals.

### Current limitation relevant to us

Upstream documentation currently requires:

- an Apple Silicon host,
- macOS as the host OS,
- HVF acceleration,
- an existing Virtualization.framework macOS VM,
- the Apple Virtualization.framework pre-boot environment,
- currently macOS 12.x as the supported guest generation.

The current QEMU machine class also defaults the vCPU type to `host`, which means the known-good path inherits the actual Apple host CPU's exposed architectural behavior.

### Why this is important

This is the best existing specification-by-implementation for **the virtual Mac hardware contract**. It means AppleSilicon does not need to begin by emulating a complete physical M-series SoC just to reach XNU.

### What it does not solve

It does not currently provide a documented path for:

```text
non-Apple ARM64 host
    -> QEMU/KVM or QEMU/TCG
    -> vmapple
    -> modern macOS
```

That missing transition is one of our main targets.

---

## 2. ChefKiss Inferno

Repository: <https://github.com/ChefKissInc/Inferno>

Project documentation: <https://chefkiss.dev/applehax/inferno/>

### Status

Inferno is active as of this research. Its repository had commits in July 2026.

Its stated purpose is to provide Apple ARM device guest support as a derivative of QEMU.

It contains Apple device-emulation work descended from the earlier QEMU Apple Silicon / T8030 ecosystem and also contains the QEMU `vmapple` machine implementation.

There is an open project issue requesting **macOS 27 support for vmapple**:

<https://github.com/ChefKissInc/Inferno/issues/303>

### Why it is highly relevant

Inferno brings two bodies of work close together:

1. physical Apple ARM/iPhone-style device emulation,
2. VMApple macOS virtual-machine support.

It therefore contains useful implementations and research for Apple-specific CPUs, peripherals, firmware-facing behavior, SEP-related experimentation, and VMApple.

### Why we should not claim it already solves our project

Its Apple device emulation is primarily oriented toward iPhone/iOS targets, and its vmapple path still inherits the existing VMApple assumptions. The existence of an open macOS 27 support request also makes clear that current modern macOS support is incomplete.

### Baseline decision

Inferno is the closest **active research/reference tree** found during this update.

For early AppleSilicon development we should:

- keep a pinned Inferno/upstream-QEMU reference,
- isolate our changes as a clear patch series or fork,
- avoid copying Apple proprietary binaries into this repository,
- carefully preserve the licensing requirements of inherited QEMU/Inferno code.

---

## 3. `qemu-t8030`

Repository: <https://github.com/TrungNguyen1909/qemu-t8030>

### What it achieved

`qemu-t8030` is a QEMU derivative implementing an emulated T8030/A13-class iPhone platform. It is direct evidence that a large amount of Apple-specific ARM SoC behavior can be modeled in software rather than requiring genuine Apple hardware.

### Limitations

- iPhone 11 / A13 oriented, not an M-series Mac.
- iOS oriented, not modern macOS.
- archived.
- old compared with current QEMU and current Apple operating systems.
- historical workflows use significant guest/kernel patching.

### Use for AppleSilicon

Research/reference only. Individual device implementations and CPU behavior may be useful, but we should not base the whole project on this old QEMU tree unless a particular component proves impossible to recover cleanly elsewhere.

---

## 4. `xnu-qemu-arm64`

Repository: <https://github.com/alephsecurity/xnu-qemu-arm64>

### What it achieved

This project booted ARM64 XNU/iOS under QEMU far enough to provide services including an interactive shell, storage, networking/tunneling, framebuffer output, debugging, and KVM experimentation.

### Limitations

Its documented target is older iOS rather than Apple-Silicon macOS, and it deliberately patches several guest security and kernel behaviors.

### Use for AppleSilicon

Its KVM and XNU bring-up work is useful prior art for understanding how to move ARM64 XNU execution from pure emulation toward hardware virtualization.

---

## 5. Asahi Linux `m1n1`

Repository: <https://github.com/AsahiLinux/m1n1>

Documentation:

- <https://asahilinux.org/docs/sw/m1n1-hypervisor/>
- <https://asahilinux.org/docs/fw/adt/>
- <https://asahilinux.org/docs/platform/introduction/>

### Why this is essential

m1n1 can run XNU/macOS as a guest on real Apple Silicon while tracing hardware access. This gives us a controlled way to answer questions such as:

- Which system register was accessed?
- Which MMIO address was read or written?
- Which interrupt arrived?
- What values does real Apple hardware return?
- Which Device Tree properties were supplied?

Asahi's documentation also describes Apple's ARM64 XNU boot protocol and Apple Device Tree format.

### Use for AppleSilicon

m1n1 is the preferred **behavior oracle / tracing environment** for physical Apple-Silicon contracts that are not already represented by VMApple.

---

## 6. Apple open-source XNU

Repository: <https://github.com/apple-oss-distributions/xnu>

XNU supports ARM64 and exposes a substantial amount of kernel-side architecture and platform behavior in source.

### Use for AppleSilicon

Use XNU source to identify:

- ARM64 feature assumptions,
- Apple-specific code paths,
- CPU initialization behavior,
- exception and timer expectations,
- virtual-memory/page-size behavior,
- IOKit matching and platform expectations that are visible in open source.

XNU source does not document all proprietary hardware, so it is a source of **guest expectations**, not a complete hardware specification.

---

# Decision for the first implementation generation

We will **not** begin by writing a new emulator from an empty C project.

The practical starting architecture is:

```text
AppleSilicon repository
        |
        +-- documentation / tests / tools
        +-- pinned upstream QEMU/Inferno reference
        +-- AppleSilicon patch series
                    |
                    v
             vmapple machine
                    |
          Apple-compatible CPU layer
                    |
           TCG first / KVM later
```

## Why TCG first

A generic-ARM KVM path can only expose or trap what the host virtualization architecture permits. TCG gives us full control over the virtual CPU contract and is therefore a better initial environment for discovering exactly which CPU features and system-register behaviors the Apple guest requires.

Performance is not a Part 1 objective.

Correctness and observability are.

Once the virtual CPU contract is understood, compatible behavior can be moved to KVM-assisted execution where possible.

# Conclusion

There is no repository to clone that simply gives us "macOS 27 on Snapdragon" today.

But there is enough existing work that AppleSilicon should be treated as an **integration, compatibility, and reverse-engineering project**, not as a from-scratch ARM emulator.

The most important immediate assets are:

```text
QEMU vmapple         -> virtual Mac platform contract
Inferno              -> active Apple ARM emulation research/code
m1n1                 -> real-hardware tracing
XNU source           -> guest-side expectations
qemu-t8030           -> historical physical Apple SoC emulation
xnu-qemu-arm64       -> historical ARM64 XNU + QEMU/KVM bring-up
```

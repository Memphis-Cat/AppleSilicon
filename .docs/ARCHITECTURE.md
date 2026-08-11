# Architecture

Project version: **`0.1.0.0.0.0`**

## Goal

Present a guest-visible machine that satisfies the contracts expected by ARM64 macOS without requiring the physical host to contain an Apple CPU.

The design must distinguish four different things that are often incorrectly collapsed into the word "Hackintosh":

1. boot environment,
2. CPU architectural compatibility,
3. virtual platform/device compatibility,
4. optional guest integration.

## Layer model

```text
+----------------------------------------------------------+
|                         macOS                            |
|  WindowServer / launchd / frameworks / Apple services   |
+----------------------------------------------------------+
|                          XNU                             |
|  ARM64 kernel / IOKit / Apple platform drivers          |
+----------------------------------------------------------+
|            guest-visible Apple-compatible machine       |
|                                                          |
| CPU contract | timers | IRQ | config | storage | gfx ... |
+----------------------------------------------------------+
|               AppleSilicon compatibility layer           |
|                                                          |
| CPU feature/sysreg model                                 |
| platform behavior                                       |
| tracing                                                  |
| deterministic fault reporting                            |
+----------------------------------------------------------+
|                  QEMU machine framework                  |
|           TCG initially / KVM acceleration later         |
+----------------------------------------------------------+
|          non-Apple ARM64 host or development host        |
+----------------------------------------------------------+
```

## Why this is not primarily an OpenCore project

OpenCore operates in the boot/firmware layer. Our hardest missing contracts continue to matter after the kernel begins executing.

Examples include:

- CPU system registers,
- architectural feature bits,
- exception behavior,
- page-table behavior,
- timers,
- interrupt delivery,
- MMIO devices,
- paravirtual devices.

A bootloader cannot emulate these after control has transferred to XNU unless a lower hypervisor/emulator layer exists.

OpenCore integration may become useful later for boot management, configuration, or compatibility conveniences, but it is not the foundation of the project.

## Why this is not primarily a kext project

A kext cannot solve a failure that occurs before XNU is capable of loading kexts.

The core machine contract therefore lives outside the guest.

Future guest drivers may be useful for AppleSilicon-specific paravirtual devices, but they should not be required to make the CPU or early platform believable.

## Two possible machine targets

### Target A — VMApple-compatible virtual Mac

```text
macOS
  -> Apple's virtual-Mac expectations
  -> VMApple-compatible machine
  -> AppleSilicon CPU compatibility
  -> QEMU
```

This is the initial target because upstream QEMU already implements much of this device model.

### Target B — physical M-series-like SoC

```text
macOS
  -> physical Apple platform drivers
  -> emulated Apple SoC
  -> AIC / DART / ANS / SMC / ASC / AGX / ...
  -> QEMU
```

This is a later research direction. It provides a stronger form of physical-machine compatibility but requires dramatically more hardware emulation.

Part 1 targets **A**, not B.

## CPU strategy

The CPU layer should eventually provide an explicit virtual CPU model such as:

```text
apple-compat-v1
```

rather than relying forever on:

```text
-cpu host
```

The virtual CPU model must document every non-generic behavior it exposes.

The implementation order is:

1. ordinary AArch64 behavior supplied by QEMU,
2. required architectural extensions already modeled by QEMU,
3. required ID-register values,
4. Apple-specific or implementation-defined system registers,
5. Apple-specific instructions/quirks if encountered,
6. exception/trap semantics,
7. optimization through KVM after correctness is established.

## Device strategy

Do not emulate physical Apple hardware when VMApple already gives macOS a supported paravirtual device contract.

Prefer, in order:

1. existing upstream VMApple devices,
2. existing generic QEMU devices that macOS VMApple already expects,
3. clean new paravirtual compatibility devices,
4. physical Apple device emulation only where the guest genuinely requires it.

## Boot strategy

The first generation should reuse the known VMApple boot environment to establish a reference boot.

Longer term, the project should document exactly what the pre-boot component provides and determine which pieces can be replaced by an open implementation without redistributing Apple proprietary material.

## Research strategy

When execution fails:

```text
boot
  -> capture exact exception/panic
  -> identify instruction/register/device involved
  -> reproduce behavior on reference Apple hardware or reference VM
  -> document contract
  -> implement minimum correct behavior
  -> add regression test
  -> boot again
```

Do not replace this loop with random feature spoofing.

## Success levels

The project should record progress as independent capability levels:

```text
L0  emulator starts
L1  VMApple firmware entry executes
L2  XNU entry reached
L3  early kernel console stable
L4  VM and scheduler stable
L5  storage root mounted
L6  launchd/userspace reached
L7  framebuffer GUI reached
L8  networking/input usable
L9  accelerated graphics / broader integration
```

These are engineering milestones, not version numbers.

# Part 01 — VMApple Baseline and Host-Dependency Map

Project version: **`0.2.0.0.0.0`**

Status: **Documentation / research phase**

## Purpose

Part 01 turns the current public VMApple work into a reproducible reference and answers one concrete question:

> What exactly prevents a VMApple macOS guest from running when the virtual CPU is no longer backed by a real Apple Silicon host CPU?

This part does **not** attempt to implement every missing Apple Silicon component.

It creates the environment in which every later component can be discovered and implemented one at a time.

## Sub-objectives

Part 01 is split into smaller objectives. The first detailed objective is:

- [P1.01 — Logged VMApple Baseline Harness](P1.01.md)

P1.01 establishes mandatory persistent `.log` output before deeper VMApple experiments begin.

Later objectives will continue the sequence as `P1.02`, `P1.03`, and so on rather than requiring Part 01 to be completed all at once.

## Maintainer testing rule

The maintainer will not be asked to manually test every Part 01 objective or intermediate release.

Manual maintainer testing is reserved for the finished integration stage. Development-side build checks, source inspection, automated tests, emulator probes, and generated logs should be used during the project instead.

## Logging rule

Every meaningful runtime experiment in Part 01 must create a persistent `.log` file, including failed runs.

The default location is:

```text
logs/AppleSilicon-YYYYMMDD-HHMMSS-PID.log
```

Console output alone is not accepted as the only record of a runtime experiment.

---

# Part 01 success condition

Part 01 is complete when all of the following are true:

1. We can build the pinned emulator/reference tree reproducibly.
2. We have a documented known-good VMApple reference path using legally obtained local guest material where authorized development hardware is available.
3. We have deterministic serial/QEMU logging from reference and probe runs.
4. We can force the same VMApple machine toward a non-host CPU path under TCG.
5. The first divergence/failure between the known-good Apple-host path and the generic virtual CPU path is identified precisely.
6. That divergence is recorded as a named CPU/platform contract with a regression test or minimal reproducer.
7. We have a written dependency map showing which known requirements are CPU, boot, or device-model problems.

A GUI is not required.

A complete XNU boot is not required on the generic CPU path.

The important output is the **first understood incompatibility**, because that becomes the next compatibility objective.

---

# Objective tree

## P01.O1 — Freeze an upstream reference

Pin the exact source revision used for experiments.

Primary candidates:

- ChefKiss Inferno for the active Apple ARM/QEMU research tree.
- Upstream QEMU for the cleanest current VMApple implementation.

Record:

```text
repository
commit SHA
host OS
host CPU
compiler
Meson version
Ninja version
QEMU configure arguments
```

Do not write documentation against an unspecified `master` checkout and later assume behavior is unchanged.

### Acceptance

A clean checkout at the pinned revision builds from documented commands.

---

## P01.O2 — Build a known-good VMApple reference

Upstream QEMU currently documents VMApple with:

```text
Apple Silicon host
macOS host
HVF
VMApple machine
Apple Virtualization.framework pre-boot environment
macOS 12 virtual-machine guest material
```

The reference command shape documented by upstream is approximately:

```bash
qemu-system-aarch64 \
  -serial mon:stdio \
  -m 4G \
  -accel hvf \
  -M vmapple,uuid="$UUID" \
  -bios "$AVPBOOTER" \
  -drive file="$AUX",if=pflash,format=raw \
  -drive file="$DISK",if=pflash,format=raw \
  -drive file="$AUX",if=none,id=aux,format=raw \
  -drive file="$DISK",if=none,id=root,format=raw \
  -device vmapple-virtio-blk-pci,variant=aux,drive=aux \
  -device vmapple-virtio-blk-pci,variant=root,drive=root
```

Source: <https://www.qemu.org/docs/master/system/arm/vmapple.html>

This command is a **reference**, not our final product design.

### Repository rule

Do not commit:

- AVPBooter,
- macOS disk images,
- IPSWs/installers,
- machine-specific secrets,
- Apple keys,
- extracted proprietary firmware.

All such material remains local to the authorized development machine.

### Logging

Runtime output from this objective must be routed through the project logging infrastructure or an equivalent launcher that produces persistent `.log` files.

### Acceptance

Capture locally:

```text
artifacts/reference/
  host-info.txt
  qemu-version.txt
  command-redacted.txt
  serial.log
  qemu.log
```

The repository should contain scripts/templates later, not proprietary inputs.

---

## P01.O3 — Inventory the current VMApple hardware contract

From upstream `hw/vmapple/vmapple.c`, record the currently modeled blocks and their addresses/interrupts.

Current upstream code includes a VMApple configuration region plus devices such as GICv3, UART, RTC, GPIO, PCIe, paravirtual graphics, AES, the VMApple backdoor interface, and Apple-specific virtio block behavior.

The important discovery here is that **VMApple is not a virtual physical M1**.

It uses a deliberately virtualized machine contract containing several generic ARM/QEMU components. This is good for our initial goal because we do not need AIC/ANS/DART/AGX physical emulation simply to reproduce VMApple.

### Acceptance

Create a machine-contract table containing:

```text
component
QEMU model
MMIO range
IRQ
required at boot?
known guest driver
host-dependent?
```

---

## P01.O4 — Inventory the CPU contract

Upstream VMApple currently defaults to:

```text
ARM_CPU_TYPE_NAME("host")
```

This is one of the most important lines in the current implementation.

It means that on the known-good HVF path, the guest CPU model inherits the real Apple Silicon CPU exposed through the host virtualization layer.

Our first CPU investigation therefore asks:

```text
What does `host` provide that a generic QEMU ARM CPU does not?
```

Collect at minimum:

- MIDR/MPIDR behavior visible to the guest,
- ID_AA64* feature registers,
- page-granule support,
- pointer-authentication features,
- timer configuration,
- exception levels presented to the guest,
- implementation-defined system register accesses,
- Apple-specific registers/instructions reached by pre-boot/XNU,
- behavior of secondary CPU startup.

### Acceptance

Produce a first CPU requirement matrix:

```text
requirement | Apple host | QEMU max | generic ARM host | required by stage
```

Unknown values are allowed. They must be marked unknown rather than guessed.

---

## P01.O5 — Create the TCG divergence run

The first generic path should use TCG because it gives us full control of the guest CPU model.

Initial experiment shape:

```bash
qemu-system-aarch64 \
  -accel tcg \
  -cpu max \
  -M vmapple,...
```

This is expected to fail.

**The failure is the experiment.**

Instrument:

```text
-d guest_errors,unimp,int,cpu_reset
-D apple-silicon-tcg.log
```

Additional QEMU trace events should be enabled as required.

The command must also run through the project logged-run infrastructure so launcher metadata and exit state survive even if QEMU's own trace output terminates unexpectedly.

We are looking for the earliest meaningful difference, such as:

```text
unsupported system register
undefined instruction
unexpected CPU feature test
page-table setup failure
firmware assumption
interrupt/timer divergence
VMApple config mismatch
```

### Acceptance

The first failure must be reproducible from a clean start and written as:

```text
P01-DIVERGENCE-0001

Stage:
PC:
Instruction/access:
Observed result:
Expected result:
Reference evidence:
Hypothesis:
Reproducer:
Log file:
```

---

## P01.O6 — Build differential tracing

We need two traces:

```text
A: known-good Apple host + HVF + vmapple
B: TCG + explicit non-host CPU + vmapple
```

Normalize volatile values, then compare the traces as early as possible in boot.

Useful trace categories include:

- CPU exceptions,
- system-register accesses,
- MMIO,
- interrupts,
- timer programming,
- VMApple config reads,
- block-device requests,
- firmware transitions.

### Acceptance

A comparison tool or documented manual process identifies the earliest divergence without requiring visual inspection of megabytes of unrelated logs.

---

## P01.O7 — Prepare real-hardware tracing for unknown Apple behavior

If a behavior cannot be explained from QEMU, Inferno, XNU, or public documentation, use a real Apple Silicon reference machine and m1n1 where appropriate.

Asahi documents running XNU/macOS under the m1n1 hypervisor and preloading hardware tracing modules.

Primary documentation:

<https://asahilinux.org/docs/sw/m1n1-hypervisor/>

The research loop is:

```text
unknown guest expectation
       ↓
identify code/register/device
       ↓
trace authorized reference hardware
       ↓
record behavior
       ↓
implement minimum compatible model
       ↓
regression test
```

### Acceptance

The repository has a documented trace format and no machine secrets are committed accidentally.

---

# First code that should eventually be added

Part 01 should not begin with an `AppleM1CPU` class containing hundreds of guessed registers.

The first observable infrastructure now starts with:

```text
src/
  tools/
    run-logged.sh
```

Later Part 01 source work is expected to include:

```text
src/
  patches/
    0001-vmapple-allow-explicit-tcg-cpu.patch
  tools/
    compare-boot-traces.py
  configs/
    reference-hvf.example
    tcg-probe.example
```

The initial VMApple patch should make it easy to select a non-`host` CPU for VMApple without changing unrelated device behavior.

Then the trace comparison tells us what CPU compatibility code is actually necessary.

---

# Part 01 non-goals

Do not spend Part 01 implementing:

- AGX GPU acceleration,
- Secure Enclave completeness,
- Touch ID,
- Apple Intelligence/ANE,
- sleep/wake,
- Thunderbolt,
- Wi-Fi,
- audio,
- OpenCore integration,
- custom kexts,
- physical M1 AIC/DART/ANS emulation.

Those may become future parts if the selected guest-machine contract requires them.

---

# Expected later direction

Part 02 is intentionally **not named yet**.

Its title will be derived from the first real compatibility divergence discovered after the Part 01 baseline and probe objectives.

For example, if the first blocker is an implementation-defined Apple system register, Part 02 might become:

```text
Part 02 — Apple CPU System Register Compatibility v1
```

If it is a page-granule/MMU issue:

```text
Part 02 — VMApple 16K Guest MMU Bring-Up
```

This keeps the project evidence-driven instead of inventing an enormous roadmap whose ordering may be wrong.

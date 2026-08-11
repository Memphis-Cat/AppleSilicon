# Part 01 — VMApple Baseline and Host-Dependency Map

Project version: **`0.8.0.0.0.0`**

Status: **Active — tooling and dependency-decoupling objectives in progress; runtime reference/probe collection deferred**

## Purpose

Part 01 answers one concrete question:

> What is the first precise compatibility difference that prevents the VMApple machine from progressing when its guest CPU is no longer backed by the known Apple/HVF reference path?

Part 01 does not try to implement an entire Apple Silicon SoC at once.

It builds the reproducible environment, removes host-only construction assumptions one at a time, defines the controlled TCG path, and creates the evidence tooling needed to discover the first real incompatibility.

## Project-wide rules applied to Part 01

### Maintainer testing

The project owner is not asked to manually test individual objectives, updates, fixes, or hotfixes.

Manual testing is reserved for the finished integration stage. Intermediate objectives should rely on source inspection, build checks, deterministic tooling, synthetic fixtures, and automated validation whenever possible.

### Logging

Every meaningful executable AppleSilicon operation must leave a persistent `.log`.

Default local artifact roots are:

```text
.logs/
.build/
```

These directories are ignored by Git.

### Repository naming

Project-owned directories are lowercase and dot-prefixed.

Examples:

```text
.docs/
.src/
.src/.configs/
.src/.patches/
.src/.tools/
.src/.fixtures/
.src/.upstream/.inferno/
```

## Upstream reference

The active pinned research base is:

```text
ChefKissInc/Inferno
cc4302a99167abec69b714cfd00c38caece7e7de
```

The pinned upstream is kept pristine. AppleSilicon changes are represented as ordered project patches or project-owned tools/configuration around disposable prepared source trees.

## Part 01 objective sequence

### P1.01 — Logged VMApple Baseline Harness

Status: **Implementation complete**

Established mandatory persistent logging before deeper experiments.

### P1.02 — Reproducible Inferno Build Baseline

Status: **Implementation complete — runtime build deferred**

Defined the pinned Inferno build contract and logged build harness.

### P1.03 — VMApple Capability and Build-Gate Probe

Status: **Implementation complete — runtime capability probe deferred**

Established source/binary inspection of VMApple, accelerators, CPU models, and the original HVF build dependency.

### P1.04 — Decouple VMApple Build From HVF

Status: **Implementation complete — runtime build deferred**

Added:

```text
.src/.patches/0001-vmapple-decouple-build-from-hvf.patch
```

The VMApple build gate no longer requires HVF in the prepared source. The Apple/HVF reference behavior remains otherwise intact.

### P1.05 — Decouple VMApple Machine Realization From Apple PVG

Status: **Implementation complete — runtime realization deferred**

Added:

```text
.src/.patches/0002-vmapple-optional-apple-pvg.patch
```

VMApple now attempts to create `apple-gfx-mmio` through QEMU's safe optional-device path. When the Darwin-only PVG implementation is unavailable, the prepared research machine can continue without inventing fake GPU behavior.

### P1.06 — Explicit Non-Host VMApple CPU Selection

Status: **Implementation complete — runtime CPU probe deferred**

Research confirmed that QEMU already routes an explicit `-cpu` model into `MachineState::cpu_type`, and VMApple creates its CPUs from that value.

Controlled non-host profiles are:

```text
TCG + max
TCG + apple-gxf
```

`host` remains the reference default and is not silently replaced.

### P1.07 — TCG VMApple Pre-Boot Probe Harness

Status: **Implementation complete — runtime launch deferred**

Created the first complete controlled launch specification:

```text
VMApple
 + P1.04
 + P1.05
 + TCG
 + max/apple-gxf
 + local authorized boot inputs
 + finite execution window
 + persistent diagnostics
```

The runtime harness records launcher output, serial/stderr evidence, QEMU debug output, trace capability information, timeout/exit classification, and does not store proprietary Apple inputs in the repository.

Initial trace events:

```text
memory_region_ops_read
memory_region_ops_write
```

Initial debug categories:

```text
guest_errors
unimp
int
cpu_reset
```

### P1.08 — VMApple Trace Normalization and Earliest-Divergence Extraction

Status: **Implementation complete — real trace comparison deferred**

Added:

```text
.docs/P1.08.md
.src/.configs/p1.08-compare.json
.src/.tools/compare-boot-traces.py
.src/.tools/prepare-p1.08.sh
.src/.fixtures/.p1.08/
```

The comparator normalizes host-only QEMU trace noise while preserving guest-semantic MMIO data:

```text
event
CPU index
guest address
value
size
region name
ordering
```

It reports the earliest mismatch, classifies it, preserves raw/source-line evidence, and performs only bounded resynchronization.

Synthetic fixtures validate:

```text
host-noise equivalence
MMIO value divergence
sequence insertion/resynchronization
```

No synthetic result is allowed to become `P01-DIVERGENCE-0001`.

### P1.09 — Reference Trace Manifest and Real-Hardware Trace Preparation

Status: **Next objective**

P1.09 will define exactly what constitutes the reference side of the first real comparison:

```text
host identity/capabilities
QEMU/Inferno revision
VMApple configuration
CPU/accelerator selection
redacted command shape
trace event set
log/artifact hashes
reference run metadata
probe run metadata
sanitization rules
```

It will also prepare the real-hardware/reference tracing workflow for behavior that cannot be explained from public source alone, without requiring immediate maintainer testing.

---

# Engineering objective map

The detailed P1.xx sequence implements the original Part 01 engineering objectives as follows.

## O1 — Freeze upstream reference

Implemented by P1.01–P1.03.

The exact Inferno revision is pinned and all later source assumptions are checked against it.

## O2 — Reproducible reference/probe build environment

Implemented structurally by P1.02–P1.05.

Actual final integration builds/runs remain deferred under project policy.

## O3 — Inventory VMApple host dependencies

Implemented progressively by P1.03–P1.05.

Confirmed early dependencies included:

```text
HVF build gating
Darwin-only Apple PVG realization
host CPU default
```

## O4 — Controlled CPU contract

Implemented structurally by P1.06.

The known reference default remains:

```text
ARM_CPU_TYPE_NAME("host")
```

The controlled non-host path can explicitly select:

```text
max
apple-gxf
```

under TCG.

## O5 — Controlled TCG divergence run

Runtime harness implemented by P1.07.

Actual guest execution is intentionally deferred.

## O6 — Differential tracing

Analysis implementation completed by P1.08.

Real A/B trace collection is intentionally deferred.

## O7 — Reference/real-hardware evidence preparation

Begins with P1.09.

If a future mismatch cannot be explained from QEMU, Inferno, XNU, or published documentation, authorized Apple Silicon reference tracing may use tools such as m1n1 where appropriate.

---

# Part 01 success condition

Part 01 is complete only when all of these are satisfied:

1. The pinned emulator tree and AppleSilicon patch chain are reproducible.
2. The reference VMApple experiment is fully described with non-secret metadata.
3. The controlled TCG VMApple experiment is fully described with the same comparison contract.
4. Reference and probe runs produce deterministic persistent evidence.
5. The trace normalization/comparison tooling can consume that evidence.
6. The **first real divergence** is reproducible and precisely located.
7. The divergence is promoted from candidate to:

```text
P01-DIVERGENCE-0001
```

8. The divergence is documented as a specific CPU/platform contract with a reproducer or regression check.
9. The evidence shows what the next compatibility part should actually implement.

A GUI is not required.

A complete generic-ARM XNU boot is not required.

The core Part 01 deliverable is the **first understood incompatibility**.

---

# Confirmed divergence report format

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

Unknown values must remain marked unknown rather than guessed.

---

# Part 01 non-goals

Part 01 does not attempt to complete:

- AGX GPU acceleration,
- Secure Enclave emulation,
- Activation Lock or account-security bypasses,
- Touch ID,
- ANE/Apple Intelligence,
- sleep/wake,
- Thunderbolt,
- Wi-Fi,
- audio,
- OpenCore integration,
- custom compatibility kexts,
- full physical M-series AIC/DART/ANS/AGX emulation.

Those belong to later evidence-driven parts only if the selected guest-machine contract actually requires them.

---

# Later direction

Part 02 remains intentionally unnamed.

Its title will be derived from `P01-DIVERGENCE-0001` rather than guessed in advance.

Examples only:

```text
Part 02 — Apple CPU System Register Compatibility v1
```

or:

```text
Part 02 — VMApple 16K Guest MMU Bring-Up
```

The first real evidence decides the next part.

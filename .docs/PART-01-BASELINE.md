# Part 01 — VMApple Baseline and Host-Dependency Map

Project version: **`0.9.0.0.0.0`**

Status: **Active — reference/probe evidence contract implemented; real A/B collection and divergence promotion remain deferred**

## Purpose

Part 01 answers one concrete question:

> What is the first precise compatibility difference that prevents the VMApple machine from progressing when its guest CPU is no longer backed by the known Apple/HVF reference path?

Part 01 does not attempt to implement an entire Apple Silicon SoC at once.

It builds the reproducible environment, removes host-only construction assumptions one at a time, defines the controlled TCG path, and creates the evidence tooling needed to discover the first real incompatibility.

## Project-wide rules applied to Part 01

### Maintainer testing

The project owner is not asked to manually test individual objectives, updates, fixes, or hotfixes.

Manual testing is reserved for the finished integration stage. Intermediate objectives rely on source inspection, build checks, deterministic tooling, synthetic fixtures, and automated validation whenever possible.

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

The comparator normalizes host-only QEMU trace noise while preserving guest-semantic MMIO data, reports the earliest mismatch, classifies it, preserves raw/source-line evidence, and performs only bounded resynchronization.

Synthetic fixtures validate host-noise equivalence, MMIO value divergence, and sequence insertion/resynchronization.

No synthetic result is allowed to become `P01-DIVERGENCE-0001`.

### P1.09 — Reference Trace Manifest and Real-Hardware Trace Preparation

Status: **Implementation complete — real reference/probe collection deferred**

Added:

```text
.docs/P1.09.md
.src/.configs/p1.09-manifest-policy.json
.src/.configs/p1.09-reference.example.json
.src/.configs/p1.09-probe.example.json
.src/.tools/reference-manifest.py
.src/.tools/prepare-p1.09.sh
.src/.tools/run-p1.09-reference.sh
```

P1.09 makes reference/probe comparability machine-checkable before a trace difference can be interpreted.

The equality contract covers:

```text
pinned Inferno repository/revision
VMApple machine type
RAM/SMP
trace event set
debug category set
firmware hash + size
auxiliary-storage hash + size
disk hash + size
machine-identity hash + size
hardware-model digest metadata when available
```

Expected differences remain explicit:

```text
reference: HVF + host CPU + Apple Silicon macOS host
probe:     TCG + max/apple-gxf + development host
```

The manifest validator rejects raw UUID/account/private-key/local-user-path material. The collector stores hashes/sizes and artifact basenames rather than copying local guest material.

A finite HVF reference runner is now defined and fail-closed to Darwin/arm64. It is reserved for final integration evidence collection.

m1n1 is documented only as a secondary authorized real-hardware tracing escalation path, not as a substitute for the primary VMApple/HVF A-side trace.

### P1.10 — Controlled A/B Evidence Bundle and Divergence Promotion Gate

Status: **Next objective**

P1.10 will connect the existing pieces into one evidence pipeline:

```text
P1.09 HVF reference run
P1.07 TCG probe run
P1.09 manifest collection/pair validation
P1.08 trace normalization/comparison
candidate report
promotion gate
```

The gate must refuse to create `P01-DIVERGENCE-0001` unless the A/B manifests satisfy P1.09 and P1.08 identifies a real, reproducible candidate from actual runtime evidence.

---

# Engineering objective map

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

The known reference default remains `host`; the controlled non-host path selects `max` or `apple-gxf` under TCG.

## O5 — Controlled TCG divergence run

Runtime harness implemented by P1.07.

Actual guest execution is intentionally deferred.

## O6 — Differential tracing

Analysis implementation completed by P1.08.

Real A/B trace collection is intentionally deferred.

## O7 — Reference/real-hardware evidence preparation

Implemented structurally by P1.09.

The primary reference is VMApple/HVF. m1n1 remains a separate escalation environment for authorized hardware tracing when a future behavior cannot be explained from public sources or the primary reference.

---

# Part 01 success condition

Part 01 is complete only when all of these are satisfied:

1. The pinned emulator tree and AppleSilicon patch chain are reproducible.
2. The reference VMApple experiment is fully described with non-secret metadata.
3. The controlled TCG VMApple experiment is fully described with the same comparison contract.
4. Reference and probe runs produce deterministic persistent evidence.
5. The reference/probe manifests satisfy the P1.09 pairing contract.
6. The trace normalization/comparison tooling consumes that evidence.
7. The **first real divergence** is reproducible and precisely located.
8. The divergence is promoted from candidate to:

```text
P01-DIVERGENCE-0001
```

9. The divergence is documented as a specific CPU/platform contract with a reproducer or regression check.
10. The evidence shows what the next compatibility part should actually implement.

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

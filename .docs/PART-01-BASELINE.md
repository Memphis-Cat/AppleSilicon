# Part 01 — VMApple Baseline and Host-Dependency Map

Project version: **`1.0.0.0.0.0`**

Status: **Implementation sequence closed at P1.10 — real A/B execution and empirical divergence promotion deferred**

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

VMApple attempts to create `apple-gfx-mmio` through QEMU's optional-device path. When the Darwin-only PVG implementation is unavailable, the prepared research machine can continue without inventing fake GPU behavior.

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

Created the controlled TCG launch specification with local authorized boot inputs, finite execution, trace capability checking, and persistent logs.

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

The comparator removes only host-runtime noise, preserves guest-semantic MMIO information, reports the earliest mismatch, classifies it, and performs bounded resynchronization.

Synthetic fixtures prove host-noise equivalence, MMIO-value divergence detection, and insertion/resynchronization handling.

### P1.09 — Reference Trace Manifest and Real-Hardware Trace Preparation

Status: **Implementation complete — real reference/probe collection deferred**

P1.09 makes A/B comparability machine-checkable.

The equality contract includes the pinned source, VMApple machine type, RAM/SMP, trace/debug sets, and hashes/sizes for firmware, auxiliary storage, disk, machine identity, and optional hardware-model metadata.

Expected differences remain explicit:

```text
reference: HVF + host CPU + Apple Silicon macOS host
probe:     TCG + max/apple-gxf + development host
```

P1.09 also defines the fail-closed HVF reference runner and keeps m1n1 as a separate secondary authorized-hardware escalation path.

### P1.10 — Controlled A/B Evidence Bundle and Divergence Promotion Gate

Status: **Implementation complete — real runtime promotion deferred**

P1.10 is the final Part 01 implementation objective.

Added:

```text
.docs/P1.10.md
.src/.configs/p1.10-promotion-policy.json
.src/.tools/evidence-bundle.py
.src/.tools/collect-p1.10-probe.sh
.src/.tools/prepare-p1.10.sh
```

P1.10 connects:

```text
P1.09 reference evidence
P1.07 probe evidence
P1.10 probe-manifest collection
P1.09 manifest pairing
artifact-integrity verification
P1.08 trace comparison
candidate generation
reproduction gate
```

A single real A/B mismatch may create only:

```text
P01-DIVERGENCE-CANDIDATE
```

Promotion to:

```text
P01-DIVERGENCE-0001
```

requires at least two unique runtime A/B run pairs with:

```text
same P1.09 contract fingerprint
same earliest-divergence signature
verified trace artifact hashes
promotion-eligible runtime results
```

Synthetic, fixture, example, self-check, unverified, and not-run results are barred from promotion.

P1.10 never auto-commits a promoted record.

---

# Engineering objective map

## O1 — Freeze upstream reference

Implemented structurally by P1.01–P1.03.

## O2 — Reproducible reference/probe build environment

Implemented structurally by P1.02–P1.05.

## O3 — Inventory VMApple host dependencies

Implemented structurally by P1.03–P1.05.

Confirmed early dependencies included:

```text
HVF build gating
Darwin-only Apple PVG realization
host CPU default
```

## O4 — Controlled CPU contract

Implemented structurally by P1.06.

## O5 — Controlled TCG divergence run

Runtime harness implemented by P1.07.

## O6 — Differential tracing

Normalization/comparison implementation completed by P1.08.

## O7 — Reference/real-hardware evidence preparation

Implemented structurally by P1.09.

## O8 — Evidence integration and promotion safety

Implemented structurally by P1.10.

---

# Part 01 implementation closure

The Part 01 implementation sequence is closed.

```text
P1.01
P1.02
P1.03
P1.04
P1.05
P1.06
P1.07
P1.08
P1.09
P1.10
```

There is no P1.11.

This does **not** mean a real guest divergence has already been observed. The project-wide testing rule intentionally defers the empirical A/B execution.

Current state:

```text
Part 01 code/documentation pipeline: implemented
real HVF reference runs: deferred
real TCG probe runs: deferred
real reproduced A/B comparison: deferred
P01-DIVERGENCE-0001: not assigned yet
```

## Empirical Part 01 success condition

When final integration testing is eventually performed, Part 01 is empirically successful only when:

1. the pinned emulator tree and AppleSilicon patch chain build as documented,
2. the reference VMApple experiment produces persistent evidence,
3. the controlled TCG VMApple experiment produces persistent evidence,
4. the reference/probe manifests satisfy the P1.09 pairing contract,
5. P1.10 verifies the selected trace artifacts against their manifest hashes,
6. P1.08 identifies the earliest real mismatch,
7. at least two independent run pairs reproduce the same divergence signature under the same contract fingerprint,
8. P1.10 promotes that evidence to `P01-DIVERGENCE-0001`,
9. the promoted record determines the concrete hardware/CPU/platform contract to implement next.

A GUI is not required.

A complete generic-ARM XNU boot is not required.

The core Part 01 empirical deliverable remains the **first understood incompatibility**.

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

Unknown values must remain unknown rather than guessed.

---

# Part 01 non-goals

Part 01 does not complete:

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

# Next project unit

The next project unit is:

```text
Part 02
```

Part 02 begins compatibility implementation rather than baseline isolation.

Its exact hardware-contract title should be derived from the first real `P01-DIVERGENCE-0001` once final integration evidence exists. Until then, unknown Apple-specific register/MMU/device behavior must not be filled with guessed implementations merely to keep development moving.

# Part 02 — Apple CPU Compatibility Contract

Project version: **`2.1.0.0.0.0`**

Status: **Active — P2.01 and P2.02 implemented**

## Purpose

Part 01 built the VMApple reference/probe and evidence pipeline. Part 02 begins the CPU compatibility layer.

Because the project-wide testing rule defers real HVF/TCG guest runs until final integration, Part 02 must not invent a fake `P01-DIVERGENCE-0001`. Until runtime evidence exists, CPU work is restricted to contracts that are supported by primary source evidence and can be validated statically.

The goal of Part 02 is:

> Give the TCG VMApple path a deliberate, reviewable Apple CPU compatibility layer for system registers and CPU-visible features without pretending to emulate an entire M-series SoC.

## Fixed objective count

Part 02 has exactly six implementation objectives:

```text
P2.01 — Apple CPU System Register and Feature Inventory
P2.02 — Apple System Register Emulation Framework
P2.03 — Register Read/Write/Reset Policy Model
P2.04 — CPU Feature and ID-Register Compatibility
P2.05 — Deterministic CPU Contract Regression Harness
P2.06 — Part 02 Integration Gate
```

There is **no P2.07**.

If new CPU requirements are discovered after P2.06, they belong to a later part or to an appropriate fix/emergency/hotfix release. The objective list must not grow merely because new research appears.

## P2.01 — Apple CPU System Register and Feature Inventory

Status: **Implementation complete — static inventory only**

P2.01 creates a machine-readable contract containing exact source identities, Apple implementation-defined system-register encodings, register families, feature notes, evidence provenance, runtime priority, and implementation state.

A register may exist on physical Apple Silicon and still be irrelevant to VMApple. Every imported entry therefore begins with unknown relevance/priority and inventory-only implementation state.

## P2.02 — Apple System Register Emulation Framework

Status: **Implementation complete — framework only**

P2.02 creates the project-owned QEMU/Inferno registration layer for Apple implementation-defined AArch64 system registers.

It uses QEMU's existing `ARMCPRegInfo`/cpreg infrastructure rather than implementing a second MRS/MSR decoder.

The framework introduces an encoding-only `AppleSysRegSpec`, a fail-closed explicit-undefined registration helper, and a TCG-only integration point in Inferno's existing `apple-gxf` CPU initializer.

Unknown semantics remain unknown. P2.02 deliberately registers **zero** guest-visible Apple sysreg policies by default. It does not add read-as-zero, write-ignore, constant, reset, or stored-state semantics.

The project patch is:

```text
.src/.patches/0003-arm-apple-sysreg-framework.patch
```

The development-side validator is:

```text
.src/.tools/prepare-p2.02.sh
```

## P2.03 — Register Read/Write/Reset Policy Model

Status: **Next**

P2.03 will make register behavior explicit and data-driven.

Candidate policy classes may include:

```text
stored state
read-as-zero
write-ignored
constant value
callback-driven behavior
access trap
```

but a policy may only be attached where its evidence and intended scope are recorded. Unknown behavior must remain fail-closed rather than silently falling into a convenient default.

## P2.04 — CPU Feature and ID-Register Compatibility

Status: **Planned**

P2.04 will handle architectural CPU feature exposure separately from Apple implementation-defined sysregs.

This includes the guest-visible contract around feature/ID registers, translation granules, pointer authentication, exception levels and other architectural capabilities that VMApple/XNU actually observes.

## P2.05 — Deterministic CPU Contract Regression Harness

Status: **Planned**

P2.05 will provide a non-guest regression harness that verifies registered Apple sysregs, encoding uniqueness, reset/access policy determinism, configured CPU feature exposure, and preservation of explicitly unknown behavior.

Every meaningful execution will write a `.log`.

## P2.06 — Part 02 Integration Gate

Status: **Planned — final Part 02 objective**

P2.06 will combine the Part 02 CPU compatibility work with the Part 01 prepared VMApple/TCG path.

The integration gate will remain compatible with the maintainer testing rule: deterministic source/build/regression validation is allowed during development, while real macOS execution remains reserved for final project integration testing.

After P2.06, Part 02 is closed.

## Evidence hierarchy

Part 02 uses evidence in this order:

1. real reproducible Part 01 A/B runtime evidence, once final integration testing exists;
2. public XNU source;
3. QEMU source and documented ARM system-register infrastructure;
4. Asahi/m1n1 source and authorized hardware traces;
5. pinned Inferno behavior;
6. clearly labeled hypotheses.

A lower-confidence source must not silently override higher-confidence evidence.

## Physical Apple Silicon versus VMApple

Part 02 deliberately separates these concepts.

Physical Apple Silicon contains many Apple implementation-defined CPU registers. VMApple is a virtual machine hardware contract and public XNU contains virtual-platform behavior that can differ from a physical Apple platform.

Therefore:

```text
known on Apple hardware
!=
proven required by VMApple
```

P2.01 records known encodings. P2.02 provides safe registration plumbing. Neither step manufactures VMApple requirements.

## Current source locks

The machine-readable P2.01 contract records exact source revisions/blobs for Apple XNU, QEMU, Asahi m1n1 and ChefKiss Inferno. P2.02 continues to target the pinned Inferno revision rather than an unreviewed moving branch.

## Logging and testing

The existing project rules remain active:

- the maintainer is not asked to manually test individual objectives;
- development-side static/self-check validation is allowed and expected;
- every meaningful executable project tool writes a `.log`;
- real guest testing remains deferred until final integration;
- no proprietary Apple firmware/images/secrets are committed.

## Part 02 completion condition

Part 02 is implementation-complete when P2.01 through P2.06 are complete.

Empirical success remains a separate final-integration question. We must not claim macOS accepts the compatibility layer until a real guest run actually demonstrates that.

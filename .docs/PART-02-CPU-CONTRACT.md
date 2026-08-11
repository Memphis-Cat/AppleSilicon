# Part 02 — Apple CPU Compatibility Contract

Project version: **`2.0.0.0.0.0`**

Status: **Active — P2.01 implemented**

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

P2.01 creates a machine-readable contract containing:

- exact source identities,
- Apple implementation-defined system-register encodings,
- register families,
- architectural/virtual-platform feature notes,
- evidence provenance,
- runtime priority,
- implementation state.

No register in P2.01 is automatically considered required by macOS.

A register may exist on physical Apple Silicon and still be irrelevant to VMApple. Therefore every inventory entry begins with:

```text
runtime_priority = unknown
implementation_state = inventory_only
xnu_relevance = unknown
```

unless a later objective has direct evidence allowing a stronger statement.

## P2.02 — Apple System Register Emulation Framework

Status: **Next**

P2.02 will create the project-owned QEMU/Inferno registration layer for Apple implementation-defined AArch64 system registers.

It will use QEMU's existing ARM coprocessor/system-register infrastructure rather than implementing a second instruction decoder.

P2.02 will establish registration, storage and trap plumbing only. It will not invent register semantics that are still unknown.

## P2.03 — Register Read/Write/Reset Policy Model

Status: **Planned**

P2.03 will make register behavior explicit and data-driven.

Future policies may include behavior such as:

```text
stored state
read-as-zero
write-ignored
constant value
callback-driven behavior
access trap
```

but only where evidence justifies that policy.

## P2.04 — CPU Feature and ID-Register Compatibility

Status: **Planned**

P2.04 will handle architectural CPU feature exposure separately from Apple implementation-defined sysregs.

This includes the guest-visible contract around feature/ID registers, translation granules, pointer authentication, exception levels and other architectural capabilities that VMApple/XNU actually observes.

## P2.05 — Deterministic CPU Contract Regression Harness

Status: **Planned**

P2.05 will provide a non-guest regression harness that verifies:

- every registered Apple sysreg has one encoding,
- no two incompatible definitions collide,
- reset/access policy is deterministic,
- configured CPU feature exposure matches the contract,
- unknown behavior remains explicitly unknown instead of silently defaulting.

Every meaningful execution will write a `.log`.

## P2.06 — Part 02 Integration Gate

Status: **Planned — final Part 02 objective**

P2.06 will combine the Part 02 CPU compatibility work with the Part 01 prepared VMApple/TCG path.

The integration gate will remain compatible with the maintainer testing rule: it can provide deterministic source/build/regression validation now, while real macOS execution remains reserved for final project integration testing.

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

Physical Apple Silicon contains many Apple implementation-defined CPU registers. m1n1 documents a large set of them.

VMApple is a virtual machine hardware contract. Public XNU contains `APPLEVIRTUALPLATFORM`/`VMAPPLE` behavior that can differ from a physical Apple platform.

Therefore:

```text
known on Apple hardware
!=
proven required by VMApple
```

P2.01 records the first fact without manufacturing the second.

## Current source locks

The machine-readable P2.01 contract records exact source revisions/blobs for:

```text
Apple XNU
QEMU
Asahi m1n1
ChefKiss Inferno
```

Those identities are part of the research contract so later updates can detect source drift.

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

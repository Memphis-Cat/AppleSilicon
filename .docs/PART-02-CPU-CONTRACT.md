# Part 02 — Apple CPU Compatibility Contract

Project version: **`2.2.0.0.0.0`**

Status: **Active — P2.01, P2.02 and P2.03 implemented**

## Purpose

Part 01 built the VMApple reference/probe and evidence pipeline. Part 02 builds the deliberate Apple CPU compatibility layer.

The goal is:

> Give the TCG VMApple path a reviewable Apple CPU contract for system registers and architectural CPU-visible features without pretending to emulate an entire M-series SoC.

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

## P2.01 — Apple CPU System Register and Feature Inventory

Status: **Implementation complete — static inventory only**

P2.01 records source-locked Apple implementation-defined register encodings, feature notes, evidence provenance and explicit unknown runtime state.

## P2.02 — Apple System Register Emulation Framework

Status: **Implementation complete — framework only**

P2.02 adds project-owned QEMU/Inferno registration plumbing through `ARMCPRegInfo` and `define_one_arm_cp_reg()` with a fail-closed undefined path on TCG `apple-gxf`.

## P2.03 — Register Read/Write/Reset Policy Model

Status: **Implementation complete — policy engine only**

P2.03 adds `AppleSysRegPolicy` with independent read, write, reset and access behavior.

Supported policy kinds include stored state, read-as-zero, write-ignore, constants, callbacks and access traps. Every semantic policy must carry evidence and intended scope; invalid state/callback combinations and duplicate encodings are rejected.

The engine maps onto QEMU's native cpreg mechanisms including `CP_ACCESS_UNDEFINED`, `CP_ACCESS_TRAP_EL1/EL2/EL3`, `ARM_CP_CONST`, `arm_cp_read_zero`, `arm_cp_write_ignore`, `arm_cp_reset_ignore`, `fieldoffset`, `resetvalue` and `define_one_arm_cp_reg_with_opaque`.

P2.03 deliberately installs **zero** live semantic Apple sysreg policies because P2.01 contains no evidence-promoted register semantics yet.

Project files:

```text
.src/.patches/0004-arm-apple-sysreg-policy-model.patch
.src/.configs/p2.03-sysreg-policy.json
.src/.tools/prepare-p2.03.sh
.docs/P2.03.md
```

## P2.04 — CPU Feature and ID-Register Compatibility

Status: **Next**

P2.04 handles architectural feature and ID-register exposure separately from Apple implementation-defined sysreg semantics.

It will define the guest-visible contract around architectural ID registers, translation granules, pointer authentication, exception levels and other CPU capabilities that VMApple/XNU observes.

## P2.05 — Deterministic CPU Contract Regression Harness

Status: **Planned**

P2.05 will provide a non-guest regression harness covering registered sysregs, encoding uniqueness, reset/access policy determinism, feature exposure and preservation of unknown behavior.

## P2.06 — Part 02 Integration Gate

Status: **Planned — final Part 02 objective**

P2.06 combines the Part 02 CPU compatibility work with the Part 01 prepared VMApple/TCG path.

After P2.06, Part 02 is closed.

## Evidence hierarchy

1. reproducible Part 01 A/B runtime evidence when final integration testing exists;
2. public XNU source;
3. QEMU source/documented ARM cpreg behavior;
4. Asahi/m1n1 source and authorized traces;
5. pinned Inferno behavior;
6. clearly labeled hypotheses.

## Physical Apple Silicon versus VMApple

```text
known on Apple hardware
!=
proven required by VMApple
!=
proven semantic behavior
```

P2.01 records encodings. P2.02 provides safe registration plumbing. P2.03 provides a policy engine. None manufactures a VMApple requirement.

## Logging and testing

- static/self-check validation is expected;
- meaningful executable tools write `.log` artifacts;
- real guest testing remains deferred until final integration;
- no proprietary Apple firmware/images/secrets are committed.

## Part 02 completion condition

Part 02 is implementation-complete when P2.01 through P2.06 are complete.

Empirical macOS success remains a separate final-integration question.

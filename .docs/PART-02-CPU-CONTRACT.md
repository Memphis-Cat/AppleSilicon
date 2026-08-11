# Part 02 — Apple CPU Compatibility Contract

Project version: **`2.3.0.0.0.0`**

Status: **Active — P2.01 through P2.04 implemented**

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

P2.02 adds project-owned QEMU/Inferno registration plumbing through `ARMCPRegInfo` with a fail-closed undefined path on TCG `apple-gxf`.

## P2.03 — Register Read/Write/Reset Policy Model

Status: **Implementation complete — policy engine only**

P2.03 adds independent read/write/reset/access policy classes, evidence/scope requirements and native QEMU cpreg mappings. The live Apple implementation-defined sysreg policy table remains empty until evidence promotes a concrete semantic contract.

## P2.04 — CPU Feature and ID-Register Compatibility

Status: **Implementation complete — architectural feature profile only**

P2.04 separates standard AArch64 feature exposure from Apple implementation-defined sysreg behavior.

The source-backed VMApple minimum for TCG `apple-gxf` covers:

```text
PAuth presence
FEAT_SSBS2
FEAT_SME / FEAT_SME2
FEAT_PAN3
4 KiB stage-1 granules
16 KiB stage-1 granules
FEAT_TLBIRANGE
```

The profile is minimum/preserve-stronger: stronger capabilities inherited from QEMU `max` are not masked merely to imitate a guessed physical Apple CPU.

P2.04 does not change the ordinary `max`, HVF/host or KVM CPU paths. It does not implement paravirtualized PAC, GICv3, CTRR or topology contracts, and it does not add Apple implementation-defined sysreg semantics.

Project files:

```text
.src/.patches/0005-arm-vmapple-feature-contract.patch
.src/.configs/p2.04-feature-contract.json
.src/.tools/prepare-p2.04.sh
.docs/P2.04.md
```

## P2.05 — Deterministic CPU Contract Regression Harness

Status: **Next**

P2.05 will build a non-guest regression suite covering both halves of the Part 02 CPU contract: P2.03 sysreg policy invariants and P2.04 architectural feature/ID-register invariants.

## P2.06 — Part 02 Integration Gate

Status: **Planned — final Part 02 objective**

P2.06 combines the Part 02 CPU compatibility work with the Part 01 prepared VMApple/TCG path. After P2.06, Part 02 is closed.

## Evidence hierarchy

1. reproducible Part 01 A/B runtime evidence when final integration testing exists;
2. public XNU source;
3. QEMU source/documented ARM behavior;
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

P2.01 records encodings, P2.02 provides registration plumbing, P2.03 provides a sysreg policy engine, and P2.04 provides an architectural minimum feature profile. None of those steps manufactures evidence for unknown implementation-defined behavior.

## Logging and testing

The project-wide rules remain active:

- no manual maintainer test is required for individual objectives;
- development-side static/build/regression validation is allowed;
- meaningful executable tools write `.log` artifacts;
- real macOS/HVF/TCG integration testing is deferred to the final integrated stage;
- no proprietary Apple firmware, images or secrets are committed.

## Part 02 completion condition

Part 02 is implementation-complete only after P2.06. Empirical guest success remains a separate final-integration result and must not be claimed before a real run demonstrates it.

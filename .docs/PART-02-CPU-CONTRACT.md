# Part 02 — Apple CPU Compatibility Contract

Project version: **`2.5.0.0.0.0`**

Status: **Closed — P2.01 through P2.06 implementation-complete**

## Purpose

Part 01 built the VMApple reference/probe and evidence pipeline. Part 02 built the deliberate Apple CPU compatibility component.

The goal was:

> Give the TCG VMApple path a reviewable Apple CPU contract for system registers and architectural CPU-visible features without pretending to emulate an entire M-series SoC.

## Fixed objective count

Part 02 contains exactly six objectives:

```text
P2.01 — Apple CPU System Register and Feature Inventory
P2.02 — Apple System Register Emulation Framework
P2.03 — Register Read/Write/Reset Policy Model
P2.04 — CPU Feature and ID-Register Compatibility
P2.05 — Deterministic CPU Contract Regression Harness
P2.06 — Part 02 Integration Gate
```

There is **no P2.07**.

## P2.01

Status: **Complete — static inventory**

P2.01 source-locks Apple implementation-defined register encodings and preserves unknown runtime relevance/semantics rather than inventing them.

## P2.02

Status: **Complete — fail-closed sysreg framework**

P2.02 adds project-owned QEMU/Inferno `ARMCPRegInfo` integration for TCG `apple-gxf` while registering no fabricated live semantics.

## P2.03

Status: **Complete — sysreg policy model**

P2.03 provides independent read/write/reset/access policies, evidence/scope requirements, duplicate-encoding rejection and native QEMU cpreg mappings.

The live implementation-defined sysreg policy table remains:

```text
0
```

## P2.04

Status: **Complete — architectural feature profile**

P2.04 adds the source-backed VMApple architectural minimum for TCG `apple-gxf`:

```text
PAuth presence
FEAT_SSBS2
FEAT_SME / FEAT_SME2
FEAT_PAN3
4 KiB stage-1 granules
16 KiB stage-1 granules
FEAT_TLBIRANGE
```

The profile preserves stronger supported features and does not contaminate ordinary `max`, host/HVF or KVM CPU paths.

## P2.05

Status: **Complete — deterministic non-guest regression**

P2.05 content-locks the Part 02 CPU contracts and patches, applies the complete source patch chain to the pinned Inferno revision, checks `max` isolation and `apple-gxf` wiring, runs negative self-checks, and emits a deterministic CPU-contract suite fingerprint.

Canonical result:

```text
.build/p2.05/cpu-contract-regression.json
```

## P2.06

Status: **Complete — Part 02 integration gate**

P2.06 binds the CPU component to the Part 01 experiment/evidence pipeline using:

```text
machine      = vmapple
accelerator  = tcg
CPU          = apple-gxf
control CPU  = max
```

It requires P2.05 to pass, creates a fresh pinned/patched integrated source tree, locks the Part 01 runtime/evidence artifacts, and emits a deterministic integration manifest:

```text
.build/p2.06/integration-manifest.json
```

The runtime wrapper `run-p2.06-probe.sh` reuses the existing P1.07 runtime harness after verifying the integration manifest and QEMU capabilities. Runtime evidence still flows through P1.09/P1.08/P1.10 rather than bypassing the existing promotion gate.

No guest execution is required to mark P2.06 implementation-complete.

## Part 02 final state

```text
P2.01 ✓
P2.02 ✓
P2.03 ✓
P2.04 ✓
P2.05 ✓
P2.06 ✓
```

Part 02 is now closed.

## Evidence hierarchy

1. reproducible Part 01 A/B runtime evidence when final integrated testing exists;
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

Part 02 deliberately preserves this distinction.

## Testing status

Development-side source/configuration validation is allowed and logged. Real macOS/HVF/TCG guest execution remains deferred to the final integrated testing stage.

Part 02 implementation completion does not claim a successful macOS boot or full Apple CPU emulation.

## Next progression point

```text
Part 03 — VMApple Platform Contract
P3.01 — Platform Contract Inventory and Ownership Map
```

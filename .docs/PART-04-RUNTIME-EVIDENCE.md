# Part 04 — Integrated Runtime Evidence and Divergence Localization

Project version: **`4.5.0.0.0.0`**

Status: **Closed at P4.06 — planned implementation complete; real runtime validation pending**

## Purpose

Parts 01 through 03 built the evidence pipeline, CPU compatibility contract and non-CPU VMApple platform contract. Part 04 adds controlled runtime provenance, capture, A/B admission, reproducible divergence promotion and the final runtime evidence gate.

Part 01 remains authoritative for manifest comparability, trace normalization and divergence promotion.

## Fixed objective count

Part 04 has exactly six objectives:

```text
P4.01 — Runtime Session Provenance and Input Lock
P4.02 — Integrated TCG Probe Capture
P4.03 — Apple Silicon HVF Reference Capture
P4.04 — Comparable A/B Session Assembly
P4.05 — Reproducible Divergence Promotion
P4.06 — Part 04 Runtime Evidence Gate
```

There is **no P4.07**.

## Runtime roles

```text
Probe      vmapple / TCG / apple-gxf
Reference  vmapple / HVF / host / Darwin arm64
```

Both runtime capture contracts use 4096 MiB RAM, 4 vCPUs, a 30-second observation window and a 3-second grace window.

## Objective status

```text
P4.01  complete
P4.02  complete
P4.03  complete
P4.04  complete
P4.05  complete
P4.06  complete
```

P4.01 locks pre-execution provenance.

P4.02 and P4.03 create provenance-bound probe/reference capture paths while reusing the established Part 01 launch/manifest machinery.

P4.04 admits only comparable A/B sessions and preserves expected HVF/host versus TCG/`apple-gxf` role differences.

P4.05 requires at least two independent admitted A/B sessions before delegating any promotion to P1.10.

P4.06 closes the implementation roadmap and provides the final evidence gate.

## P4.06 runtime outcomes

The final gate accepts two reproduced outcomes:

```text
equivalent_observations
reproducible_divergence_promoted
```

For `equivalent_observations`, at least two independent A/B sessions must each produce a runtime-origin P1.10 `no_divergence` candidate. This is scoped only to the configured trace contract and capture window and is not proof of a full macOS boot.

For `reproducible_divergence_promoted`, the independent sessions must reproduce one divergence signature and P1.09 contract fingerprint, and the exact P4.05/P1.10 promotion record must validate.

Mixed outcomes fail closed.

## Implementation closure vs runtime closure

At repository implementation completion the expected state is:

```text
P4_06_IMPLEMENTATION_COMPLETE_RUNTIME_EVIDENCE_PENDING
closed_implementation_complete_runtime_validation_pending
```

This is a valid planned-roadmap closure, not a runtime pass.

A future evidence-backed runtime pass is classified as either:

```text
P4_06_RUNTIME_EVIDENCE_PASS_EQUIVALENT_OBSERVATIONS
```

or:

```text
P4_06_RUNTIME_EVIDENCE_PASS_PROMOTED_DIVERGENCE
```

and moves Part 04 to:

```text
closed_runtime_evidence_validated
```

## Privacy and proprietary material

Real firmware, AUX/root images, machine identity, hardware-model data, UUIDs, serial numbers, account data, keys and tickets remain local. Only hashes, sizes and sanitized metadata may enter generated session/capture/A-B/evidence manifests.

## Testing state

The P4.01–P4.06 implementation is complete, but the real P4.02 TCG capture, P4.03 Apple-Silicon/HVF reference capture and resulting P4.04–P4.06 runtime evidence were not executed during implementation.

Missing reference hardware or missing runtime artifacts remain explicit pending conditions rather than fabricated passes.

## After Part 04

No Part 05 is automatically defined.

Further implementation work must be justified by real promoted runtime evidence or by an explicit new project scope. The repository root `README.md` remains intentionally unchanged.

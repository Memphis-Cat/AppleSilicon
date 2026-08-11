# Part 04 — Integrated Runtime Evidence and Divergence Localization

Project version: **`4.3.0.0.0.0`**

Status: **Active — P4.04 implemented**

## Purpose

Parts 01 through 03 built the evidence pipeline, CPU compatibility contract and non-CPU VMApple platform contract. Part 04 transitions that static/source-level integration into controlled runtime evidence.

Part 01 remains authoritative for manifest comparability, trace normalization and divergence promotion. Part 04 adds provenance and orchestration around it.

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

## P4.01 — Runtime Session Provenance and Input Lock

Status: **Implementation complete — real local session planning deferred**

P4.01 creates privacy-safe deterministic pre-execution session plans binding the P3.06 integration fingerprint, exact QEMU binary/version/capabilities, guest-input digests, hashed machine UUID and Part 01 trace/debug contract.

A P4.01 plan is provenance metadata, not runtime evidence.

## P4.02 — Integrated TCG Probe Capture

Status: **Implementation complete — real TCG execution deferred**

P4.02 verifies the probe plan before and after execution, delegates through `P3.06 → P2.06 → P1.07`, then creates a valid P1.09 probe manifest and sanitized P4.02 capture descriptor.

## P4.03 — Apple Silicon HVF Reference Capture

Status: **Implementation complete — real Apple Silicon/HVF execution deferred**

P4.03 requires a real Darwin/arm64 host, verifies the reference plan before and after execution, reuses the existing P1.09 HVF reference runner and creates a sanitized P4.03 capture descriptor. Reference unavailability fails closed.

## P4.04 — Comparable A/B Session Assembly

Status: **Implementation complete — real A/B assembly deferred**

P4.04 consumes both P4.01 plans, both runtime capture descriptors and both P1.09 manifests.

It recomputes capture fingerprints, verifies capture-to-plan and capture-to-manifest bindings, and requires the plans to agree on:

```text
P3.06 manifest SHA-256
P3.06 platform integration fingerprint
machine UUID SHA-256
guest input hashes/sizes
trace/debug contract
locked project artifacts
QEMU version string
```

The QEMU executable digest/size may differ across host builds; host, accelerator, CPU and role-specific session fingerprints are also intentional differences.

P4.04 then invokes the existing P1.09 `compare` operation. The pair must be `comparable=true` with zero contract mismatches.

The deterministic output is:

```text
.build/p4.04/ab-session.json
P4_04_AB_SESSION_READY
```

The bundle is assembled twice and must be byte-identical. It cannot compare traces or promote a divergence.

## P4.05 — Reproducible Divergence Promotion

Status: **Next**

P4.05 will take admitted P4.04 A/B pairs through the P1.08/P1.10 evidence path and require reproducibility before a divergence can become an implementation requirement.

## P4.06 — Part 04 Runtime Evidence Gate

P4.06 is the final Part 04 objective. It closes Part 04 only when the runtime evidence chain is internally consistent. Missing real reference hardware remains an explicit limitation rather than a fabricated pass.

## Privacy and proprietary-material rule

Real firmware, AUX/root images, machine identity, hardware-model data, UUIDs, serial numbers, account data, keys and tickets remain local. Only hashes, sizes and sanitized metadata may enter generated session/capture/A-B manifests.

## Testing rule

No manual maintainer test is required for individual Part 04 implementation objectives. Real P4.02/P4.03 guest execution and resulting P4.04 assembly remain deferred to final integrated testing with the required local environments.

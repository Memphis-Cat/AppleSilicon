# Part 04 — Integrated Runtime Evidence and Divergence Localization

Project version: **`4.4.0.0.0.0`**

Status: **Active — P4.05 implemented**

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

## P4.02 — Integrated TCG Probe Capture

Status: **Implementation complete — real TCG execution deferred**

P4.02 verifies probe provenance before/after execution, delegates through `P3.06 → P2.06 → P1.07`, then creates a valid P1.09 probe manifest and sanitized P4.02 capture descriptor.

## P4.03 — Apple Silicon HVF Reference Capture

Status: **Implementation complete — real Apple Silicon/HVF execution deferred**

P4.03 requires Darwin/arm64, verifies reference provenance before/after execution, reuses the existing P1.09 HVF reference runner and creates a sanitized P4.03 capture descriptor. Reference unavailability fails closed.

## P4.04 — Comparable A/B Session Assembly

Status: **Implementation complete — real A/B assembly deferred**

P4.04 consumes both P4.01 plans, both runtime capture descriptors and both P1.09 manifests. It recomputes bindings and requires equal P3.06 state, hashed machine UUID, guest inputs, trace/debug contract, locked project artifacts, QEMU version, RAM and SMP.

The deterministic local output is:

```text
.build/p4.04/ab-session.json
P4_04_AB_SESSION_READY
```

P4.04 establishes pair admissibility only; it does not compare traces or promote a divergence.

## P4.05 — Reproducible Divergence Promotion

Status: **Implementation complete — real reproduced runtime promotion deferred**

P4.05 consumes at least two independent P4.04-admitted runtime pairs. It requires different A/B fingerprints, reference/probe run IDs and capture fingerprints while keeping the complete P4.04 shared contract, role-specific QEMU binaries and machine contracts identical across reproductions.

For every reproduction P4.05 invokes the existing P1.10 `candidate` path, which itself reuses P1.09 and P1.08. Every candidate must be runtime-origin, promotion-eligible and contain a real divergence.

All candidates must reproduce the same:

```text
divergence_signature
contract_fingerprint
```

P4.05 then invokes the existing P1.10 `promote` command. The authoritative record must be:

```text
P01-DIVERGENCE-0001
status = promoted
auto_committed = false
```

The P4.05 wrapper runs the complete evaluation twice and requires byte-identical sanitized P4.05 records before publishing local evidence under `.build/p4.05/`.

A promoted divergence is evidence; it is not automatically a hardware implementation or authorization to guess Apple semantics.

## P4.06 — Part 04 Runtime Evidence Gate

Status: **Next / final Part 04 objective**

P4.06 will close Part 04 by evaluating the complete runtime-evidence state. It must distinguish implementation readiness, missing real runtime evidence, no observed divergence, and a reproducibly promoted divergence without fabricating success when Apple-Silicon reference hardware is unavailable.

## Privacy and proprietary-material rule

Real firmware, AUX/root images, machine identity, hardware-model data, UUIDs, serial numbers, account data, keys and tickets remain local. Only hashes, sizes and sanitized metadata may enter generated session/capture/A-B/promotion descriptors.

## Testing rule

No manual maintainer test is required for individual Part 04 implementation objectives. Real P4.02/P4.03 guest execution, P4.04 pair assembly and P4.05 promotion remain deferred to final integrated testing with the required local environments.

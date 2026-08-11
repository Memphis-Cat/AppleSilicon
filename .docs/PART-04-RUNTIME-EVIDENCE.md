# Part 04 — Integrated Runtime Evidence and Divergence Localization

Project version: **`4.2.0.0.0.0`**

Status: **Active — P4.03 implemented**

## Purpose

Parts 01 through 03 built the evidence pipeline, CPU compatibility contract and non-CPU VMApple platform contract. Part 04 is the transition from static/source-level integration into controlled runtime evidence.

Part 04 does not replace the Part 01 evidence rules. It operationalizes them around the completed P3.06 integrated machine contract.

A runtime result is useful only if we know exactly which QEMU binary, integrated project state, guest inputs, machine UUID, role, accelerator, CPU model and trace contract produced it.

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

### Probe

```text
machine      vmapple
accelerator  tcg
cpu          apple-gxf
```

### Reference

```text
machine      vmapple
accelerator  hvf
cpu          host
host         Darwin arm64
```

The primary reference remains an Apple-Silicon macOS host using VMApple/HVF. This keeps the device model aligned while changing the CPU/accelerator path.

## P4.01 — Runtime Session Provenance and Input Lock

Status: **Implementation complete — real local session planning deferred**

P4.01 creates a deterministic privacy-safe session plan before either runtime role may execute. It binds the passing P3.06 fingerprint, exact QEMU binary digest/version/capabilities, firmware/AUX/root/identity digests, optional hardware-model digest, canonical machine-UUID digest and Part 01 trace/debug contract.

A P4.01 plan is provenance metadata, not runtime evidence.

Project files:

```text
.docs/P4.01.md
.src/.configs/p4.01-runtime-session-policy.json
.src/.tools/runtime-session.py
.src/.tools/prepare-p4.01.sh
.src/.tools/plan-p4.01-session.sh
```

## P4.02 — Integrated TCG Probe Capture

Status: **Implementation complete — real TCG execution deferred**

P4.02 consumes a P4.01 `probe` plan and locks:

```text
vmapple / TCG / apple-gxf
RAM      4G / 4096 MiB
SMP      4
window   30 seconds
grace    3 seconds
```

It verifies provenance before and after execution, delegates only through `P3.06 → P2.06 → P1.07`, then uses the existing Part 01 collector to create a valid P1.09 probe manifest and a sanitized P4.02 capture descriptor.

P4.02 cannot promote a divergence.

Project files:

```text
.docs/P4.02.md
.src/.configs/p4.02-probe-capture-policy.json
.src/.tools/probe-capture.py
.src/.tools/prepare-p4.02.sh
.src/.tools/run-p4.02-probe.sh
```

## P4.03 — Apple Silicon HVF Reference Capture

Status: **Implementation complete — real Apple Silicon/HVF execution deferred**

P4.03 applies the same provenance discipline to the primary reference role:

```text
vmapple / HVF / host
host     Darwin arm64
RAM      4G / 4096 MiB
SMP      4
window   30 seconds
grace    3 seconds
```

The host requirement is fail-closed. An Intel Mac/Hackintosh, Linux ARM host, TCG substitute, or synthetic manifest cannot become a primary reference.

P4.03 reuses `.src/.tools/run-p1.09-reference.sh`; it does not create another HVF QEMU launcher or another reference-manifest schema.

Before execution it requires a valid P4.01 `reference` plan, the exact P3.06 fingerprint, exact planned QEMU digest/version plus `vmapple`/`hvf`/`host` capabilities, exact guest-input digests and the canonical UUID digest.

After a completed `P1_09_REFERENCE_*` observation, the generated P1.09 reference manifest must validate under the existing Part 01 policy and must record the locked 4096 MiB / 4-vCPU contract.

The current P1.09 reference manifest does not include its launcher log as a manifest artifact. P4.03 preserves that closed format and hashes the launcher log separately in the P4.03 capture descriptor.

The full provenance preflight runs again after execution and must be byte-identical to the pre-run result.

A `P4_03_REFERENCE_CAPTURE_READY` result is reference provenance, not a boot-success claim or divergence promotion.

Project files:

```text
.docs/P4.03.md
.src/.configs/p4.03-reference-capture-policy.json
.src/.tools/reference-capture.py
.src/.tools/prepare-p4.03.sh
.src/.tools/run-p4.03-reference.sh
```

## P4.04 — Comparable A/B Session Assembly

Status: **Next**

P4.04 will combine P4.02 and P4.03 captures, invoke the P1.09 equality contract, and reject mixed guest assets, RAM/SMP drift, trace-contract drift or otherwise incomparable sessions before any trace divergence is considered.

## P4.05 — Reproducible Divergence Promotion

P4.05 will feed comparable real traces through P1.08/P1.10 and promote a divergence only when the existing reproducibility requirements are met.

## P4.06 — Part 04 Runtime Evidence Gate

P4.06 is the final Part 04 objective. It closes Part 04 only when the runtime evidence chain is internally consistent. If real reference hardware is unavailable, the gate must report that limitation rather than fabricate a successful reference run.

## Evidence authority

Part 01 remains authoritative for:

```text
trace normalization
reference/probe manifest comparability
divergence candidate generation
divergence promotion
```

Part 04 adds provenance and orchestration around those mechanisms; it does not weaken them.

## Privacy and proprietary-material rule

Real firmware, AUX/root images, machine identity, hardware-model data, UUIDs, serial numbers, account data, keys and tickets remain local. Only hashes, sizes and sanitized metadata may enter generated session/capture manifests.

## Testing rule

No manual maintainer test is required for individual Part 04 implementation objectives. Real P4.02/P4.03 guest execution remains deferred to the final integrated testing phase with the required local environments.

# Part 04 — Integrated Runtime Evidence and Divergence Localization

Project version: **`4.1.0.0.0.0`**

Status: **Active — P4.02 implemented**

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

The probe role is the portable compatibility-layer path and may run on a non-Apple-Silicon host when a suitable `qemu-system-aarch64` binary is available.

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

P4.01 creates the pre-execution provenance contract. Before either role may run, a sanitized deterministic session plan must bind:

- the passing P3.06 platform integration fingerprint;
- the exact QEMU executable SHA-256 and byte size;
- QEMU version output;
- role-specific `vmapple`, accelerator and CPU capability checks;
- firmware SHA-256/bytes;
- AUX SHA-256/bytes;
- root disk SHA-256/bytes;
- machine-identity SHA-256/bytes;
- optional hardware-model SHA-256/bytes;
- SHA-256 of the normalized machine UUID without storing the UUID itself;
- the Part 01 MMIO trace/debug contract.

The session plan stores no raw local paths, hostname, UUID, identity content, hardware-model content, firmware or disk content.

A P4.01 plan is **not runtime evidence**. It is an admissibility/provenance record for a later run.

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

P4.02 consumes a P4.01 `probe` session plan and adds a runtime execution lock:

```text
RAM              4G / 4096 MiB
SMP              4
capture window   30 seconds
grace window     3 seconds
```

The RAM/SMP lock is important because those fields participate in P1.09 reference/probe comparability.

Before execution, P4.02 repeats the P4.01 provenance checks against the live QEMU binary, P3.06 manifest, machine UUID digest and all guest-input digests.

It then delegates only through:

```text
P3.06
  ↓
P2.06
  ↓
P1.07
```

so there is still one authoritative TCG QEMU launch implementation.

After a completed P1.07 observation, P4.02 immediately uses `collect-p1.10-probe.sh` to produce a P1.09-compatible sanitized probe manifest. The manifest must validate under the existing P1.09 policy.

P4.02 then repeats the provenance preflight and requires the pre-run and post-run canonical results to be byte-identical.

The final local capture descriptor binds the P4.01 session fingerprint, P3.06 platform fingerprint, validated P1.09 probe manifest and runtime artifact digests without storing raw guest paths or contents.

A completed P4.02 capture is runtime evidence provenance, but **not** a divergence promotion. P1.10 remains the only promotion authority.

Project files:

```text
.docs/P4.02.md
.src/.configs/p4.02-probe-capture-policy.json
.src/.tools/probe-capture.py
.src/.tools/prepare-p4.02.sh
.src/.tools/run-p4.02-probe.sh
```

## P4.03 — Apple Silicon HVF Reference Capture

Status: **Next**

P4.03 will apply the same provenance discipline to the Apple-Silicon/HVF/`host` reference role. It will reuse the Part 01 reference runner and P1.09 evidence format rather than creating an independent reference format.

## P4.04 — Comparable A/B Session Assembly

P4.04 will require probe/reference session-plan and runtime-evidence equality on every field that is supposed to match and will reject mixed assets or changed binaries.

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

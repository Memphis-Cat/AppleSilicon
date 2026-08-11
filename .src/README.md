# Source

Project version: **`4.0.0.0.0.0`**

The source tree contains closed Part 01 evidence, closed Part 02 CPU compatibility, closed Part 03 VMApple platform integration, and active Part 04 runtime-evidence work beginning at P4.01.

## Layout

```text
.src/
├── .upstream/.inferno/  # pinned Inferno submodule
├── .patches/            # ordered compatibility patches
├── .tools/              # logged preparation/regression/evidence tools
├── .configs/            # non-secret machine-readable contracts/configs
└── .fixtures/           # sanitized deterministic fixtures
```

## Closed implementation layers

Part 01 is closed at P1.10 and remains authoritative for runtime manifests, trace comparison and divergence promotion.

Part 02 is closed at P2.06 and owns the `apple-gxf` CPU compatibility contract.

Part 03 is closed at P3.06 and owns the integrated non-CPU VMApple platform contract.

## Compatibility patch chain

The ordered source patch chain remains exactly:

```text
0001-vmapple-decouple-build-from-hvf.patch
0002-vmapple-optional-apple-pvg.patch
0003-arm-apple-sysreg-framework.patch
0004-arm-apple-sysreg-policy-model.patch
0005-arm-vmapple-feature-contract.patch
```

P4.01 adds no `0006` patch.

## Part 04 — Runtime evidence

Part 04 is fixed at exactly P4.01 through P4.06.

Current state:

```text
P4.01  Runtime Session Provenance and Input Lock  complete
P4.02  Integrated TCG Probe Capture               NEXT
P4.03  Apple Silicon HVF Reference Capture
P4.04  Comparable A/B Session Assembly
P4.05  Reproducible Divergence Promotion
P4.06  Part 04 Runtime Evidence Gate
```

There is no P4.07.

P4.01 introduces a deterministic pre-execution session plan that binds:

```text
P3.06 platform integration fingerprint
QEMU executable SHA-256/version/capabilities
role: probe or reference
firmware/AUX/root/machine-identity digests
optional hardware-model digest
canonical machine-UUID digest
Part 01 trace/debug contract
```

The plan stores no raw UUID, hostname, local paths, identity data or guest artifact contents. It is provenance metadata only and cannot be promoted to runtime evidence.

## Testing and artifacts

`prepare-p4.01.sh` performs logged static validation without a guest.

`plan-p4.01-session.sh` performs logged local pre-execution planning and determinism checks when real QEMU/VM inputs are available, but still does not launch QEMU.

No proprietary Apple firmware, macOS images, AUX/root storage artifacts, tickets, keys, authentic hardware secrets, machine-identity blobs or account secrets belong in `.src/`.

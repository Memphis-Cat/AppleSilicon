# Source

Project version: **`4.3.0.0.0.0`**

The source tree contains closed Part 01 evidence, closed Part 02 CPU compatibility, closed Part 03 VMApple platform integration, and active Part 04 runtime-evidence work through P4.04.

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

P4.01 through P4.04 add no `0006` patch.

## Part 04 — Runtime evidence

Part 04 is fixed at exactly P4.01 through P4.06.

Current state:

```text
P4.01  Runtime Session Provenance and Input Lock  complete
P4.02  Integrated TCG Probe Capture               complete
P4.03  Apple Silicon HVF Reference Capture        complete
P4.04  Comparable A/B Session Assembly            complete
P4.05  Reproducible Divergence Promotion          NEXT
P4.06  Part 04 Runtime Evidence Gate
```

There is no P4.07.

P4.02 defines the provenance-bound `vmapple / TCG / apple-gxf` probe capture; P4.03 defines the fail-closed `vmapple / HVF / host / Darwin arm64` primary reference capture.

P4.04 admits a pair only when its P4.01 plans, P4.02/P4.03 capture descriptors and P1.09 manifests agree on the full comparison contract. It additionally binds the same machine-UUID digest, P3.06 state and QEMU version string while allowing host-specific executable hashes to differ.

The final P4.04 artifact is a deterministic local `.build/p4.04/ab-session.json`. It is pair-admission metadata, not a trace divergence or promotion.

## Testing and artifacts

`prepare-p4.01.sh` through `prepare-p4.04.sh` perform logged static validation without requiring a guest for implementation completion.

The P4.02/P4.03 runtime wrappers and P4.04 A/B assembler are implemented, but real guest execution/pair assembly remains intentionally deferred to final integrated testing with the required local environments.

No proprietary Apple firmware, macOS images, AUX/root storage artifacts, tickets, keys, authentic hardware secrets, machine-identity blobs or account secrets belong in `.src/`.

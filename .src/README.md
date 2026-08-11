# Source

Project version: **`4.4.0.0.0.0`**

The source tree contains closed Part 01 evidence, closed Part 02 CPU compatibility, closed Part 03 VMApple platform integration, and active Part 04 runtime-evidence work through P4.05.

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

P4.01 through P4.05 add no `0006` patch.

## Part 04 — Runtime evidence

Part 04 is fixed at exactly P4.01 through P4.06.

Current state:

```text
P4.01  Runtime Session Provenance and Input Lock  complete
P4.02  Integrated TCG Probe Capture               complete
P4.03  Apple Silicon HVF Reference Capture        complete
P4.04  Comparable A/B Session Assembly            complete
P4.05  Reproducible Divergence Promotion          complete
P4.06  Part 04 Runtime Evidence Gate              NEXT / final
```

There is no P4.07.

P4.02 and P4.03 define provenance-bound probe/reference captures. P4.04 admits one pair only after full comparison-contract validation.

P4.05 requires at least two independent P4.04 sessions, keeps their shared contract and exact role-specific QEMU builds fixed, generates candidates through P1.10/P1.08, requires one repeated divergence signature and P1.09 contract fingerprint, and delegates the authoritative promotion to P1.10.

The P4.05 local output is `.build/p4.05/promotion.json` plus local P1.10 candidate/promotion evidence. Nothing is auto-committed and no new hardware behavior is inferred merely because a trace divergence is promoted.

## Testing and artifacts

`prepare-p4.01.sh` through `prepare-p4.05.sh` perform logged static validation without requiring a guest for implementation completion.

The runtime capture, A/B assembly and reproduced promotion paths are implemented, but real P4.02/P4.03 executions and therefore real P4.04/P4.05 runtime evidence remain intentionally deferred to final integrated testing with the required local environments.

No proprietary Apple firmware, macOS images, AUX/root storage artifacts, tickets, keys, authentic hardware secrets, machine-identity blobs or account secrets belong in `.src/`.

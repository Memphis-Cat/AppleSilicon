# Source

Project version: **`4.5.0.0.0.0`**

The source tree contains closed Part 01 evidence, closed Part 02 CPU compatibility, closed Part 03 VMApple platform integration, and the completed Part 04 runtime-evidence implementation through P4.06.

## Layout

```text
.src/
├── .upstream/.inferno/  # pinned Inferno submodule
├── .patches/            # ordered compatibility patches
├── .tools/              # logged preparation/regression/evidence tools
├── .configs/            # non-secret machine-readable contracts/configs
└── .fixtures/           # sanitized deterministic fixtures
```

## Compatibility patch chain

The ordered source patch chain remains exactly:

```text
0001-vmapple-decouple-build-from-hvf.patch
0002-vmapple-optional-apple-pvg.patch
0003-arm-apple-sysreg-framework.patch
0004-arm-apple-sysreg-policy-model.patch
0005-arm-vmapple-feature-contract.patch
```

Part 04 adds no `0006` patch.

## Part 04 — Runtime evidence

Part 04 is fixed at exactly P4.01 through P4.06 and is implementation-complete:

```text
P4.01  Runtime Session Provenance and Input Lock  complete
P4.02  Integrated TCG Probe Capture               complete
P4.03  Apple Silicon HVF Reference Capture        complete
P4.04  Comparable A/B Session Assembly            complete
P4.05  Reproducible Divergence Promotion          complete
P4.06  Part 04 Runtime Evidence Gate              complete
```

There is no P4.07.

P4.06 emits a deterministic implementation state that intentionally reports runtime evidence as pending until real P4.02/P4.03 captures exist.

The final runtime evaluator requires at least two independent P4.04 sessions and accepts either reproduced trace equivalence or a reproducible divergence promoted by the existing P1.10 authority.

## Current closure state

```text
planned implementation roadmap  complete
runtime evidence validation      pending
```

This is not a claim of full macOS boot success, `apple-gxf` runtime sufficiency or modern macOS compatibility.

No Part 05 is automatically defined. Further implementation work must be justified by runtime evidence or an explicit new scope.

## Testing and artifacts

`prepare-p4.01.sh` through `prepare-p4.06.sh` provide logged static/deterministic implementation checks.

Real guest execution remains local and evidence-gated. No proprietary Apple firmware, macOS images, AUX/root storage artifacts, tickets, keys, authentic hardware secrets, machine-identity blobs or account secrets belong in `.src/`.

# Source

Project version: **`4.6.0.0.0.0`**

The source tree contains closed Part 01 evidence, closed Part 02 CPU compatibility, closed Part 03 VMApple platform integration, completed Part 04 runtime-evidence implementation through P4.06, and the final post-roadmap stability hardening layer.

## Layout

```text
.src/
├── .upstream/.inferno/  # pinned Inferno submodule
├── .patches/            # ordered compatibility patches
├── .tools/              # logged preparation/regression/evidence/audit tools
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

There is no `0006` patch.

The final source audit did not establish evidence for another Apple CPU/sysreg/device/storage behavior, so no speculative emulator patch was added.

## Part 04 — Runtime evidence

Part 04 is fixed at exactly P4.01 through P4.06 and remains implementation-complete:

```text
P4.01  Runtime Session Provenance and Input Lock  complete
P4.02  Integrated TCG Probe Capture               complete
P4.03  Apple Silicon HVF Reference Capture        complete
P4.04  Comparable A/B Session Assembly            complete
P4.05  Reproducible Divergence Promotion          complete
P4.06  Part 04 Runtime Evidence Gate              complete
```

There is no P4.07.

## Final stability hardening

Version `4.6.0.0.0.0` is not another Part/objective. It hardens the finished implementation before real integrated testing.

Key changes include:

- correct VMApple `uint64_t` machine-ID semantics instead of RFC UUID semantics;
- compiled P3.02 identity validation and real application to QEMU;
- P2/P3/P4 generated-fingerprint recomputation;
- runtime-origin probe run IDs;
- QEMU signal cleanup;
- P4 plan/preflight/capture authentication;
- P1.10 rejection of empty/unstructured runtime trace evidence;
- positive-integer Inferno build parallelism;
- a whole-repository final static audit that locks the actual runtime wrappers.

Final hardening files:

```text
.configs/final-stability-policy.json
.tools/runtime_integrity.py
.tools/final-stability-audit.py
.tools/prepare-final-stability.sh
```

## Current closure state

```text
planned implementation roadmap  complete
final stability hardening        implemented
runtime evidence validation      pending
```

This is not a claim of full macOS boot success, `apple-gxf` runtime sufficiency or modern macOS compatibility.

No Part 05 is automatically defined. Further implementation work must be justified by runtime evidence or an explicit new scope.

## Testing and artifacts

`prepare-final-stability.sh` is the final logged static/source/repository audit and executes no guest.

Real guest execution remains local and evidence-gated through P4.01–P4.06. No proprietary Apple firmware, macOS images, AUX/root storage artifacts, tickets, keys, authentic hardware secrets, machine-identity blobs or account secrets belong in `.src/`.

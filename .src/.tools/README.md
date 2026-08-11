# Research, Trace, CPU, Platform and Runtime Evidence Tools

Tools in this directory support reproducible compatibility research rather than guest patching.

## Closed implementation layers

Part 01 is closed at P1.10 and remains authoritative for runtime manifests, trace comparison and divergence promotion.

Part 02 is closed at P2.06 and owns the `apple-gxf` CPU compatibility contract.

Part 03 is closed at P3.06 and owns the integrated non-CPU VMApple platform contract.

Part 04 implementation is closed at P4.06.

## Part 04 tools

```text
runtime-session.py
prepare-p4.01.sh
plan-p4.01-session.sh

probe-capture.py
prepare-p4.02.sh
run-p4.02-probe.sh

reference-capture.py
prepare-p4.03.sh
run-p4.03-reference.sh

ab-session.py
prepare-p4.04.sh
assemble-p4.04.sh

divergence-promotion.py
prepare-p4.05.sh
promote-p4.05.sh

runtime-evidence-gate.py
prepare-p4.06.sh
evaluate-p4.06.sh
```

P4.01–P4.05 provide provenance, capture, A/B admission and reproduced-promotion layers.

P4.06 validates all five prior Part 04 policies/tools, verifies the five-patch repository state, emits a deterministic implementation-close record, and provides the final deterministic runtime evaluator.

The implementation-only P4.06 state is:

```text
P4_06_IMPLEMENTATION_COMPLETE_RUNTIME_EVIDENCE_PENDING
```

The runtime evaluator requires at least two independent admitted sessions. It accepts either `P4_06_RUNTIME_EVIDENCE_PASS_EQUIVALENT_OBSERVATIONS` or `P4_06_RUNTIME_EVIDENCE_PASS_PROMOTED_DIVERGENCE`.

Default generated state remains local under `.build/` and `.logs/`.

## Rules

Preparation tools keep the pinned Inferno submodule pristine and use project-owned `.build/` and `.logs/` state. Secret or proprietary Apple artifacts must not be committed.

No Part 05 is automatically created. Future implementation must follow real runtime evidence or an explicit scope change.

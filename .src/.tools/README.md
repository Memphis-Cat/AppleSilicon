# Research, Trace, CPU, Platform and Runtime Evidence Tools

Tools in this directory support reproducible compatibility research rather than guest patching.

## Closed implementation layers

Part 01 is closed at P1.10 and remains authoritative for runtime manifests, trace comparison and divergence promotion.

Part 02 is closed at P2.06 and owns the `apple-gxf` CPU compatibility contract.

Part 03 is closed at P3.06 and owns the integrated non-CPU VMApple platform contract.

Part 04 implementation is closed at P4.06.

## Runtime/evidence tools

```text
runtime_integrity.py

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

`runtime_integrity.py` centralizes the hardened VMApple uint64 machine-ID, compiled P3.02 identity and generated-fingerprint checks used by the runtime layers.

P4.01–P4.05 provide provenance, capture, A/B admission and reproduced-promotion layers.

P4.06 is the final runtime evidence gate.

## Final stability tools

```text
final-stability-audit.py
prepare-final-stability.sh
```

These belong to release `4.6.0.0.0.0` and do not create another Part/objective.

The final auditor scans every project-owned JSON configuration and every Python/shell tool, verifies executable Git modes, checks the frozen root README and Inferno gitlink, verifies the exact five-patch chain, locks the actual runtime shell wrappers, executes static P1.10/P3/P4 validators and negative self-checks, and verifies the hardened runtime-source invariants.

`prepare-final-stability.sh` runs the whole audit twice and requires byte-identical output.

Expected classification when that repository-owned static harness passes:

```text
FINAL_STABILITY_AUDIT_PASS
```

with runtime validation still explicitly pending.

Default generated state remains local under `.build/` and `.logs/`.

## Rules

Preparation tools keep the pinned Inferno submodule pristine and use project-owned `.build/` and `.logs/` state. Secret or proprietary Apple artifacts must not be committed.

No Part 05 is automatically created. The next action after final hardening is real integrated runtime testing; future implementation must follow real evidence or an explicit scope change.

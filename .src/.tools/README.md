# Research, Trace, CPU, Platform and Runtime Evidence Tools

Tools in this directory support reproducible compatibility research rather than guest patching.

## Part 01

Part 01 tools provide build/probe, trace normalization, reference-manifest and A/B evidence workflows. Part 01 is closed at P1.10 and remains authoritative for runtime evidence/promotion.

## Part 02

Part 02 tools implement and validate the source-locked CPU compatibility contract through the P2.06 integration gate. Part 02 is closed at P2.06.

## Part 03

Part 03 tools validate the VMApple platform contracts and close them through P3.06. Part 03 is closed at P3.06.

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
```

### P4.01–P4.03

Create privacy-safe pre-execution plans and provenance-bound TCG probe / Apple-Silicon HVF reference captures while reusing the Part 01 runtime/manifest paths.

### P4.04

`ab-session.py` validates both P4.01 plans, capture fingerprints, exact P1.09 manifest bindings and the authoritative P1.09 comparability result. `assemble-p4.04.sh` runs the assembly twice and publishes `.build/p4.04/ab-session.json` only when deterministic.

### P4.05

`divergence-promotion.py` consumes at least two independent P4.04 sessions, verifies reproduction independence/equality rules, delegates each candidate to `evidence-bundle.py candidate`, requires one reproduced divergence signature/contract fingerprint, then delegates final promotion to `evidence-bundle.py promote`.

`promote-p4.05.sh` evaluates the complete promotion chain twice and requires byte-identical sanitized P4.05 records before publishing `.build/p4.05/promotion.json` and the local P1.10 candidate/promotion evidence.

P4.05 launches no guest and never auto-commits a promotion.

Default generated state remains local under `.build/p4.01/` through `.build/p4.05/` and `.logs/`.

## Rules

Preparation tools keep the pinned Inferno submodule pristine and use project-owned `.build/` and `.logs/` state. Secret or proprietary Apple artifacts must not be committed.

P1.08/P1.10 remain authoritative for trace comparison and divergence promotion; Part 04 adds provenance, admission and reproducibility orchestration around them.

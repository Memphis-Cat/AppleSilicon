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
```

### P4.01

Creates deterministic privacy-safe pre-execution session plans for probe/reference roles without launching guests.

### P4.02

Validates live TCG/`apple-gxf` probe provenance before/after execution and finalizes a sanitized P4.02 capture while reusing the Part 01 runtime/manifest path.

### P4.03

Validates real Darwin/arm64 + HVF + `host` reference provenance, reuses the existing P1.09 reference runner and finalizes a sanitized P4.03 capture.

### P4.04

`ab-session.py` validates both P4.01 plans, recomputes both capture fingerprints, verifies exact capture-to-P1.09-manifest bindings and invokes the authoritative P1.09 `compare` operation.

`assemble-p4.04.sh` runs the assembly twice and requires byte-identical output before publishing `.build/p4.04/ab-session.json`.

P4.04 requires equal P3.06 state, machine-UUID digest, guest inputs, trace/debug contract, locked project artifacts and QEMU version while preserving intentional host/HVF-vs-TCG/CPU/binary-build differences.

Default generated state remains local under `.build/p4.01/` through `.build/p4.04/` and `.logs/`.

## Rules

Preparation tools keep the pinned Inferno submodule pristine and use project-owned `.build/` and `.logs/` state. Secret or proprietary Apple artifacts must not be committed.

P4.02/P4.03 capture metadata and P4.04 pair-admission metadata cannot promote divergences. P1.08/P1.10 remain authoritative.

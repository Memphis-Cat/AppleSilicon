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
```

### P4.01

`runtime-session.py` validates the P4.01 policy and creates privacy-safe deterministic pre-execution runtime session plans.

`prepare-p4.01.sh` performs logged static preparation without a guest.

`plan-p4.01-session.sh` hashes the selected QEMU executable and local VM inputs twice and requires deterministic session plans. It does not launch QEMU.

### P4.02

`probe-capture.py` validates the P4.02 policy, performs live pre/post provenance checks and finalizes a sanitized capture descriptor around a validated P1.09 probe manifest.

`prepare-p4.02.sh` performs logged static P4.02 validation without launching a guest.

`run-p4.02-probe.sh` is the integrated runtime wrapper. It fixes the probe to `vmapple` / TCG / `apple-gxf` / 4G / 4 vCPUs / 30 seconds, delegates through P3.06 → P2.06 → P1.07, packages the completed observation through `collect-p1.10-probe.sh`, validates the resulting P1.09 manifest, repeats provenance checks, and emits a P4.02 capture descriptor.

P4.02 does not compare A/B traces and cannot promote a divergence.

Default local outputs include:

```text
.build/p4.01/probe-runtime-session-plan.json
.build/p4.02/<run>/probe-manifest.json
.build/p4.02/<run>/probe-capture.json
```

Logs remain under `.logs/`.

## Rules

Preparation tools keep the pinned Inferno submodule pristine and use project-owned `.build/` and `.logs/` state. Secret or proprietary Apple artifacts must not be committed. Part 04 remains fixed at P4.01–P4.06; P4.03 is next.

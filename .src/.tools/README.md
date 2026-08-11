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
```

### P4.01

`runtime-session.py` and the P4.01 shell tools create deterministic privacy-safe pre-execution session plans for the probe and reference roles. They do not launch guests.

### P4.02

`probe-capture.py` validates live probe provenance before/after execution and finalizes the sanitized probe capture. `run-p4.02-probe.sh` reuses the P3.06 → P2.06 → P1.07 path and the existing P1.09-compatible collector.

The TCG probe contract is `vmapple / tcg / apple-gxf / 4G / 4 vCPUs / 30 seconds`.

### P4.03

`reference-capture.py` validates the real Apple Silicon reference provenance and finalizes the sanitized reference capture. `run-p4.03-reference.sh` requires Darwin/arm64 and delegates the actual reference run to the existing P1.09 HVF runner.

The reference contract is `vmapple / hvf / host / Darwin arm64 / 4G / 4 vCPUs / 30 seconds`.

The P1.09 reference manifest remains authoritative. P4.03 hashes the launcher log separately instead of modifying the closed P1.09 format.

Default generated state remains local under `.build/p4.01/`, `.build/p4.02/`, `.build/p4.03/` and `.logs/`.

## Rules

Preparation tools keep the pinned Inferno submodule pristine and use project-owned `.build/` and `.logs/` state. Secret or proprietary Apple artifacts must not be committed.

P4.02/P4.03 capture metadata cannot promote divergences. P1.10 remains the promotion authority.

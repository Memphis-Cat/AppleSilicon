# Experiment Configurations

This directory contains reproducible, non-secret example configurations, policies and machine-readable compatibility contracts for AppleSilicon.

## Closed contracts

Part 02 CPU contracts are closed at P2.06.
Part 03 platform contracts are closed at P3.06.
Part 04 implementation contracts are closed at P4.06.

## Part 04 runtime-evidence contracts

```text
p4.01-runtime-session-policy.json
p4.02-probe-capture-policy.json
p4.03-reference-capture-policy.json
p4.04-ab-session-policy.json
p4.05-divergence-promotion-policy.json
p4.06-runtime-evidence-gate-policy.json
```

P4.01 locks privacy-safe pre-execution provenance.

P4.02/P4.03 define the TCG/`apple-gxf` probe and Darwin/arm64 + HVF + `host` reference capture contracts.

P4.04 defines A/B admission and comparability.

P4.05 requires at least two independent admitted sessions before delegating any divergence promotion to P1.10.

P4.06 is the final gate. It distinguishes `planned_implementation_complete` from real runtime validation and accepts only two evidence-backed runtime outcomes: reproduced trace equivalence within the configured capture scope, or a reproducible divergence backed by P4.05/P1.10 promotion.

There is no P4.07 and no automatically defined Part 05.

## Secret/proprietary material rule

Configuration files may describe local inputs using placeholders or policy names, but must not contain Apple proprietary firmware, macOS disk images, real serial numbers, machine secrets, signing tickets, private keys, authentic hardware keys or device-specific credentials.

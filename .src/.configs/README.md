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

P4.01 locks privacy-safe pre-execution provenance. Its legacy `machine_uuid` field now explicitly means the pinned VMApple unsigned 64-bit machine ID/SDOM/ECID source, not an RFC UUID.

P4.02/P4.03 define the TCG/`apple-gxf` probe and Darwin/arm64 + HVF + `host` reference capture contracts.

P4.04 defines A/B admission and comparability.

P4.05 requires at least two independent admitted sessions before delegating any divergence promotion to P1.10.

P4.06 is the final runtime evidence gate.

## Final stability contract

```text
final-stability-policy.json
```

This is a post-roadmap `4.6.0.0.0.0` hardening policy rather than a new Part/objective. It locks the actual runtime shell wrappers as well as the validator/policy layers and requires a whole-repository static scan.

The policy preserves:

- exact Inferno gitlink revision;
- exact root README blob;
- exact five-patch chain, with no `0006`;
- uint64 VMApple machine-ID semantics;
- compiled P3.02 identity application;
- generated fingerprint recomputation;
- runtime-origin run IDs;
- QEMU signal cleanup;
- non-empty structured trace evidence;
- runtime validation still pending.

There is no P4.07 and no automatically defined Part 05.

## Secret/proprietary material rule

Configuration files may describe local inputs using placeholders or policy names, but must not contain Apple proprietary firmware, macOS disk images, real serial numbers, machine secrets, signing tickets, private keys, authentic hardware keys or device-specific credentials.

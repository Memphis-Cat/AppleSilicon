# Experiment Configurations

This directory contains reproducible, non-secret example configurations, policies and machine-readable compatibility contracts for AppleSilicon.

## Closed contracts

Part 02 CPU contracts are closed at P2.06.

Part 03 platform contracts are closed at P3.06.

## Part 04 runtime-evidence contracts

```text
p4.01-runtime-session-policy.json
p4.02-probe-capture-policy.json
p4.03-reference-capture-policy.json
p4.04-ab-session-policy.json
```

### P4.01

Defines deterministic pre-execution provenance for both runtime roles:

```text
probe      vmapple / TCG / apple-gxf
reference  vmapple / HVF / host / Darwin arm64
```

### P4.02 / P4.03

Define provenance-bound runtime capture contracts using 4G RAM, 4 vCPUs, a 30-second observation and 3-second grace period. P4.03 additionally fails closed without Darwin/arm64 + HVF + `host`.

### P4.04

Defines the A/B admission contract. It requires the P4.01 plans, P4.02/P4.03 captures and authoritative P1.09 manifests to agree on shared P3.06 state, hashed machine UUID, guest inputs, trace/debug configuration, RAM/SMP and QEMU version. Host-specific QEMU executable digests may differ.

A P4.04 bundle is pair-admission metadata only; P1.08/P1.10 remain authoritative for trace comparison and promotion.

P4.05 is next. Part 04 remains fixed at P4.01 through P4.06; there is no P4.07.

## Secret/proprietary material rule

Configuration files may describe local inputs using placeholders or policy names, but must not contain Apple proprietary firmware, macOS disk images, real serial numbers, machine secrets, signing tickets, private keys, authentic hardware keys or device-specific credentials.

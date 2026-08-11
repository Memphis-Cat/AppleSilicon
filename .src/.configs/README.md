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
```

### P4.01

Defines deterministic pre-execution provenance for both runtime roles:

```text
probe      vmapple / TCG / apple-gxf
reference  vmapple / HVF / host / Darwin arm64
```

### P4.02

Defines the integrated TCG probe capture and locks:

```text
RAM      4G / 4096 MiB
SMP      4
window   30 seconds
grace    3 seconds
```

It binds the resulting P1.09-compatible probe manifest to the P4.01 provenance fingerprint without promoting a divergence.

### P4.03

Defines the Apple Silicon reference capture using the same comparison-sensitive RAM/SMP/window contract as P4.02, with mandatory:

```text
host         Darwin arm64
accelerator  HVF
CPU          host
```

The reference path must fail closed when Apple Silicon/HVF is unavailable. It reuses the P1.09 reference manifest rather than defining a replacement evidence format.

P4.04 is next. Part 04 remains fixed at P4.01 through P4.06; there is no P4.07.

## Secret/proprietary material rule

Configuration files may describe local inputs using placeholders or policy names, but must not contain Apple proprietary firmware, macOS disk images, real serial numbers, machine secrets, signing tickets, private keys, authentic hardware keys or device-specific credentials.

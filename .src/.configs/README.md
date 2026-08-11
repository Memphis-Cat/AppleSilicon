# Experiment Configurations

This directory contains reproducible, non-secret example configurations, policies and machine-readable compatibility contracts for AppleSilicon.

Current Part 02 contracts include:

```text
p2.01-cpu-contract.json
p2.02-framework-policy.json
p2.03-sysreg-policy.json
p2.04-feature-contract.json
```

## P2.01

`p2.01-cpu-contract.json` is the static source-locked inventory of Apple implementation-defined CPU register encodings and feature observations. Unknown runtime behavior remains explicitly unknown.

## P2.02

`p2.02-framework-policy.json` defines the fail-closed system-register framework boundary on TCG `apple-gxf`.

## P2.03

`p2.03-sysreg-policy.json` defines the legal read/write/reset/access policy classes and evidence/scope requirements. Its live semantic policy count remains zero until evidence promotes a register contract.

## P2.04

`p2.04-feature-contract.json` defines the source-backed minimum architectural VMApple CPU profile for TCG `apple-gxf`:

```text
PAuth presence
SSBS2
SME / SME2
PAN3
4 KiB stage-1 granules
16 KiB stage-1 granules
range TLBI
```

The contract uses a minimum/preserve-stronger rule and explicitly defers non-ID platform contracts such as paravirtualized PAC/CTRR, GICv3 and topology.

## Secret/proprietary material rule

Configuration files may describe local paths using placeholders, but must not contain Apple proprietary firmware, macOS disk images, serial numbers, machine secrets, signing tickets, private keys or device-specific credentials.

# Experiment Configurations

This directory contains reproducible, non-secret example configurations, policies and machine-readable compatibility contracts for AppleSilicon.

Current Part 02 contracts include:

```text
p2.01-cpu-contract.json
p2.02-framework-policy.json
p2.03-sysreg-policy.json
p2.04-feature-contract.json
p2.05-regression-policy.json
```

## P2.01

`p2.01-cpu-contract.json` is the static source-locked inventory of Apple implementation-defined CPU register encodings and feature observations. Unknown runtime behavior remains explicitly unknown.

## P2.02

`p2.02-framework-policy.json` defines the fail-closed system-register framework boundary on TCG `apple-gxf`.

## P2.03

`p2.03-sysreg-policy.json` defines the legal read/write/reset/access policy classes and evidence/scope requirements. Its live semantic policy count remains zero until evidence promotes a register contract.

## P2.04

`p2.04-feature-contract.json` defines the source-backed minimum architectural VMApple CPU profile for TCG `apple-gxf`: PAuth presence, SSBS2, SME/SME2, PAN3, 4 KiB + 16 KiB stage-1 granules and range TLBI. Stronger supported `max` capabilities are preserved.

## P2.05

`p2.05-regression-policy.json` locks the exact contract/patch inputs used by the deterministic CPU regression suite.

It protects:

```text
P2.01 inventory
P2.02 framework policy
P2.03 sysreg policy
P2.04 feature contract
patch 0003
patch 0004
patch 0005
```

The policy also requires `apple-gxf` + TCG scope, untouched `max` control behavior, zero live P2.03 sysreg semantics, enforced P2.04 feature requirements and deterministic regression output.

## Secret/proprietary material rule

Configuration files may describe local paths using placeholders, but must not contain Apple proprietary firmware, macOS disk images, serial numbers, machine secrets, signing tickets, private keys or device-specific credentials.

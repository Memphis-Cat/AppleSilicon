# Experiment Configurations

This directory contains reproducible, non-secret example configurations, policies and machine-readable compatibility contracts for AppleSilicon.

## Part 02 CPU contracts

```text
p2.01-cpu-contract.json
p2.02-framework-policy.json
p2.03-sysreg-policy.json
p2.04-feature-contract.json
p2.05-regression-policy.json
p2.06-integration-policy.json
```

Part 02 is closed at P2.06.

## Part 03 platform contracts

```text
p3.01-platform-contract.json
p3.02-identity-contract.json
p3.02-identity.example.json
p3.03-io-contract.json
p3.04-storage-contract.json
p3.05-peripheral-contract.json
p3.06-integration-policy.json
```

Part 03 is closed at P3.06.

## Part 04 runtime-evidence contracts

```text
p4.01-runtime-session-policy.json
```

### P4.01

`p4.01-runtime-session-policy.json` defines the pre-execution provenance lock for both runtime roles:

```text
probe      vmapple / TCG / apple-gxf
reference  vmapple / HVF / host / Darwin arm64
```

A session plan must bind a passing P3.06 integration fingerprint, the exact QEMU executable digest/version/capabilities, hashes and sizes of firmware/AUX/root/machine-identity inputs, optional hardware-model digest, and a SHA-256 digest of the canonicalized machine UUID.

The raw UUID and all local source paths/content remain excluded from the plan.

Part 04 is fixed at P4.01 through P4.06; there is no P4.07.

## Secret/proprietary material rule

Configuration files may describe local inputs using placeholders or policy names, but must not contain Apple proprietary firmware, macOS disk images, real serial numbers, machine secrets, signing tickets, private keys, authentic hardware keys or device-specific credentials.

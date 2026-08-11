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

### P3.01

`p3.01-platform-contract.json` assigns each non-CPU VMApple component to an ownership class and a fixed Part 03 objective.

### P3.02

`p3.02-identity-contract.json` records VMApple configuration/identity field ownership and the unresolved CPU-ID-array layout discrepancy.

`p3.02-identity.example.json` is synthetic only and demonstrates the privacy-safe local identity profile format.

### P3.03

`p3.03-io-contract.json` freezes the source-backed/reference wiring for GICv3, per-vCPU virtual timer PPI 27, PL011, PL031, PL061/power and pvpanic. Exact power-button event semantics remain runtime-evidence gated.

### P3.04

`p3.04-storage-contract.json` freezes the two-phase VMApple storage contract: BDIF MMIO/DMA pre-boot access, AUX/root backend topology, Apple `vmapple-virtio-blk-pci` identity/variants/config field and the current successful no-op Apple barrier. BDIF writes and real barrier flush semantics remain runtime-evidence gated.

### P3.05

`p3.05-peripheral-contract.json` freezes generic GPEX/virtio/XHCI ownership, the VMApple macOS XHCI conditional-interrupter compatibility policy, Apple AES MMIO/reset/known command behavior, unresolved AES commands, and the host-framework-dependent Apple PVG boundary. P1.05's optional-PVG policy is preserved and no fake GPU or new Inferno patch is introduced.

### P3.06

`p3.06-integration-policy.json` binds the exact P3.01–P3.05 contract/validator blobs to the passing P2.06 CPU integration result and Part 01 evidence/promotion policy. It requires the compatibility patch series to remain exactly `0001` through `0005`, preserves all evidence-gated unknown semantics, freezes the root README blob, and closes Part 03 only after deterministic integration validation.

## Secret/proprietary material rule

Configuration files may describe local paths using placeholders, but must not contain Apple proprietary firmware, macOS disk images, real serial numbers, machine secrets, signing tickets, private keys, authentic hardware keys or device-specific credentials.

# Research, Trace, CPU and Platform Contract Tools

Tools in this directory support reproducible compatibility research rather than guest patching.

## Part 01

Part 01 tools provide build/probe, trace normalization, reference-manifest and A/B evidence workflows. Part 01 is closed at P1.10.

## Part 02

Part 02 tools implement and validate the source-locked CPU compatibility contract through the P2.06 integration gate. Part 02 is closed at P2.06.

## Part 03 tools

```text
platform-contract.py
platform-identity.py
platform-io-contract.py
platform-storage-contract.py
platform-peripheral-contract.py
platform-integration-gate.py
prepare-p3.01.sh
prepare-p3.02.sh
prepare-p3.03.sh
prepare-p3.04.sh
prepare-p3.05.sh
prepare-p3.06.sh
run-p3.06-probe.sh
```

Part 03 is closed at P3.06.

### P3.01

`platform-contract.py` / `prepare-p3.01.sh` validate the non-CPU VMApple ownership inventory and fixed Part 03 objective map.

### P3.02

`platform-identity.py` / `prepare-p3.02.sh` validate and deterministically compile privacy-safe VMApple configuration/identity profiles without overriding machine-derived CPU/RAM/random/CPU-ID fields.

### P3.03

`platform-io-contract.py` / `prepare-p3.03.sh` validate the stable VMApple GICv3, architectural timer, PL011, PL031, PL061/power and pvpanic wiring.

### P3.04

`platform-storage-contract.py` / `prepare-p3.04.sh` validate VMApple's two-phase storage contract: BDIF MMIO/DMA pre-boot reads, AUX/root backend topology and Apple `vmapple-virtio-blk-pci` identity/extensions.

### P3.05

`platform-peripheral-contract.py` / `prepare-p3.05.sh` validate VMApple's GPEX PCIe geometry, virtio/XHCI compatibility defaults, default USB peripherals, Apple AES source-backed command/reset/MMIO contract and host-dependent Apple PVG optionalization.

### P3.06

`platform-integration-gate.py` consumes a passing P2.06 integration manifest, invokes every P3.01–P3.05 validator, verifies the exact patch series and locked artifact blobs, applies machine-wide fail-closed checks, and writes a deterministic Part 03 platform integration manifest.

`prepare-p3.06.sh` regenerates the P2.06 integration state, runs P3.06 twice, requires byte-identical manifests, and logs the complete preparation operation beneath `.logs/`.

P3.06 output:

```text
.build/p3.06/platform-integration-manifest.json
```

`run-p3.06-probe.sh` is the final Part 03 runtime wrapper. It validates the P3.06/P2.06 manifest binding and delegates:

```text
P3.06 -> P2.06 -> P1.07
```

It does not create a second QEMU launch path and cannot promote runtime evidence itself; P1.09/P1.10 remain authoritative.

## Rules

Preparation tools keep the pinned Inferno submodule pristine and use project-owned `.build/` and `.logs/` state. Secret or proprietary Apple artifacts must not be committed.

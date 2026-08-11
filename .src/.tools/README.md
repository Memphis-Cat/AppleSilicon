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
prepare-p3.01.sh
prepare-p3.02.sh
prepare-p3.03.sh
prepare-p3.04.sh
prepare-p3.05.sh
```

### platform-contract.py / prepare-p3.01.sh

Validate the non-CPU VMApple ownership inventory and fixed Part 03 objective map.

### platform-identity.py / prepare-p3.02.sh

Validate and deterministically compile privacy-safe VMApple configuration/identity profiles without overriding machine-derived CPU/RAM/random/CPU-ID fields.

### platform-io-contract.py / prepare-p3.03.sh

Validate the stable VMApple GICv3, architectural timer, PL011, PL031, PL061/power and pvpanic wiring against the pinned Inferno source.

### platform-storage-contract.py / prepare-p3.04.sh

Validate VMApple's two-phase storage contract: BDIF MMIO/DMA pre-boot reads, AUX/root backend topology and Apple `vmapple-virtio-blk-pci` identity/extensions.

### platform-peripheral-contract.py / prepare-p3.05.sh

Validate VMApple's GPEX PCIe geometry, virtio/XHCI compatibility defaults, default USB peripherals, Apple AES source-backed command/reset/MMIO contract and host-dependent Apple PVG optionalization.

The P3.05 source verifier deliberately rejects invented AES DSB/SKG/WRITE_REG support, authentic-key claims for public emulator constants, fake-PVG substitution and modern-macOS graphics compatibility claims without evidence.

P3.05 emits deterministic summaries beneath:

```text
.build/p3.05/
```

and logs meaningful preparation runs as:

```text
.logs/AppleSilicon-p3.05-YYYYMMDD-HHMMSS-PID.log
```

The preparation harness does not launch a macOS guest and does not open firmware, AUX/root storage or platform-identity inputs.

## Rules

Preparation tools keep the pinned Inferno submodule pristine and use project-owned `.build/` and `.logs/` state. Secret or proprietary Apple artifacts must not be committed.

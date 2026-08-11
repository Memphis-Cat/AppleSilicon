# Source

Project version: **`3.3.0.0.0.0`**

The source tree contains the closed Part 01 evidence pipeline, the closed Part 02 CPU compatibility contract, and active Part 03 VMApple platform-contract work through P3.04.

## Layout

```text
.src/
├── .upstream/.inferno/  # pinned Inferno submodule
├── .patches/            # ordered compatibility patches
├── .tools/              # logged preparation/regression/evidence tools
├── .configs/            # non-secret machine-readable contracts/configs
└── .fixtures/           # sanitized deterministic fixtures
```

## Part 01

Part 01 is closed at P1.10. Its build/probe, trace normalization, reference-manifest and A/B evidence pipeline remains available for final integration testing.

## Part 02

Part 02 is closed at P2.06. It owns the deliberate Apple-compatible CPU contract, including the fail-closed implementation-defined sysreg framework/policy model and the `apple-gxf` architectural feature contract.

The ordered source patch chain remains:

```text
0001-vmapple-decouple-build-from-hvf.patch
0002-vmapple-optional-apple-pvg.patch
0003-arm-apple-sysreg-framework.patch
0004-arm-apple-sysreg-policy-model.patch
0005-arm-vmapple-feature-contract.patch
```

## Part 03

Part 03 is fixed at exactly P3.01 through P3.06.

Completed platform objectives:

```text
P3.01  platform ownership inventory
P3.02  configuration and platform identity
P3.03  interrupt, timer, power and console
P3.04  boot backdoor and storage
```

P3.04 freezes the source-backed two-phase VMApple storage model:

```text
BDIF MMIO/DMA pre-boot reads
        +
Apple vmapple-virtio-blk-pci AUX/root runtime devices
```

It adds no new Inferno patch. BDIF write requirements and real Apple barrier flush/ordering semantics remain evidence-gated.

The next source objective is:

```text
P3.05 — PCIe, Peripheral, Crypto and Graphics Contract
```

P3.06 is the final Part 03 objective; there is no P3.07.

## Testing and artifacts

Intermediate objectives rely on development-side validation and persistent `.logs/` artifacts rather than repeated maintainer testing. Real macOS execution remains reserved for final integration.

No proprietary Apple firmware, macOS images, AUX/root storage artifacts, tickets, keys, machine-identity blobs or account secrets belong in `.src/`.

# Source

Project version: **`3.5.0.0.0.0`**

The source tree contains the closed Part 01 evidence pipeline, closed Part 02 CPU compatibility contract, and closed Part 03 VMApple platform contract through P3.06.

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

Part 01 is closed at P1.10. Its build/probe, trace normalization, reference-manifest and A/B evidence pipeline remains authoritative for runtime evidence and divergence promotion.

## Part 02

Part 02 is closed at P2.06. It owns the deliberate Apple-compatible CPU contract, including the fail-closed implementation-defined sysreg framework/policy model and the `apple-gxf` architectural feature contract.

## Part 03

Part 03 is closed at P3.06.

Completed platform objectives:

```text
P3.01  platform ownership inventory
P3.02  configuration and platform identity
P3.03  interrupt, timer, power and console
P3.04  boot backdoor and storage
P3.05  PCIe, peripheral, crypto and graphics
P3.06  Part 03 integration gate
```

The final P3.06 gate binds all Part 03 contracts to the passing P2.06 CPU integration state, invokes each platform validator, checks cross-contract evidence gates and emits:

```text
.build/p3.06/platform-integration-manifest.json
```

The final runtime delegation remains:

```text
P3.06 -> P2.06 -> P1.07
```

with P1.09/P1.10 controlling comparable evidence and divergence promotion.

## Compatibility patch chain

The ordered source patch chain remains exactly:

```text
0001-vmapple-decouple-build-from-hvf.patch
0002-vmapple-optional-apple-pvg.patch
0003-arm-apple-sysreg-framework.patch
0004-arm-apple-sysreg-policy-model.patch
0005-arm-vmapple-feature-contract.patch
```

Part 03 adds no `0006` patch.

Unknown config-layout, power-event, BDIF-write/barrier, AES-command and modern graphics behavior remains evidence-gated rather than implemented from guesses.

P1.05's optional real-PVG path remains in force and fake GPU substitution is forbidden.

## Next progression point

```text
Part 04
P4.01
```

Part 04 begins from the integrated CPU + platform contract and moves into runtime evidence instead of extending the Part 03 static contract inventory.

## Testing and artifacts

Intermediate objectives rely on development-side validation and persistent `.logs/` artifacts rather than repeated maintainer testing. Real macOS execution remains reserved for integrated runtime evidence.

No proprietary Apple firmware, macOS images, AUX/root storage artifacts, tickets, keys, authentic hardware secrets, machine-identity blobs or account secrets belong in `.src/`.

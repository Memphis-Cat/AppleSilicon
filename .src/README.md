# Source

Project version: **`2.2.0.0.0.0`**

The source tree contains the complete Part 01 evidence pipeline and the first three Part 02 Apple CPU compatibility objectives.

## Current layout

```text
.src/
├── .upstream/
│   └── .inferno/
├── .patches/
├── .tools/
├── .configs/
└── .fixtures/
```

## Upstream strategy

ChefKiss Inferno remains the pinned VMApple implementation base. QEMU is the reference for AArch64 cpreg behavior. Apple XNU provides public guest-side evidence. Asahi m1n1 provides Apple implementation-defined register encodings and authorized-hardware research tooling.

Project changes stay as ordered patches/tools/configs around a pristine pinned checkout.

## Part 01 closure

Part 01 is closed at P1.10.

## Part 02 source chain

Part 02 is fixed at P2.01 through P2.06.

P2.01:

```text
.src/.configs/p2.01-cpu-contract.json
.src/.tools/cpu-contract.py
.src/.tools/prepare-p2.01.sh
```

P2.02:

```text
.src/.patches/0003-arm-apple-sysreg-framework.patch
.src/.configs/p2.02-framework-policy.json
.src/.tools/prepare-p2.02.sh
```

P2.03:

```text
.src/.patches/0004-arm-apple-sysreg-policy-model.patch
.src/.configs/p2.03-sysreg-policy.json
.src/.tools/prepare-p2.03.sh
```

P2.03 adds independent read/write/reset/access policy dimensions, evidence/scope enforcement, duplicate-encoding validation and QEMU-native policy mappings.

The live semantic Apple sysreg table remains `0` entries because no P2.01 register semantics have been evidence-promoted.

Next:

```text
P2.04 — CPU Feature and ID-Register Compatibility
```

## Maintainer testing policy

Intermediate changes use logged development-side validation. Real macOS/HVF/TCG integration testing remains reserved for final integration.

## No proprietary Apple artifacts

Do not add Apple firmware, macOS images, installers, device-specific secrets, tickets, keys or machine-identity blobs to `.src/`.

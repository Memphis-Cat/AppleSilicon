# AppleSilicon Patch Series

Patches in this directory modify the pinned upstream emulator for AppleSilicon-specific experiments and compatibility work.

## Rules

- Keep `.src/.upstream/.inferno` pristine.
- Apply patches in numeric order to disposable working trees.
- Keep behavior changes reviewable and evidence-backed.
- Do not hide failures with broad bypasses.
- Do not invent register/device state merely to move boot farther.
- Pair compatibility patches with development-side validation.

## Current ordered series

```text
0001-vmapple-decouple-build-from-hvf.patch
0002-vmapple-optional-apple-pvg.patch
0003-arm-apple-sysreg-framework.patch
0004-arm-apple-sysreg-policy-model.patch
0005-arm-vmapple-feature-contract.patch
```

### 0001

Removes VMApple's build-time HVF dependency while preserving AArch64 as the machine requirement.

### 0002

Makes Apple paravirtual graphics construction optional for the early host-neutral VMApple research path.

### 0003

Adds fail-closed Apple AArch64 system-register registration infrastructure to TCG `apple-gxf`.

### 0004

Adds the evidence-gated Apple sysreg read/write/reset/access policy engine. Its live semantic policy table remains empty.

### 0005

P2.04's architectural CPU feature profile. It derives a minimum standard AArch64 feature/ID-register contract from public XNU VMApple declarations and scopes that profile to TCG `apple-gxf`.

It requires PAuth presence, SSBS2, SME/SME2, PAN3, 4 KiB + 16 KiB stage-1 granules and range TLBI, while preserving stronger QEMU `max` features. It deliberately does not implement paravirtualized PAC/CTRR, GICv3, topology, or Apple implementation-defined sysreg semantics.

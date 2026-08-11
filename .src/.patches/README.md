# AppleSilicon Patch Series

## Rules

- Keep `.src/.upstream/.inferno` pristine.
- Apply patches in numeric order to disposable trees.
- Prefer one behavior objective per patch.
- Do not hide unexplained failures with broad bypasses.
- Do not invent register values, reset state or side effects merely to move boot farther.
- Every compatibility patch should have a development-side validator or later regression test.

## Current ordered series

```text
0001-vmapple-decouple-build-from-hvf.patch
0002-vmapple-optional-apple-pvg.patch
0003-arm-apple-sysreg-framework.patch
0004-arm-apple-sysreg-policy-model.patch
```

### `0001-vmapple-decouple-build-from-hvf.patch`

Removes VMApple's build-time HVF dependency while preserving AArch64 as the machine requirement.

### `0002-vmapple-optional-apple-pvg.patch`

Makes Apple paravirtual graphics construction optional for the early TCG research path.

### `0003-arm-apple-sysreg-framework.patch`

P2.02's fail-closed Apple AArch64 sysreg framework. It adds `AppleSysRegSpec`, QEMU `ARMCPRegInfo` registration plumbing and TCG-only `apple-gxf` integration while installing zero live semantic policies.

### `0004-arm-apple-sysreg-policy-model.patch`

P2.03's semantic policy engine. It adds read/write/reset/access policy enums, `AppleSysRegPolicy`, evidence/scope enforcement, duplicate-encoding checks and mappings onto QEMU's cpreg constant/zero/ignore/storage/reset/trap/callback mechanisms.

The live semantic policy table remains empty until evidence promotes a concrete P2.01 register contract.

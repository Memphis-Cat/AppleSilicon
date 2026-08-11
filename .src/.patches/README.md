# AppleSilicon Patch Series

Patches in this directory modify the pinned upstream emulator for AppleSilicon-specific experiments and compatibility work.

## Rules

- Keep the pinned `.src/.upstream/.inferno` checkout pristine.
- Apply project patches in numeric order to disposable working trees.
- Prefer one hardware/behavior objective per patch where practical.
- Explain the guest-visible or development contract in the patch message.
- Do not hide unexplained guest failures with broad bypass patches.
- Keep research-only hacks clearly marked and separate from compatibility implementations.
- Do not invent register values, reset state or device behavior merely to move boot farther.
- Every compatibility patch should have a development-side validator or later regression test.

## Current ordered series

```text
0001-vmapple-decouple-build-from-hvf.patch
0002-vmapple-optional-apple-pvg.patch
0003-arm-apple-sysreg-framework.patch
```

### `0001-vmapple-decouple-build-from-hvf.patch`

Removes VMApple's build-time dependency on HVF while preserving AArch64 as the machine requirement. This allows the VMApple code to exist in a TCG-capable experimental build.

### `0002-vmapple-optional-apple-pvg.patch`

Makes Apple paravirtual graphics construction optional so missing Apple PVG support does not prevent the early VMApple TCG research path from being constructed.

### `0003-arm-apple-sysreg-framework.patch`

P2.02's Apple CPU framework patch.

It adds project-owned AArch64 Apple system-register plumbing using QEMU/Inferno's real `ARMCPRegInfo` infrastructure and attaches it only to the TCG `apple-gxf` CPU path.

The patch deliberately installs zero guest-visible Apple register policies by default. Its explicit undefined helper returns `CP_ACCESS_UNDEFINED`; it does not substitute read-as-zero, write-ignore, constant values, reset values, or fake stored state for unknown behavior.

P2.03 will extend this framework with an evidence-backed read/write/reset policy model.

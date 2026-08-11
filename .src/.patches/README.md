# AppleSilicon Patch Series

Patches in this directory modify the pinned upstream emulator for AppleSilicon-specific experiments and compatibility work.

## Rules

- One hardware/behavior objective per patch where practical.
- Explain the guest-visible contract in the commit message.
- Do not hide unexplained guest failures with broad bypass patches.
- Keep research-only hacks clearly marked and separate from compatibility implementations.
- Every compatibility patch should eventually have a reproducer or regression test.

## First planned patch

```text
0001-vmapple-allow-explicit-tcg-cpu.patch
```

Goal: make the VMApple experiment path accept an explicit TCG CPU cleanly so Part 01 can identify the first host-CPU dependency.

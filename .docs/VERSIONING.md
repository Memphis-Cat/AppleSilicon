# Versioning

AppleSilicon uses:

```text
MAJOR.UPDATE.EMERGENCY.FIX.RESERVED.HOTFIX
```

## Fields

1. **MAJOR** — very large project update.
2. **UPDATE** — normal meaningful project update.
3. **EMERGENCY** — critical release; size does not matter.
4. **FIX** — small corrective release larger than a hotfix.
5. **RESERVED** — intentionally undefined and kept at `0`.
6. **HOTFIX** — very small correction.

## Current version

```text
2.2.0.0.0.0
```

This normal update implements P2.03, **Register Read/Write/Reset Policy Model**.

P2.03 adds the data-driven Apple system-register policy engine on top of the P2.02 QEMU/Inferno cpreg framework.

The engine represents read, write, reset and access behavior independently; requires evidence and scope metadata; rejects conflicting encodings and inconsistent callback/state declarations; and preserves fail-closed undefined behavior.

It maps supported behavior onto QEMU's native cpreg mechanisms including `ARM_CP_CONST`, `arm_cp_read_zero`, `arm_cp_write_ignore`, `arm_cp_reset_ignore`, `fieldoffset`, `resetvalue`, access traps and callbacks.

No P2.01 Apple implementation-defined register has yet been promoted to a live semantic policy, so the live policy count remains `0`.

Part 02 remains fixed at six objectives and ends at P2.06. P2.04 is next.

The root `README.md` remains intentionally unchanged.

## Reset behavior

When a higher-order field increments, lower non-reserved fields normally reset to zero.

```text
0.1.0.0.0.7 -> 0.1.0.1.0.0
0.1.0.4.0.3 -> 0.2.0.0.0.0
0.9.0.0.0.0 -> 1.0.0.0.0.0
1.9.0.0.0.0 -> 2.0.0.0.0.0
2.0.0.0.0.0 -> 2.1.0.0.0.0
2.1.0.0.0.0 -> 2.2.0.0.0.0
```

# Versioning

AppleSilicon uses a six-field version number:

```text
MAJOR.UPDATE.EMERGENCY.FIX.RESERVED.HOTFIX
```

## Fields

1. **MAJOR** — very large project update or subsystem generation.
2. **UPDATE** — normal meaningful project update.
3. **EMERGENCY** — critically urgent release of any size.
4. **FIX** — small corrective release larger than a hotfix.
5. **RESERVED** — not assigned; remains `0` until formally defined.
6. **HOTFIX** — extremely small correction.

## Current version

```text
3.4.0.0.0.0
```

This normal update implements P3.05, **PCIe, Peripheral, Crypto and Graphics Contract**.

P3.05 freezes the remaining non-CPU VMApple peripheral ownership boundary. Generic GPEX PCIe, virtio transport/networking and QEMU XHCI remain preserved; pinned Inferno already carries the macOS XHCI `conditional-intr-mapping=on` compatibility behavior and VMApple's `disable-legacy=on` virtio default.

The Apple AES MMIO geometry/reset/public command set is source-locked while DSB, SKG and WRITE_REG remain evidence-gated because the public command processor does not implement them. Builtin AES constants are classified as emulator placeholders rather than authentic Apple hardware secrets.

Apple PVG remains host-framework dependent. P1.05's optional `qdev_try_new` behavior is preserved: real Apple PVG is used when available, otherwise VMApple warns and continues without it. P3.05 introduces no fake GPU and no new Inferno patch.

Part 03 remains fixed at exactly six objectives:

```text
P3.01 — Platform Contract Inventory and Ownership Map
P3.02 — Configuration and Platform Identity Contract
P3.03 — Interrupt, Timer, Power and Console Contract
P3.04 — Boot Backdoor and Storage Contract
P3.05 — PCIe, Peripheral, Crypto and Graphics Contract
P3.06 — Part 03 Integration Gate
```

There is no P3.07.

P3.06 is next and is the final Part 03 objective.

No real macOS/HVF/TCG guest execution is claimed for P3.05. The repository root `README.md` remains intentionally unchanged.

## Reset behavior

When a higher-order field increments, lower non-reserved fields normally reset to zero unless an emergency release requires preserving a specific lineage.

Examples:

```text
0.1.0.0.0.7 -> 0.1.0.1.0.0
0.1.0.4.0.3 -> 0.2.0.0.0.0
0.9.0.0.0.0 -> 1.0.0.0.0.0
1.9.0.0.0.0 -> 2.0.0.0.0.0
2.3.0.0.0.0 -> 2.4.0.0.0.0
2.4.0.0.0.0 -> 2.5.0.0.0.0
2.5.0.0.0.0 -> 3.0.0.0.0.0
3.0.0.0.0.0 -> 3.1.0.0.0.0
3.1.0.0.0.0 -> 3.2.0.0.0.0
3.2.0.0.0.0 -> 3.3.0.0.0.0
3.3.0.0.0.0 -> 3.4.0.0.0.0
```

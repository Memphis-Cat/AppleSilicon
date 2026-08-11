# Research, Trace and CPU Contract Tools

Tools in this directory support reproducible compatibility research rather than guest patching.

## Part 01 tools

```text
run-logged.sh
build-inferno.sh
probe-vmapple.sh
prepare-p1.04.sh
prepare-p1.05.sh
prepare-p1.06.sh
prepare-p1.07.sh
run-p1.07-probe.sh
compare-boot-traces.py
prepare-p1.08.sh
reference-manifest.py
prepare-p1.09.sh
run-p1.09-reference.sh
evidence-bundle.py
collect-p1.10-probe.sh
prepare-p1.10.sh
```

Part 01 closes at P1.10. There is no P1.11.

## Part 02 tools

Current Part 02 tools are:

```text
cpu-contract.py
prepare-p2.01.sh
prepare-p2.02.sh
```

### `cpu-contract.py`

This is P2.01's standard-library validator/query tool for `.src/.configs/p2.01-cpu-contract.json`.

It supports:

```text
validate
summary
lookup
self-check
```

The validator enforces exact source locks, valid AArch64 system-register encoding ranges, unique names/encoding tuples, evidence-source resolution, and the P2.01 rule that runtime priority/relevance/implementation semantics remain unknown/inventory-only.

### `prepare-p2.01.sh`

This is the logged development-side P2.01 harness. It validates JSON and Python syntax, runs contract validation/self-checks, prints a summary, performs representative register lookups, and writes a persistent `.log`.

It does not launch QEMU, macOS, HVF, a TCG guest or m1n1.

### `prepare-p2.02.sh`

This is P2.02's logged patch/framework validator.

It verifies the exact pinned Inferno revision, validates the P2.01 inventory contract, creates a disposable `.build/p2.02/inferno-src` checkout, and applies patches `0001`, `0002` and `0003` in order with `git apply --check` before each application.

It then verifies that:

- `target/arm/apple-sysregs.c` and `.h` exist;
- the framework is compiled by the AArch64 Meson source set;
- the framework is attached inside the TCG-only `apple-gxf` initializer path;
- the framework bridges through `define_one_arm_cp_reg()`;
- undefined Apple register access returns `CP_ACCESS_UNDEFINED`;
- undefined registrations are excluded from raw/GDB exposure;
- no read-as-zero, write-ignore, constant, reset-value or stored-state policy leaked into P2.02;
- the default guest-visible Apple sysreg policy count is zero;
- the complete patched tree passes `git diff --check`.

Every run writes:

```text
.logs/AppleSilicon-p2.02-YYYYMMDD-HHMMSS-PID.log
```

It does not launch a macOS guest, HVF session, TCG guest, or m1n1 runtime.

## Existing evidence tools

`compare-boot-traces.py` is P1.08's trace normalizer and earliest-divergence comparator.

`reference-manifest.py` is P1.09's privacy-safe manifest collector/validator/pair checker.

`run-p1.09-reference.sh` is the fail-closed Apple-Silicon/HVF reference runner reserved for final integration evidence collection.

`collect-p1.10-probe.sh` converts an already completed P1.07 runtime into a P1.09 probe manifest without relaunching QEMU.

`evidence-bundle.py` is the final Part 01 A/B evidence gate and requires reproduced runtime evidence before a local `P01-DIVERGENCE-0001` record may exist.

## Rules

Preparation tools keep the pinned Inferno submodule pristine and use project-owned `.build/`/`.logs/` state where applicable.

Tools must avoid collecting or committing machine-specific secrets unless explicitly required for a local authorized experiment, and secret/local artifacts must remain outside version control.

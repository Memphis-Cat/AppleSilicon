# Research, Trace and CPU Contract Tools

## Part 01 tools

Part 01 closes at P1.10. Its build, probe, trace, manifest, comparison and evidence tools remain available for final integration testing.

## Part 02 tools

```text
cpu-contract.py
prepare-p2.01.sh
prepare-p2.02.sh
prepare-p2.03.sh
```

### `cpu-contract.py`

Validates and queries `.src/.configs/p2.01-cpu-contract.json`.

### `prepare-p2.01.sh`

Logged P2.01 contract validator.

### `prepare-p2.02.sh`

Logged P2.02 framework validator. It applies patches `0001` through `0003` to a disposable pinned Inferno tree and verifies the TCG-only fail-closed framework with zero live policies.

### `prepare-p2.03.sh`

Logged P2.03 policy-model validator.

It validates the P2.01 inventory and P2.03 JSON contract, verifies QEMU cpreg policy APIs, applies patches `0001` through `0004`, checks evidence/scope and fail-closed invariants, verifies zero live semantic policies, preserves the P2.02 undefined helper and runs `git diff --check`.

Every run writes:

```text
.logs/AppleSilicon-p2.03-YYYYMMDD-HHMMSS-PID.log
```

It does not launch macOS, HVF, a TCG guest or m1n1.

## Rules

Preparation tools keep the pinned Inferno submodule pristine and use project-owned `.build/`/`.logs/` state. Tools must avoid collecting or committing machine-specific secrets.

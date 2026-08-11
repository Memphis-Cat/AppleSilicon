# Research, Trace, CPU, Platform and Runtime Evidence Tools

Tools in this directory support reproducible compatibility research rather than guest patching.

## Part 01

Part 01 tools provide build/probe, trace normalization, reference-manifest and A/B evidence workflows. Part 01 is closed at P1.10 and remains authoritative for runtime evidence/promotion.

## Part 02

Part 02 tools implement and validate the source-locked CPU compatibility contract through the P2.06 integration gate. Part 02 is closed at P2.06.

## Part 03

Part 03 tools validate the VMApple platform contracts and close them through P3.06. Part 03 is closed at P3.06.

## Part 04 tools

```text
runtime-session.py
prepare-p4.01.sh
plan-p4.01-session.sh
```

### runtime-session.py

Validates the P4.01 policy and creates privacy-safe deterministic pre-execution runtime session plans. It hashes the selected QEMU executable and local guest inputs, verifies role-specific QEMU capabilities, canonicalizes then hashes the machine UUID, and stores no raw local paths or guest artifact contents.

### prepare-p4.01.sh

Logged non-guest P4.01 preparation. It validates JSON/Python/Bash syntax, locked project artifacts, privacy rules, fixed Part 04 objective count and negative self-checks. It also rejects an unreviewed `0006` patch.

### plan-p4.01-session.sh

Logged local session planner. It requires a passing P3.06 integration manifest plus real local QEMU/VM inputs, generates the plan twice and requires byte-for-byte equality. It does not launch QEMU.

Default output pattern:

```text
.build/p4.01/<role>-runtime-session-plan.json
```

Logs:

```text
.logs/AppleSilicon-p4.01-prepare-*.log
.logs/AppleSilicon-p4.01-plan-<role>-*.log
```

## Rules

Preparation tools keep the pinned Inferno submodule pristine and use project-owned `.build/` and `.logs/` state. Secret or proprietary Apple artifacts must not be committed.

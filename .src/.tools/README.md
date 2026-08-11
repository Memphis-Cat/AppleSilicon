# Research, Trace and CPU Contract Tools

Tools in this directory support reproducible compatibility research rather than guest patching.

## Part 01

Part 01 tools provide build/probe, trace normalization, reference-manifest and A/B evidence workflows. Part 01 is closed at P1.10.

## Part 02 tools

```text
cpu-contract.py
prepare-p2.01.sh
prepare-p2.02.sh
prepare-p2.03.sh
prepare-p2.04.sh
```

### cpu-contract.py / prepare-p2.01.sh

Validate and query the source-locked P2.01 Apple CPU register/feature inventory.

### prepare-p2.02.sh

Validates the fail-closed Apple system-register framework and ordered patches through 0003.

### prepare-p2.03.sh

Validates the sysreg policy engine and ordered patches through 0004, including evidence/scope requirements and the zero live-semantic-policy invariant.

### prepare-p2.04.sh

P2.04's logged architectural feature-profile validator.

It checks the exact XNU VMApple and Inferno source locks, validates the P2.04 JSON contract, verifies pinned Inferno's feature-test/max-CPU capabilities, applies patches 0001–0005 to `.build/p2.04/inferno-src`, verifies TCG-only `apple-gxf` wiring and `max` isolation, validates the required PAuth/SSBS2/SME2/PAN3/TGran4/TGran16/TLBIRANGE postconditions, confirms P2.03's live sysreg policy count remains zero, and runs `git diff --check`.

Every run writes:

```text
.logs/AppleSilicon-p2.04-YYYYMMDD-HHMMSS-PID.log
```

It does not launch a macOS guest.

## Rules

Preparation tools keep the pinned Inferno submodule pristine and use project-owned `.build/` and `.logs/` state. Secret or proprietary Apple artifacts must not be committed.

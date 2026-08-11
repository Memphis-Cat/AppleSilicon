# Research, Trace, CPU and Platform Contract Tools

Tools in this directory support reproducible compatibility research rather than guest patching.

## Part 01

Part 01 tools provide build/probe, trace normalization, reference-manifest and A/B evidence workflows. Part 01 is closed at P1.10.

## Part 02

Part 02 tools implement and validate the source-locked CPU compatibility contract through the P2.06 integration gate. Part 02 is closed at P2.06.

## Part 03 tools

```text
platform-contract.py
platform-identity.py
platform-io-contract.py
prepare-p3.01.sh
prepare-p3.02.sh
prepare-p3.03.sh
```

### platform-contract.py / prepare-p3.01.sh

Validate the non-CPU VMApple ownership inventory and fixed Part 03 objective map.

### platform-identity.py / prepare-p3.02.sh

Validate and deterministically compile privacy-safe VMApple configuration/identity profiles without overriding machine-derived CPU/RAM/random/CPU-ID fields.

### platform-io-contract.py / prepare-p3.03.sh

Validate the stable VMApple GICv3, architectural timer, PL011, PL031, PL061/power and pvpanic wiring against the pinned Inferno source.

P3.03 emits deterministic summaries beneath:

```text
.build/p3.03/
```

and logs meaningful preparation runs as:

```text
.logs/AppleSilicon-p3.03-YYYYMMDD-HHMMSS-PID.log
```

No macOS guest is launched and no generic device is replaced.

## Rules

Preparation tools keep the pinned Inferno submodule pristine and use project-owned `.build/` and `.logs/` state. Secret or proprietary Apple artifacts must not be committed.

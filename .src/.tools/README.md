# Research, Trace and CPU Contract Tools

Tools in this directory support reproducible compatibility research rather than guest patching.

## Part 01

Part 01 tools provide build/probe, trace normalization, reference-manifest and A/B evidence workflows. Part 01 is closed at P1.10.

## Part 02 tools

```text
cpu-contract.py
cpu-contract-regression.py
prepare-p2.01.sh
prepare-p2.02.sh
prepare-p2.03.sh
prepare-p2.04.sh
prepare-p2.05.sh
```

### cpu-contract.py / prepare-p2.01.sh

Validate and query the source-locked P2.01 Apple CPU register/feature inventory.

### prepare-p2.02.sh

Validates the fail-closed Apple system-register framework and ordered patches through 0003.

### prepare-p2.03.sh

Validates the sysreg policy engine and ordered patches through 0004, including evidence/scope requirements and the zero live-semantic-policy invariant.

### prepare-p2.04.sh

Validates the VMApple architectural feature profile and ordered patches through 0005, including TCG-only `apple-gxf` wiring, `max` isolation, PAuth/SSBS2/SME2/PAN3/translation-granule/range-TLBI requirements and preservation of P2.03's empty live sysreg policy table.

### cpu-contract-regression.py / prepare-p2.05.sh

P2.05's deterministic non-guest CPU-contract regression suite.

It content-locks the P2.01–P2.04 contracts and patches 0003–0005, cross-checks objective sequencing and policy invariants, prepares the complete 0001–0005 patch chain on the pinned Inferno source, inspects the resulting `apple-gxf` source integration, and emits:

```text
.build/p2.05/cpu-contract-regression.json
```

The result contains a deterministic SHA-256 suite fingerprint. The logged preparation harness runs the regression twice and requires byte-identical JSON.

Every preparation run writes:

```text
.logs/AppleSilicon-p2.05-YYYYMMDD-HHMMSS-PID.log
```

No macOS guest is launched.

## Rules

Preparation tools keep the pinned Inferno submodule pristine and use project-owned `.build/` and `.logs/` state. Secret or proprietary Apple artifacts must not be committed.

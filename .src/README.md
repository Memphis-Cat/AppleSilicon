# Source

Project version: **`2.4.0.0.0.0`**

The source tree contains the complete Part 01 evidence pipeline and Part 02 CPU compatibility work through P2.05.

## Layout

```text
.src/
├── .upstream/.inferno/  # pinned Inferno submodule
├── .patches/            # ordered compatibility patches
├── .tools/              # logged preparation/regression/evidence tools
├── .configs/            # non-secret machine-readable contracts/configs
└── .fixtures/           # sanitized deterministic fixtures
```

## Part 01

Part 01 is closed at P1.10. Its evidence pipeline remains available for final integration testing.

## Part 02 source chain

Part 02 is fixed at P2.01 through P2.06.

P2.01 inventories Apple implementation-defined CPU registers and source-backed feature observations without assigning semantics.

P2.02 adds the fail-closed Apple sysreg registration framework.

P2.03 adds the evidence-gated sysreg read/write/reset/access policy engine. The live semantic table remains empty.

P2.04 adds the project-owned VMApple architectural minimum feature profile for TCG `apple-gxf` while leaving ordinary `max`, host/HVF and KVM paths unchanged.

P2.05 adds:

```text
.src/.configs/p2.05-regression-policy.json
.src/.tools/cpu-contract-regression.py
.src/.tools/prepare-p2.05.sh
```

The P2.05 suite content-locks the Part 02 contracts and patches through P2.04, prepares the full `0001`–`0005` patch series on the pinned Inferno source, verifies `max` isolation and TCG `apple-gxf` CPU wiring, checks that P2.03 still exposes zero live implementation-defined sysreg semantics, and emits a deterministic regression fingerprint.

The next source objective is:

```text
P2.06 — Part 02 Integration Gate
```

P2.06 is the final Part 02 objective.

## Testing and artifacts

Intermediate objectives rely on development-side validation and persistent `.logs/` artifacts rather than repeated maintainer testing. Real macOS execution remains reserved for final integration.

No proprietary Apple firmware, macOS images, tickets, keys, machine-identity blobs or account secrets belong in `.src/`.

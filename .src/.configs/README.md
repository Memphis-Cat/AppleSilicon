# Experiment Configurations

This directory contains reproducible, non-secret example configurations, policies and machine-readable compatibility contracts for AppleSilicon.

Current configurations include:

```text
inferno-build.env.example
vmapple-probe.env.example
vmapple-cpu.env.example
vmapple-preboot.env.example
p1.07-trace-events
p1.08-compare.json
p1.09-manifest-policy.json
p1.09-reference.example.json
p1.09-probe.example.json
p1.10-promotion-policy.json
p2.01-cpu-contract.json
p2.02-framework-policy.json
```

## Part 01

`vmapple-cpu.env.example` defines the explicit non-host VMApple CPU-selection profile.

`vmapple-preboot.env.example` defines local paths and probe controls for the finite TCG VMApple pre-boot experiment. Its paths are examples only; no Apple boot material is stored in the repository.

`p1.07-trace-events`, `p1.08-compare.json`, the P1.09 manifests/policy and `p1.10-promotion-policy.json` form the Part 01 trace/evidence contract.

## Part 02

`p2.01-cpu-contract.json` is the static source-locked Apple CPU contract inventory.

It records exact XNU/QEMU/m1n1 source identities, the pinned Inferno revision, Apple implementation-defined register encodings, feature-contract observations, and explicit deferred families.

Every P2.01 register remains:

```text
xnu_relevance = unknown
runtime_priority = unknown
implementation_state = inventory_only
```

The contract must not contain guessed reset values, fake register semantics or claims that a physical Apple register is required by VMApple merely because the register is known.

`p2.02-framework-policy.json` defines the source-level safety boundary for the first Apple sysreg framework:

```text
enabled CPU      = apple-gxf
accelerator      = tcg
control CPU      = max
unknown access   = CP_ACCESS_UNDEFINED
GDB exposure     = false
migration state  = false
invented values  = false
invented effects = false
invented resets  = false
```

Its six representative registers are validation references—one from each P2.01 group. They are cross-checked against the P2.01 inventory but are **not** installed as guest-visible policies by P2.02.

P2.03 owns the first evidence-backed read/write/reset policy table.

## Secret/proprietary material rule

Configuration files may describe paths using placeholders, but must not contain:

- Apple proprietary firmware,
- macOS disk images,
- serial numbers or machine secrets,
- signing tickets,
- private keys,
- device-specific credentials.

The goal is for another authorized researcher to recreate an experiment using their own locally obtained test material without copying restricted artifacts from this repository.

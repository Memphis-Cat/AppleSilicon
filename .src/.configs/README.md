# Experiment Configurations

This directory contains reproducible, non-secret example configurations, policies and machine-readable compatibility contracts.

Current Part 02 contracts:

```text
p2.01-cpu-contract.json
p2.02-framework-policy.json
p2.03-sysreg-policy.json
```

## P2.01

`p2.01-cpu-contract.json` is the source-locked Apple CPU inventory. Imported Apple implementation-defined registers remain `xnu_relevance = unknown`, `runtime_priority = unknown`, and `implementation_state = inventory_only` until stronger evidence promotes them.

## P2.02

`p2.02-framework-policy.json` records the fail-closed framework boundary: TCG `apple-gxf`, `max` control CPU, `CP_ACCESS_UNDEFINED` for unknown access, and no invented values/effects/resets.

Its representative registers are validation references, not live semantic policies.

## P2.03

`p2.03-sysreg-policy.json` defines:

```text
read   = undefined | stored | zero | constant | callback
write  = undefined | store | ignore | callback
reset  = none | value | callback
access = allow | undefined | trap_el1 | trap_el2 | trap_el3 | callback
```

Semantic policies require evidence and scope metadata. Stored state requires an explicit CPU field. Constants require write-ignore. Callback kinds require the matching callback. Duplicate encodings are forbidden.

Current live semantic policy count: `0`.

No register value or behavior is invented merely because its encoding is known.

## Secret/proprietary material rule

Configuration files may use placeholder paths, but must not contain Apple proprietary firmware, macOS disk images, serial numbers, signing tickets, private keys or device-specific credentials.

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
4.6.0.0.0.0
```

This is the **final post-roadmap stability hardening release**.

It does not create another Part or objective. P4.06 remains the final planned implementation objective; there is no P4.07 and no automatically defined Part 05.

The hardening pass corrected runtime/provenance defects before real integrated testing, including:

- VMApple's machine `uuid` property is handled as the pinned `uint64_t` machine ID/SDOM/ECID source rather than an RFC 128-bit UUID;
- compiled P3.02 machine identity is validated, machine-ID-bound and actually applied to QEMU;
- generated P2/P3/P4 fingerprints are recomputed before use;
- P1.07/P1.09 QEMU children are cleaned up on interruption;
- probe run IDs originate at runtime launch rather than evidence collection;
- P4 session/preflight/capture fingerprints are authenticated;
- P1.10 rejects empty canonical traces and unstructured fallback records as insufficient runtime evidence;
- Inferno build parallelism must be a positive integer;
- a final whole-repository static auditor locks the actual runtime shell wrappers as well as the policy/validator layers.

The compatibility patch chain still ends at `0005`; no evidence justified a new Inferno patch.

The final static hardening classification is:

```text
FINAL_STABILITY_AUDIT_PASS
```

This classification means the source/repository stability audit passed when the repository-owned final harness is executed. It is intentionally separate from real runtime validation.

Current project state remains:

```text
planned implementation roadmap  complete
final stability hardening        implemented
real runtime evidence validation pending
```

No real macOS boot, TCG success, HVF equivalence or full Apple-Silicon compatibility is claimed by version `4.6.0.0.0.0` without the required runtime evidence.

The repository root `README.md` remains intentionally unchanged.

## Reset behavior

When a higher-order field increments, lower non-reserved fields normally reset to zero unless an emergency release requires preserving a specific lineage.

Examples:

```text
0.9.0.0.0.0 -> 1.0.0.0.0.0
1.9.0.0.0.0 -> 2.0.0.0.0.0
2.5.0.0.0.0 -> 3.0.0.0.0.0
3.5.0.0.0.0 -> 4.0.0.0.0.0
4.5.0.0.0.0 -> 4.6.0.0.0.0
```

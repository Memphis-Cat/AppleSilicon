# Final Stability Audit

Project hardening release: **`4.6.0.0.0.0`**

Status: **Final planned implementation hardening complete; real runtime validation remains pending**

This is a cross-roadmap stability release after P4.06. It does **not** create P4.07 or Part 05 and does not add speculative Apple behavior.

## Scope

The hardening pass reviewed the project-owned implementation surface with emphasis on:

- the five Inferno compatibility patches;
- build/preparation wrappers;
- CPU/platform integration manifests;
- runtime argument construction;
- P3.02 identity handling;
- P4.01 provenance planning;
- P4.02/P4.03 capture paths;
- P4.04 A/B admission;
- P1.08/P1.09/P1.10 comparison and promotion;
- P4.05/P4.06 promotion/final-gate integration;
- deterministic fingerprints, file modes, privacy boundaries and process cleanup.

## Important defects found and corrected

### 1. VMApple `uuid` property type

The pinned VMApple implementation exposes the machine property named `uuid` as a `uint64_t`. The runtime evidence layer had incorrectly treated that property as a conventional 128-bit UUID.

The hardened path now treats it as a VMApple unsigned 64-bit machine ID/SDOM/ECID source. Decimal and `0x`-prefixed input are accepted and canonicalized to decimal ASCII for privacy-safe hashing.

The legacy environment-variable name `APPLESILICON_VMAPPLE_UUID` is retained only for compatibility with existing local scripts.

### 2. Machine identity was provenance-only

The runtime plans hashed the machine-identity input, but the QEMU launchers did not apply its compiled `vmapple-cfg.*` properties.

The runtime now requires a compiled P3.02 identity artifact, reproduces its fingerprint, verifies that its machine ID matches the VMApple machine ID, permits only the expected `vmapple-cfg.*` globals, and actually appends those validated globals to both TCG and HVF launches.

Example-only P3.02 profiles are rejected for real runtime sessions.

### 3. Generated fingerprints were trusted by shape

Several later stages checked only that upstream fingerprints were 64 hexadecimal characters.

P2.06, P3.06, P4.01, P4.02 and P4.03 consumers now recompute the generated fingerprints before accepting the document. P4.04 re-authenticates the P4.01 plans and P4.02/P4.03 capture fingerprints before admitting a pair.

### 4. Probe run independence could be repackaged

The P1.10 probe collector previously created a new run ID while packaging an already completed P1.07 run. The same launcher log could therefore be collected twice with different IDs.

P1.07 now creates and logs the runtime run ID before QEMU starts. The collector reuses that exact ID. Recollecting one launcher log remains the same run and cannot satisfy the P4.05 independent-reproduction rule.

### 5. QEMU interruption cleanup

The controlled TCG and HVF launchers now install signal/exit cleanup guards. An interrupted wrapper attempts TERM, waits for the configured grace period, escalates to KILL if necessary, and reaps the child.

This reduces orphaned QEMU processes and held-open local VM inputs after aborted runs.

### 6. Empty/unstructured trace false equivalence

Two traces with zero canonical events could previously look equivalent merely because both normalized streams were empty. Unstructured fallback records could also enter the evidence path.

P1.10 now requires at least one canonical event in each supplied runtime trace and requires all promotable runtime records to be structured trace events. Empty or fallback-only observations are **insufficient evidence**, not equivalence.

### 7. Build parallelism input

`APPLESILICON_JOBS` is now required to resolve to a positive integer. Invalid, zero or negative parallelism no longer reaches `make -j` with host-dependent behavior.

## Emulator patch conclusion

The source-level audit did not establish evidence for another Apple CPU, sysreg, VMApple device or storage behavior.

The compatibility patch series therefore remains exactly:

```text
0001-vmapple-decouple-build-from-hvf.patch
0002-vmapple-optional-apple-pvg.patch
0003-arm-apple-sysreg-framework.patch
0004-arm-apple-sysreg-policy-model.patch
0005-arm-vmapple-feature-contract.patch
```

There is no `0006`.

Known evidence-gated unknowns remain evidence-gated rather than being guessed.

## Whole-repository auditor

The hardening release adds:

```text
.src/.configs/final-stability-policy.json
.src/.tools/final-stability-audit.py
.src/.tools/prepare-final-stability.sh
```

The audit scans the full project-owned configuration/tool surface:

- every `.src/.configs/**/*.json` must parse;
- every `.src/.tools/**/*.py` must compile;
- every `.src/.tools/**/*.sh` must pass `bash -n`;
- project-owned Python and shell tools must be Git mode `100755`;
- the root README blob must remain frozen;
- the Inferno gitlink must remain exact;
- patches must remain exactly `0001`–`0005` with exact blobs;
- critical runtime shell wrappers and evidence validators are source-locked;
- P1.10, P3 and P4 static validators/self-checks are executed;
- a P3.02 synthetic identity is compiled in temporary state and passed through the shared runtime-identity validator;
- obsolete RFC-UUID parsing and normalization are rejected from runtime sources.

`prepare-final-stability.sh` executes the complete audit twice and requires byte-identical output.

Expected static classification:

```text
FINAL_STABILITY_AUDIT_PASS
```

with:

```text
planned_implementation_complete = true
runtime_validation_pending = true
guest_execution = false
roadmap_extended = false
```

## Runtime boundary

This hardening pass does not launch macOS and does not claim that `apple-gxf`, VMApple, graphics, AES, storage, or any other subsystem is runtime-sufficient.

A real runtime result still requires the implemented pipeline:

```text
P4.01 provenance
    ↓
P4.02 TCG / apple-gxf probe
    +
P4.03 Apple Silicon / HVF / host reference
    ↓
P4.04 comparable A/B sessions
    ↓
P4.05 reproduced divergence promotion when applicable
    ↓
P4.06 runtime evidence gate
```

The next project action is **integrated runtime testing**, not another predetermined implementation objective.

# Research and Trace Tools

Tools in this directory support reproducible compatibility research rather than guest patching.

Current tools include:

```text
run-logged.sh
build-inferno.sh
probe-vmapple.sh
prepare-p1.04.sh
prepare-p1.05.sh
prepare-p1.06.sh
prepare-p1.07.sh
run-p1.07-probe.sh
compare-boot-traces.py
prepare-p1.08.sh
reference-manifest.py
prepare-p1.09.sh
run-p1.09-reference.sh
evidence-bundle.py
collect-p1.10-probe.sh
prepare-p1.10.sh
```

The preparation tools keep the pinned Inferno submodule pristine and build disposable research trees under `.build/`.

`prepare-p1.06.sh` validates QEMU's explicit CPU-selection path and emits deterministic TCG VMApple CPU-profile metadata using either `max` or Inferno's `apple-gxf` model.

`prepare-p1.07.sh` extends that prepared source into the first complete pre-boot probe manifest without launching a guest.

`run-p1.07-probe.sh` is the runtime harness reserved for final integration testing. It validates VMApple/TCG/CPU/trace capabilities and local boot inputs, then runs a finite probe while preserving separate launcher, serial, and QEMU debug logs.

`compare-boot-traces.py` is P1.08's standard-library trace normalizer and earliest-divergence comparator. It removes only configured host-runtime noise, preserves guest-semantic MMIO fields, produces normalized streams plus Markdown/JSON candidate reports, and supports bounded resynchronization.

`reference-manifest.py` is P1.09's privacy-safe manifest collector/validator/pair checker. It proves that reference/probe inputs and experiment settings are comparable without publishing raw VM identity or Apple guest material.

`run-p1.09-reference.sh` is the fail-closed Apple-Silicon/HVF reference runner reserved for final integration evidence collection.

`collect-p1.10-probe.sh` converts an already completed P1.07 runtime into a P1.09 probe manifest. It does not relaunch QEMU.

`evidence-bundle.py` is the final Part 01 A/B evidence gate. It verifies P1.09 pairing, verifies supplied trace hashes against their manifests, invokes P1.08 comparison, generates non-promoted candidates, fingerprints the comparison contract and earliest divergence, and requires at least two unique matching runtime reproductions before creating a local `P01-DIVERGENCE-0001` record.

`prepare-p1.10.sh` runs the final non-runtime Part 01 regression/self-check chain and writes a mandatory `.log`. It does not launch QEMU, macOS, HVF, TCG guests, or m1n1.

Part 01 closes at P1.10. There is no P1.11.

Tools must avoid collecting or committing machine-specific secrets unless explicitly required for a local authorized experiment, and secret/local artifacts must remain outside version control.

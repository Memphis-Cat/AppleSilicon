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
```

The preparation tools keep the pinned Inferno submodule pristine and build disposable research trees under `.build/`.

`prepare-p1.06.sh` validates QEMU's explicit CPU-selection path and emits deterministic TCG VMApple CPU-profile metadata using either `max` or Inferno's `apple-gxf` model.

`prepare-p1.07.sh` extends that prepared source into the first complete pre-boot probe manifest without launching a guest.

`run-p1.07-probe.sh` is the runtime TCG harness reserved for final integration testing. It validates VMApple/TCG/CPU/trace capabilities and local boot inputs, then runs a finite probe while preserving separate launcher, serial, and QEMU debug logs.

`compare-boot-traces.py` is P1.08's standard-library trace normalizer and earliest-divergence comparator. It removes only configured host-runtime noise, preserves guest-semantic MMIO fields, produces normalized streams plus Markdown/JSON candidate reports, and supports bounded resynchronization.

`prepare-p1.08.sh` validates the comparator without QEMU or macOS using embedded checks and sanitized fixtures. Every validation run writes a persistent `.log`.

`reference-manifest.py` is P1.09's evidence collector/validator. It hashes local guest inputs and artifacts without copying their contents, rejects sensitive material from versionable manifests, validates reference/probe role contracts, and checks whether two manifests are comparable before their traces can be interpreted as an A/B experiment.

`run-p1.09-reference.sh` defines the controlled Apple-Silicon/HVF reference capture. It fails closed on non-Darwin/non-arm64 hosts, validates VMApple/HVF/trace capabilities, uses the same finite evidence shape as the probe, and creates a sanitized local reference manifest after execution.

`prepare-p1.09.sh` validates the P1.09 policy/examples/tooling and collector with synthetic files. It syntax-checks the runtime reference harness but does not launch QEMU, macOS, HVF, or m1n1.

Tools must avoid collecting or committing machine-specific secrets unless explicitly required for a local authorized experiment, and secret/local artifacts must remain outside version control.

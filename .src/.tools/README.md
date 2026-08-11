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
```

The preparation tools keep the pinned Inferno submodule pristine and build disposable research trees under `.build/`.

`prepare-p1.06.sh` validates QEMU's explicit CPU-selection path and emits deterministic TCG VMApple CPU-profile metadata using either `max` or Inferno's `apple-gxf` model.

`prepare-p1.07.sh` extends that prepared source into the first complete pre-boot probe manifest without launching a guest.

`run-p1.07-probe.sh` is the runtime harness reserved for final integration testing. It validates VMApple/TCG/CPU/trace capabilities and local boot inputs, then runs a finite probe while preserving separate launcher, serial, and QEMU debug logs.

`compare-boot-traces.py` is P1.08's standard-library trace normalizer and earliest-divergence comparator. It removes only configured host-runtime noise, preserves guest-semantic MMIO fields, produces normalized streams plus Markdown/JSON candidate reports, and supports bounded resynchronization.

`prepare-p1.08.sh` validates the comparator without QEMU or macOS using embedded checks and sanitized fixtures. Every validation run writes a persistent `.log`.

Tools must avoid collecting or committing machine-specific secrets unless explicitly required for a local authorized experiment, and secret/local artifacts must remain outside version control.

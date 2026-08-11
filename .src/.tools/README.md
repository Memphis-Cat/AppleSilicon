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
```

The preparation tools keep the pinned Inferno submodule pristine and build disposable research trees under `.build/`.

`prepare-p1.06.sh` validates QEMU's existing explicit CPU-selection path and emits a deterministic TCG VMApple CPU profile using either `max` or Inferno's `apple-gxf` model. It does not boot a guest.

`prepare-p1.07.sh` extends that prepared source into the first complete pre-boot probe manifest. It still does not launch a guest.

`run-p1.07-probe.sh` is the runtime harness reserved for final integration testing. It validates VMApple/TCG/CPU/trace capabilities and local boot inputs, then runs a finite probe while preserving separate launcher, serial, and QEMU debug logs.

Later tools will normalize and compare these traces so the earliest meaningful divergence can be extracted automatically.

Tools must avoid collecting or committing machine-specific secrets unless explicitly required for a local experiment, and secret/local artifacts must remain outside version control.

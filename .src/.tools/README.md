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
```

The preparation tools keep the pinned Inferno submodule pristine and build disposable research trees under `.build/`.

`prepare-p1.06.sh` validates QEMU's existing explicit CPU-selection path and emits a deterministic TCG VMApple CPU profile using either `max` or Inferno's `apple-gxf` model. It does not boot a guest.

Later tools are expected to include differential boot-trace comparison and normalization once the first controlled TCG launch objective begins.

Tools must avoid collecting or committing machine-specific secrets unless explicitly required for a local experiment, and secret/local artifacts must remain outside version control.

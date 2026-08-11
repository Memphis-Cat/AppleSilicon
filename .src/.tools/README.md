# Research and Trace Tools

Tools in this directory will support reproducible compatibility research rather than guest patching.

Planned first tools:

```text
compare-boot-traces.py
host-capabilities.py
normalize-qemu-log.py
```

The first useful tool should compare a known-good Apple-host VMApple trace against a TCG/non-host CPU trace and report the earliest meaningful divergence.

Tools must avoid collecting or committing machine-specific secrets unless explicitly required for a local experiment, and secret/local artifacts must remain outside version control.

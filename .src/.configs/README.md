# Experiment Configurations

This directory contains reproducible, non-secret example configurations for AppleSilicon experiments.

Current configurations include:

```text
inferno-build.env.example
vmapple-probe.env.example
vmapple-cpu.env.example
vmapple-preboot.env.example
p1.07-trace-events
```

`vmapple-cpu.env.example` belongs to P1.06 and defines the explicit non-host VMApple CPU-selection profile. The default control profile is TCG + `max`; Inferno's existing `apple-gxf` model is also accepted as an Apple-oriented experimental comparison profile.

`vmapple-preboot.env.example` belongs to P1.07 and defines local paths and probe controls for the first complete TCG VMApple pre-boot experiment. Its paths are examples only; no Apple boot material is stored in the repository.

`p1.07-trace-events` is the version-controlled initial trace set. The runtime harness verifies every configured event against `qemu-system-aarch64 -trace help` before launch instead of assuming the built QEMU binary exposes it.

Configuration files may describe paths using placeholders, but must not contain:

- Apple proprietary firmware,
- macOS disk images,
- serial numbers or machine secrets,
- signing tickets,
- private keys,
- device-specific credentials.

The goal is for another authorized researcher to recreate an experiment using their own locally obtained test material without copying restricted artifacts from this repository.

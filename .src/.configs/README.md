# Experiment Configurations

This directory contains reproducible, non-secret example configurations for AppleSilicon experiments.

Current configurations include:

```text
inferno-build.env.example
vmapple-probe.env.example
vmapple-cpu.env.example
```

`vmapple-cpu.env.example` belongs to P1.06 and defines the explicit non-host VMApple CPU-selection profile. The default control profile is TCG + `max`; Inferno's existing `apple-gxf` model is also accepted as an Apple-oriented experimental comparison profile.

Configuration files may describe paths using placeholders, but must not contain:

- Apple proprietary firmware,
- macOS disk images,
- serial numbers or machine secrets,
- signing tickets,
- private keys,
- device-specific credentials.

The goal is for another authorized researcher to recreate an experiment using their own locally obtained test material without copying restricted artifacts from this repository.

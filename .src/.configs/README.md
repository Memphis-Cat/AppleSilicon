# Experiment Configurations

This directory will contain reproducible, non-secret example configurations for AppleSilicon experiments.

Planned first configurations:

```text
reference-hvf.example
tcg-probe.example
```

Configuration files may describe paths using placeholders, but must not contain:

- Apple proprietary firmware,
- macOS disk images,
- serial numbers or machine secrets,
- signing tickets,
- private keys,
- device-specific credentials.

The goal is for another authorized researcher to recreate an experiment using their own locally obtained test material without copying restricted artifacts from this repository.

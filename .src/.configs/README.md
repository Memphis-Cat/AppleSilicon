# Experiment Configurations

This directory contains reproducible, non-secret example configurations and policies for AppleSilicon experiments.

Current configurations include:

```text
inferno-build.env.example
vmapple-probe.env.example
vmapple-cpu.env.example
vmapple-preboot.env.example
p1.07-trace-events
p1.08-compare.json
p1.09-manifest-policy.json
p1.09-reference.example.json
p1.09-probe.example.json
p1.10-promotion-policy.json
```

`vmapple-cpu.env.example` belongs to P1.06 and defines the explicit non-host VMApple CPU-selection profile. The default control profile is TCG + `max`; Inferno's existing `apple-gxf` model is also accepted as an Apple-oriented experimental comparison profile.

`vmapple-preboot.env.example` belongs to P1.07 and defines local paths and probe controls for the first complete TCG VMApple pre-boot experiment. Its paths are examples only; no Apple boot material is stored in the repository.

`p1.07-trace-events` is the version-controlled initial MMIO trace set. The runtime harness verifies every configured event against `qemu-system-aarch64 -trace help` before launch.

`p1.08-compare.json` defines deterministic trace-analysis behavior, including the selected event names, context size, bounded resynchronization window, guest fields that must be preserved, and host-only fields that may be normalized away.

The P1.09 files define the privacy-safe reference/probe evidence-manifest contract and sanitized examples.

`p1.10-promotion-policy.json` closes Part 01. It requires at least two unique matching runtime A/B reproductions, the same P1.09 contract fingerprint, the same earliest-divergence signature, and explicitly blocks synthetic/example/self-check evidence from promotion. It also forbids automatic GitHub commits from the promotion tool.

Configuration files may describe paths using placeholders, but must not contain:

- Apple proprietary firmware,
- macOS disk images,
- serial numbers or machine secrets,
- signing tickets,
- private keys,
- device-specific credentials.

The goal is for another authorized researcher to recreate an experiment using their own locally obtained test material without copying restricted artifacts from this repository.

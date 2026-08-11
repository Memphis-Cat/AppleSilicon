# Sanitized Fixtures

This directory contains synthetic or deliberately sanitized development fixtures.

Fixtures must never contain proprietary Apple firmware, macOS disk data, real machine identifiers, account information, authentication material, private keys, tickets, or other machine secrets.

Current fixture sets:

```text
.p1.08/
```

P1.08 uses synthetic QEMU MMIO trace records to validate normalization and divergence extraction without launching a guest.

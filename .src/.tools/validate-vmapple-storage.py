#!/usr/bin/env python3

from pathlib import Path
import argparse
import hashlib
import struct
import sys

def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()

def is_all_zero(path, sample_size=16 * 1024 * 1024):
    size = path.stat().st_size

    positions = {0}
    if size > sample_size:
        positions.add(max(0, size // 2 - sample_size // 2))
        positions.add(max(0, size - sample_size))

    with path.open("rb") as f:
        for pos in sorted(positions):
            f.seek(pos)
            data = f.read(min(sample_size, size - pos))
            if any(data):
                return False

    return True

def inspect_aux(path):
    rows = []

    with path.open("rb") as f:
        for off in range(0, min(path.stat().st_size, 0x20000), 0x1000):
            f.seek(off)
            data = f.read(0x200)

            if len(data) < 8:
                break

            first8 = struct.unpack_from("<Q", data, 0)[0]
            second8 = (
                struct.unpack_from("<Q", data, 8)[0]
                if len(data) >= 16 else 0
            )

            rows.append((
                off,
                first8,
                second8,
                sum(b != 0 for b in data)
            ))

    return rows

p = argparse.ArgumentParser()
p.add_argument("--aux", required=True, type=Path)
p.add_argument("--root", required=True, type=Path)
a = p.parse_args()

failed = False

for label, path in (("AUX", a.aux), ("ROOT", a.root)):
    print(f"===== {label} =====")
    print(f"Path: {path}")

    if not path.is_file():
        print("ERROR: file does not exist")
        failed = True
        print()
        continue

    size = path.stat().st_size

    print(f"Size: {size} bytes ({size / 1024**3:.3f} GiB)")
    print(f"SHA-256: {sha256(path)}")

    zero = is_all_zero(path)
    print(f"Sampled all-zero: {'YES' if zero else 'NO'}")

    if size == 0:
        print("ERROR: empty image")
        failed = True

    if zero:
        print("ERROR: image appears blank")
        failed = True

    print()

if a.aux.is_file():
    print("===== AUX EARLY-SECTOR SUMMARY =====")

    rows = inspect_aux(a.aux)

    nonzero_sectors = 0

    for off, first8, second8, count in rows:
        if count:
            nonzero_sectors += 1

        print(
            f"0x{off:08x} "
            f"first8=0x{first8:016x} "
            f"second8=0x{second8:016x} "
            f"nonzero={count}/512"
        )

    print()
    print(f"Inspected sectors: {len(rows)}")
    print(f"Non-zero sectors: {nonzero_sectors}")

    if not nonzero_sectors:
        print("ERROR: inspected AUX region is completely blank")
        failed = True

print()
if failed:
    print("RESULT: INVALID_OR_SYNTHETIC")
    sys.exit(1)

print("RESULT: NONBLANK_STORAGE_PREFLIGHT_PASS")
print("NOTE: this confirms readable, non-blank storage only; it does not prove VMApple/macOS structural validity")

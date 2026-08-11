#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable, Optional

VERSION = "0.8.0.0.0.0"
DEFAULT_CONFIG = Path(__file__).resolve().parents[1] / ".configs" / "p1.08-compare.json"
DIVERGENCE_EXIT = 10
INPUT_ERROR_EXIT = 2

MMIO_RE = re.compile(
    r"^(?P<event>memory_region_ops_(?:read|write))\s+"
    r"cpu\s+(?P<cpu>\d+)\s+"
    r"mr\s+(?P<mr>\S+)\s+"
    r"addr\s+(?P<addr>0[xX][0-9a-fA-F]+)\s+"
    r"value\s+(?P<value>0[xX][0-9a-fA-F]+)\s+"
    r"size\s+(?P<size>\d+)\s+"
    r"name\s+'(?P<name>(?:[^'\\]|\\.)*)'\s*$"
)


@dataclass(frozen=True)
class TraceRecord:
    event_index: int
    source_line: int
    raw: str
    canonical: str
    event: str
    fields: dict[str, Any]
    structured: bool


@dataclass(frozen=True)
class TraceStream:
    path: str
    records: list[TraceRecord]
    ignored_lines: int


class TraceError(Exception):
    pass


def normalize_hex(value: str) -> str:
    return f"0x{int(value, 16):x}"


def escape_name(value: str) -> str:
    return value.replace("\\", "\\\\").replace("'", "\\'")


def load_config(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise TraceError(f"configuration file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise TraceError(f"invalid JSON configuration {path}: {exc}") from exc

    if data.get("schema") != 1:
        raise TraceError(f"unsupported configuration schema: {data.get('schema')!r}")

    events = data.get("extract_events")
    if not isinstance(events, list) or not events or not all(isinstance(x, str) for x in events):
        raise TraceError("extract_events must be a non-empty list of event names")

    for key in ("context_records", "resync_window"):
        value = data.get(key)
        if not isinstance(value, int) or value < 0:
            raise TraceError(f"{key} must be a non-negative integer")

    return data


def extract_event_payload(line: str, events: Iterable[str]) -> Optional[str]:
    best: Optional[tuple[int, str]] = None
    for event in events:
        position = line.find(event)
        if position < 0:
            continue
        if best is None or position < best[0]:
            best = (position, event)
    if best is None:
        return None
    return line[best[0] :].strip()


def canonicalize_payload(payload: str) -> tuple[str, str, dict[str, Any], bool]:
    match = MMIO_RE.fullmatch(payload)
    if match:
        fields: dict[str, Any] = {
            "cpu": int(match.group("cpu"), 10),
            "addr": normalize_hex(match.group("addr")),
            "value": normalize_hex(match.group("value")),
            "size": int(match.group("size"), 10),
            "name": match.group("name"),
        }
        event = match.group("event")
        canonical = (
            f"{event} "
            f"cpu={fields['cpu']} "
            f"addr={fields['addr']} "
            f"value={fields['value']} "
            f"size={fields['size']} "
            f"name='{escape_name(fields['name'])}'"
        )
        return canonical, event, fields, True

    event = payload.split(None, 1)[0]
    canonical = " ".join(payload.split())
    return canonical, event, {"payload": canonical}, False


def parse_lines(lines: Iterable[str], source_name: str, config: dict[str, Any]) -> TraceStream:
    events = config["extract_events"]
    records: list[TraceRecord] = []
    ignored = 0

    for source_line, line in enumerate(lines, start=1):
        raw = line.rstrip("\r\n")
        payload = extract_event_payload(raw, events)
        if payload is None:
            ignored += 1
            continue
        canonical, event, fields, structured = canonicalize_payload(payload)
        records.append(
            TraceRecord(
                event_index=len(records),
                source_line=source_line,
                raw=raw,
                canonical=canonical,
                event=event,
                fields=fields,
                structured=structured,
            )
        )

    return TraceStream(path=source_name, records=records, ignored_lines=ignored)


def parse_file(path: Path, config: dict[str, Any]) -> TraceStream:
    try:
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            return parse_lines(handle, str(path), config)
    except OSError as exc:
        raise TraceError(f"could not read trace file {path}: {exc}") from exc


def write_normalized(stream: TraceStream, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = "\n".join(record.canonical for record in stream.records)
    if text:
        text += "\n"
    path.write_text(text, encoding="utf-8")


def record_public(record: Optional[TraceRecord]) -> Optional[dict[str, Any]]:
    if record is None:
        return None
    return {
        "event_index": record.event_index,
        "source_line": record.source_line,
        "canonical": record.canonical,
        "raw": record.raw,
        "event": record.event,
        "fields": record.fields,
        "structured": record.structured,
    }


def classify_pair(reference: TraceRecord, probe: TraceRecord) -> str:
    if reference.event != probe.event:
        return "event_divergence"
    if not reference.structured or not probe.structured:
        return "unstructured_payload_divergence"

    for field, classification in (
        ("cpu", "cpu_divergence"),
        ("addr", "mmio_address_divergence"),
        ("size", "mmio_size_divergence"),
        ("name", "mmio_region_divergence"),
        ("value", "mmio_value_divergence"),
    ):
        if reference.fields.get(field) != probe.fields.get(field):
            return classification

    return "sequence_divergence"


def find_resync(
    reference: list[TraceRecord],
    probe: list[TraceRecord],
    ref_index: int,
    probe_index: int,
    window: int,
) -> Optional[dict[str, Any]]:
    if window <= 0:
        return None

    best: Optional[tuple[int, int, int, TraceRecord]] = None
    ref_limit = min(len(reference), ref_index + window + 1)
    probe_limit = min(len(probe), probe_index + window + 1)

    for ri in range(ref_index, ref_limit):
        for pi in range(probe_index, probe_limit):
            if ri == ref_index and pi == probe_index:
                continue
            if reference[ri].canonical != probe[pi].canonical:
                continue
            skipped_ref = ri - ref_index
            skipped_probe = pi - probe_index
            score = skipped_ref + skipped_probe
            candidate = (score, max(skipped_ref, skipped_probe), skipped_ref, reference[ri])
            if best is None or candidate[:3] < best[:3]:
                best = candidate
                best_ri = ri
                best_pi = pi

    if best is None:
        return None

    return {
        "reference_event_index": best_ri,
        "probe_event_index": best_pi,
        "reference_skipped": best_ri - ref_index,
        "probe_skipped": best_pi - probe_index,
        "anchor": reference[best_ri].canonical,
        "reference_source_line": reference[best_ri].source_line,
        "probe_source_line": probe[best_pi].source_line,
    }


def context(records: list[TraceRecord], index: int, radius: int) -> list[dict[str, Any]]:
    if not records:
        return []
    start = max(0, index - radius)
    end = min(len(records), index + radius + 1)
    return [record_public(record) for record in records[start:end] if record is not None]


def compare_streams(reference: TraceStream, probe: TraceStream, config: dict[str, Any]) -> dict[str, Any]:
    ref_records = reference.records
    probe_records = probe.records
    common = min(len(ref_records), len(probe_records))
    mismatch: Optional[int] = None

    for index in range(common):
        if ref_records[index].canonical != probe_records[index].canonical:
            mismatch = index
            break

    if mismatch is None and len(ref_records) == len(probe_records):
        return {
            "schema": 1,
            "tool_version": VERSION,
            "identical": True,
            "reference": {
                "path": reference.path,
                "event_count": len(ref_records),
                "ignored_lines": reference.ignored_lines,
            },
            "probe": {
                "path": probe.path,
                "event_count": len(probe_records),
                "ignored_lines": probe.ignored_lines,
            },
            "first_mismatch": None,
        }

    if mismatch is None:
        mismatch = common

    ref_record = ref_records[mismatch] if mismatch < len(ref_records) else None
    probe_record = probe_records[mismatch] if mismatch < len(probe_records) else None

    if ref_record is None or probe_record is None:
        classification = "trace_length_divergence"
    else:
        classification = classify_pair(ref_record, probe_record)

    resync = None
    if ref_record is not None and probe_record is not None:
        resync = find_resync(
            ref_records,
            probe_records,
            mismatch,
            mismatch,
            config["resync_window"],
        )
        if resync and (
            resync["reference_skipped"] == 0 or resync["probe_skipped"] == 0
        ):
            classification = "sequence_divergence"

    radius = config["context_records"]
    return {
        "schema": 1,
        "tool_version": VERSION,
        "identical": False,
        "reference": {
            "path": reference.path,
            "event_count": len(ref_records),
            "ignored_lines": reference.ignored_lines,
        },
        "probe": {
            "path": probe.path,
            "event_count": len(probe_records),
            "ignored_lines": probe.ignored_lines,
        },
        "first_mismatch": {
            "classification": classification,
            "reference_event_index": mismatch if ref_record is not None else None,
            "probe_event_index": mismatch if probe_record is not None else None,
            "reference": record_public(ref_record),
            "probe": record_public(probe_record),
            "reference_context": context(ref_records, min(mismatch, max(0, len(ref_records) - 1)), radius),
            "probe_context": context(probe_records, min(mismatch, max(0, len(probe_records) - 1)), radius),
            "resynchronization": resync,
        },
    }


def write_json_report(report: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def md_record(record: Optional[dict[str, Any]]) -> str:
    if record is None:
        return "<end-of-trace>"
    return record["canonical"]


def write_markdown_report(report: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# P01-DIVERGENCE-CANDIDATE",
        "",
        f"Tool version: `{report['tool_version']}`",
        "",
    ]

    if report["identical"]:
        lines.extend(
            [
                "Result: **No divergence found in the compared canonical event streams.**",
                "",
                f"Reference events: `{report['reference']['event_count']}`",
                f"Probe events: `{report['probe']['event_count']}`",
            ]
        )
    else:
        mismatch = report["first_mismatch"]
        ref = mismatch["reference"]
        probe = mismatch["probe"]
        lines.extend(
            [
                f"Classification: **`{mismatch['classification']}`**",
                "",
                f"Reference event index: `{mismatch['reference_event_index']}`",
                f"Probe event index: `{mismatch['probe_event_index']}`",
                f"Reference source line: `{ref['source_line'] if ref else None}`",
                f"Probe source line: `{probe['source_line'] if probe else None}`",
                "",
                "## Reference event",
                "",
                "```text",
                md_record(ref),
                "```",
                "",
                "## Probe event",
                "",
                "```text",
                md_record(probe),
                "```",
                "",
            ]
        )
        resync = mismatch.get("resynchronization")
        if resync:
            lines.extend(
                [
                    "## Bounded resynchronization",
                    "",
                    f"Reference skipped: `{resync['reference_skipped']}`",
                    f"Probe skipped: `{resync['probe_skipped']}`",
                    f"Reference anchor index: `{resync['reference_event_index']}`",
                    f"Probe anchor index: `{resync['probe_event_index']}`",
                    "",
                    "```text",
                    resync["anchor"],
                    "```",
                    "",
                ]
            )
        else:
            lines.extend(["## Bounded resynchronization", "", "No anchor found inside the configured window.", ""])

        lines.extend(["## Reference context", ""])
        for item in mismatch["reference_context"]:
            marker = ">" if item["event_index"] == mismatch["reference_event_index"] else " "
            lines.append(f"`{marker} {item['event_index']:06d}` {item['canonical']}")
        lines.extend(["", "## Probe context", ""])
        for item in mismatch["probe_context"]:
            marker = ">" if item["event_index"] == mismatch["probe_event_index"] else " "
            lines.append(f"`{marker} {item['event_index']:06d}` {item['canonical']}")

    lines.extend(
        [
            "",
            "---",
            "",
            "This is an automatically generated candidate report. It is not a confirmed AppleSilicon compatibility divergence until reproduced and reviewed.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def run_normalize(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    stream = parse_file(args.input, config)
    write_normalized(stream, args.output)
    print(f"normalized_events={len(stream.records)}")
    print(f"ignored_lines={stream.ignored_lines}")
    print(f"output={args.output}")
    return 0


def run_compare(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    reference = parse_file(args.reference, config)
    probe = parse_file(args.probe, config)
    write_normalized(reference, args.normalized_reference)
    write_normalized(probe, args.normalized_probe)
    report = compare_streams(reference, probe, config)
    write_json_report(report, args.report_json)
    write_markdown_report(report, args.report_md)

    print(f"reference_events={len(reference.records)}")
    print(f"probe_events={len(probe.records)}")
    print(f"identical={str(report['identical']).lower()}")
    if not report["identical"]:
        print(f"classification={report['first_mismatch']['classification']}")
        print(f"report_md={args.report_md}")
        print(f"report_json={args.report_json}")
        return DIVERGENCE_EXIT
    return 0


def expect(condition: bool, message: str) -> None:
    if not condition:
        raise TraceError(f"self-check failed: {message}")


def self_check(config: dict[str, Any]) -> None:
    reference_lines = [
        "noise before trace\n",
        "719585@1608130130.441188:memory_region_ops_read cpu 0 mr 0x562fdfbb3820 addr 0x000003CC value 0x00000067 size 1 name 'vmapple-cfg'\n",
        "719585@1608130130.441200:memory_region_ops_write cpu 1 mr 0x562fdfbb3990 addr 0x1000 value 0x1 size 4 name 'vmapple-cfg'\n",
        "719585@1608130130.441300:memory_region_ops_read cpu 0 mr 0x562fdfbb4000 addr 0x2000 value 0x2 size 8 name 'vmapple-test'\n",
    ]
    equivalent_lines = [
        "123@999.000001:memory_region_ops_read cpu 0 mr 0xabcdef addr 0x3cc value 0x67 size 1 name 'vmapple-cfg'\n",
        "123@999.000002:memory_region_ops_write cpu 1 mr 0x111111 addr 0x00001000 value 0x0001 size 4 name 'vmapple-cfg'\n",
        "123@999.000003:memory_region_ops_read cpu 0 mr 0x222222 addr 0x00002000 value 0x00000002 size 8 name 'vmapple-test'\n",
    ]
    changed_value_lines = equivalent_lines.copy()
    changed_value_lines[1] = "123@999.000002:memory_region_ops_write cpu 1 mr 0x111111 addr 0x1000 value 0x9 size 4 name 'vmapple-cfg'\n"
    inserted_lines = [equivalent_lines[0], "123@999.0000015:memory_region_ops_read cpu 0 mr 0x333333 addr 0x5555 value 0xaa size 4 name 'inserted'\n", *equivalent_lines[1:]]

    reference = parse_lines(reference_lines, "self-check-reference", config)
    equivalent = parse_lines(equivalent_lines, "self-check-equivalent", config)
    changed = parse_lines(changed_value_lines, "self-check-changed", config)
    inserted = parse_lines(inserted_lines, "self-check-inserted", config)

    expect(len(reference.records) == 3, "reference event extraction count")
    expect(
        [r.canonical for r in reference.records] == [r.canonical for r in equivalent.records],
        "host timestamp, pointer, hex case, and leading-zero noise must normalize away",
    )

    equal_report = compare_streams(reference, equivalent, config)
    expect(equal_report["identical"] is True, "semantically equal traces must compare equal")

    value_report = compare_streams(reference, changed, config)
    expect(value_report["identical"] is False, "changed value must diverge")
    expect(value_report["first_mismatch"]["classification"] == "mmio_value_divergence", "changed value classification")
    expect(value_report["first_mismatch"]["reference_event_index"] == 1, "changed value index")

    insertion_report = compare_streams(reference, inserted, config)
    expect(insertion_report["identical"] is False, "inserted event must diverge")
    expect(insertion_report["first_mismatch"]["classification"] == "sequence_divergence", "insertion classification")
    resync = insertion_report["first_mismatch"]["resynchronization"]
    expect(resync is not None, "insertion must produce bounded resync")
    expect(resync["reference_skipped"] == 0, "insertion reference skip")
    expect(resync["probe_skipped"] == 1, "insertion probe skip")


def run_self_check(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    self_check(config)
    print("P1.08 self-check: PASS")
    print("checks=normalization,value-divergence,bounded-resynchronization")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="AppleSilicon P1.08 VMApple trace normalizer and comparator")
    parser.add_argument("--version", action="version", version=f"AppleSilicon trace comparator {VERSION}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    normalize = subparsers.add_parser("normalize", help="normalize one mixed QEMU/serial trace log")
    normalize.add_argument("input", type=Path)
    normalize.add_argument("--output", type=Path, required=True)
    normalize.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    normalize.set_defaults(func=run_normalize)

    compare = subparsers.add_parser("compare", help="compare reference and probe trace logs")
    compare.add_argument("reference", type=Path)
    compare.add_argument("probe", type=Path)
    compare.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    compare.add_argument("--normalized-reference", type=Path, required=True)
    compare.add_argument("--normalized-probe", type=Path, required=True)
    compare.add_argument("--report-md", type=Path, required=True)
    compare.add_argument("--report-json", type=Path, required=True)
    compare.set_defaults(func=run_compare)

    selfcheck = subparsers.add_parser("self-check", help="run deterministic synthetic P1.08 checks")
    selfcheck.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    selfcheck.set_defaults(func=run_self_check)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return args.func(args)
    except TraceError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return INPUT_ERROR_EXIT
    except OSError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return INPUT_ERROR_EXIT


if __name__ == "__main__":
    raise SystemExit(main())

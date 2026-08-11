#!/usr/bin/env python3
import argparse
import copy
import hashlib
import json
import pathlib
import re
import sys

EXPECTED_VERSION = "3.2.0.0.0.0"
EXPECTED_OBJECTIVE = "P3.03"
EXPECTED_INFERNO_REVISION = "cc4302a99167abec69b714cfd00c38caece7e7de"
EXPECTED_IDS = [
    "gicv3_distributor",
    "gicv3_redistributor",
    "gicv3_cpu_lines",
    "architectural_virtual_timer",
    "pl011_uart",
    "pl031_rtc",
    "pl061_gpio_power",
    "pvpanic_mmio",
]


class ContractError(ValueError):
    pass


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def fail(message):
    raise ContractError(message)


def parse_hex(value, field):
    if not isinstance(value, str) or not re.fullmatch(r"0x[0-9a-fA-F]+", value):
        fail(f"{field}: expected hexadecimal string")
    return int(value, 16)


def canonical_bytes(data):
    return (json.dumps(data, sort_keys=True, separators=(",", ":")) + "\n").encode()


def fingerprint(data):
    return hashlib.sha256(canonical_bytes(data)).hexdigest()


def components_by_id(data):
    comps = data.get("components")
    if not isinstance(comps, list):
        fail("components must be an array")
    ids = [c.get("id") for c in comps if isinstance(c, dict)]
    if ids != EXPECTED_IDS:
        fail(f"component order/identity mismatch: expected {EXPECTED_IDS}")
    if len(ids) != len(set(ids)):
        fail("duplicate component id")
    return {c["id"]: c for c in comps}


def validate(data):
    if data.get("schema") != 1:
        fail("schema must be 1")
    if data.get("project_version") != EXPECTED_VERSION:
        fail("project_version mismatch")
    if data.get("part") != "Part 03" or data.get("objective") != EXPECTED_OBJECTIVE:
        fail("part/objective mismatch")
    if data.get("title") != "Interrupt, Timer, Power and Console Contract":
        fail("title mismatch")

    locks = data.get("source_locks", {})
    inferno = locks.get("inferno", {})
    if inferno.get("revision") != EXPECTED_INFERNO_REVISION:
        fail("Inferno source lock drift")
    if inferno.get("path") != "hw/vmapple/vmapple.c":
        fail("Inferno source path mismatch")
    if inferno.get("blob_sha") != "89c04c09f705d987ee96c11c1f5f4fc79713bf2e":
        fail("Inferno vmapple blob drift")

    xnu = locks.get("xnu_vmapple", {})
    if xnu.get("revision") != "f6217f891ac0bb64f3d375211650a4c1ff8ca1ea":
        fail("XNU source lock drift")
    if xnu.get("blob_sha") != "08b35780a1dcf187af2ced7839d7045afb433de7":
        fail("XNU VMAPPLE blob drift")

    qemu = locks.get("qemu_reference", {})
    if qemu.get("revision") != "84f07211cc5b4fc6a371559bf8a5de4fb068e648":
        fail("QEMU reference revision drift")
    if qemu.get("release") != "11.1.0":
        fail("QEMU reference release mismatch")
    if qemu.get("blob_sha") != "607181f5177b1c798a7504150ce29aa383b29993":
        fail("QEMU VMApple reference blob drift")

    limits = data.get("machine_limits", {})
    if limits != {
        "max_cpus": 32,
        "external_irq_lines": 256,
        "gic_internal_irqs": 32,
        "gic_num_irq_property": 288,
    }:
        fail("machine/GIC limits changed")
    if limits["external_irq_lines"] + limits["gic_internal_irqs"] != limits["gic_num_irq_property"]:
        fail("GIC IRQ accounting mismatch")

    c = components_by_id(data)

    if (parse_hex(c["gicv3_distributor"].get("base"), "gic distributor base"),
            parse_hex(c["gicv3_distributor"].get("size"), "gic distributor size")) != (0x10000000, 0x10000):
        fail("GIC distributor mapping mismatch")
    if c["gicv3_distributor"].get("revision") != 3:
        fail("GIC revision must be 3")

    redist = c["gicv3_redistributor"]
    redist_size = parse_hex(redist.get("size"), "redistributor size")
    stride = parse_hex(redist.get("per_cpu_stride"), "redistributor stride")
    if parse_hex(redist.get("base"), "redistributor base") != 0x10010000:
        fail("GIC redistributor base mismatch")
    if (redist_size, stride, redist.get("capacity_cpus")) != (0x400000, 0x20000, 32):
        fail("GIC redistributor geometry mismatch")
    if redist_size // stride != limits["max_cpus"]:
        fail("redistributor capacity does not match VMApple max CPUs")

    lines = c["gicv3_cpu_lines"]
    if lines.get("gic_outputs") != ["IRQ", "FIQ"] or lines.get("cpu_inputs") != ["ARM_CPU_IRQ", "ARM_CPU_FIQ"] or lines.get("per_cpu") is not True:
        fail("GIC CPU-line wiring mismatch")

    timer = c["architectural_virtual_timer"]
    if timer.get("cpu_output") != "GTIMER_VIRT" or timer.get("ppi") != 27 or timer.get("per_cpu") is not True:
        fail("virtual timer wiring mismatch")

    expected_mmio = {
        "pl011_uart": (0x20010000, 0x10000, 1),
        "pl031_rtc": (0x20050000, 0x1000, 2),
        "pl061_gpio_power": (0x20060000, 0x1000, 5),
        "pvpanic_mmio": (0x20070000, 0x2, None),
    }
    for cid, expected in expected_mmio.items():
        item = c[cid]
        actual = (
            parse_hex(item.get("base"), f"{cid} base"),
            parse_hex(item.get("size"), f"{cid} size"),
            item.get("spi"),
        )
        if actual != expected:
            fail(f"{cid} mapping mismatch")

    if c["pl011_uart"].get("device") != "pl011" or c["pl011_uart"].get("chardev") != "serial_hd(0)":
        fail("PL011 device/console contract mismatch")

    gpio = c["pl061_gpio_power"]
    if (gpio.get("pullups"), gpio.get("pulldowns"), gpio.get("power_gpio_pin"), gpio.get("power_request_input")) != (0, 255, 3, 0):
        fail("PL061 power wiring mismatch")
    if gpio.get("event_semantics") != "unknown_requires_runtime_evidence":
        fail("power GPIO semantics must remain evidence-gated")

    if c["pvpanic_mmio"].get("guest_contract") != "optional_reference_component":
        fail("pvpanic must remain optional")

    for item in c.values():
        if item.get("ownership") != "generic_qemu":
            fail(f"{item['id']}: ownership must remain generic_qemu")
        if item.get("action") not in {"preserve", "validate"}:
            fail(f"{item['id']}: unsupported action")

    rules = data.get("rules", {})
    required_true = [
        "generic_devices_are_preserved_until_evidence_disproves_compatibility",
        "gicv3_and_pl011_are_source_backed_by_xnu_vmapple",
        "virtual_timer_ppi_is_27",
        "redistributor_capacity_must_match_machine_cpu_cap",
        "power_gpio_event_semantics_remain_evidence_gated",
        "pvpanic_is_not_promoted_to_boot_requirement",
        "no_new_inferno_patch_for_p3_03",
        "guest_runtime_deferred",
    ]
    for key in required_true:
        if rules.get(key) is not True:
            fail(f"rule must remain true: {key}")

    if data.get("next_objective") != "P3.04":
        fail("next objective must be P3.04")

    return {
        "classification": "P3_03_CONTRACT_VALID",
        "component_count": len(c),
        "fingerprint": fingerprint(data),
        "runtime_executed": False,
    }


PINNED_SOURCE_SNIPPETS = [
    "#define NUM_IRQS 256",
    "[VMAPPLE_GIC_DIST] =           { 0x10000000, 0x00010000 }",
    "[VMAPPLE_GIC_REDIST] =         { 0x10010000, 0x00400000 }",
    "[VMAPPLE_UART] =               { 0x20010000, 0x00010000 }",
    "[VMAPPLE_RTC] =                { 0x20050000, 0x00001000 }",
    "[VMAPPLE_GPIO] =               { 0x20060000, 0x00001000 }",
    "[VMAPPLE_PVPANIC] =            { 0x20070000, 0x00000002 }",
    "[VMAPPLE_UART] = 1",
    "[VMAPPLE_RTC] = 2",
    "[VMAPPLE_GPIO] = 0x5",
    'qdev_prop_set_uint32(vms->gic, "revision", 3)',
    'qdev_prop_set_uint32(vms->gic, "num-irq", NUM_IRQS + 32)',
    "arm_gic_ppi_index(i, 27)",
    "qdev_connect_gpio_out(cpudev, GTIMER_VIRT",
    "qdev_get_gpio_in(cpudev, ARM_CPU_IRQ)",
    "qdev_get_gpio_in(cpudev, ARM_CPU_FIQ)",
    "DeviceState *dev = qdev_new(TYPE_PL011)",
    'sysbus_create_simple("pl031"',
    'pl061_dev = qdev_new("pl061")',
    'qdev_prop_set_uint32(pl061_dev, "pullups", 0)',
    'qdev_prop_set_uint32(pl061_dev, "pulldowns", 0xff)',
    'sysbus_create_simple("gpio-key", -1',
    "qdev_get_gpio_in(pl061_dev, 3)",
    "vms->pvpanic = qdev_new(TYPE_PVPANIC_MMIO_DEVICE)",
]


def verify_source(data, source_path):
    validate(data)
    source = pathlib.Path(source_path).read_text(encoding="utf-8")
    missing = [s for s in PINNED_SOURCE_SNIPPETS if s not in source]
    if missing:
        fail("pinned VMApple source contract missing: " + " | ".join(missing))
    return {
        "classification": "P3_03_SOURCE_CONTRACT_PASS",
        "checks": len(PINNED_SOURCE_SNIPPETS),
        "runtime_executed": False,
    }


def self_check(data):
    validate(data)
    mutations = []

    def must_fail(label, mutate):
        candidate = copy.deepcopy(data)
        mutate(candidate)
        try:
            validate(candidate)
        except ContractError:
            mutations.append(label)
            return
        fail(f"self-check mutation unexpectedly passed: {label}")

    must_fail("timer_ppi", lambda d: d["components"][3].__setitem__("ppi", 26))
    must_fail("redistributor_capacity", lambda d: d["components"][1].__setitem__("capacity_cpus", 31))
    must_fail("uart_irq", lambda d: d["components"][4].__setitem__("spi", 3))
    must_fail("power_semantics", lambda d: d["components"][6].__setitem__("event_semantics", "assumed_pulse"))
    must_fail("pvpanic_required", lambda d: d["components"][7].__setitem__("guest_contract", "boot_required"))
    must_fail("ownership_rewrite", lambda d: d["components"][5].__setitem__("ownership", "vmapple_specific"))
    must_fail("source_drift", lambda d: d["source_locks"]["inferno"].__setitem__("revision", "deadbeef"))
    must_fail("scope_creep", lambda d: d.__setitem__("next_objective", "P3.07"))

    return {
        "classification": "P3_03_SELF_CHECK_PASS",
        "negative_tests": mutations,
        "count": len(mutations),
    }


def print_json(value):
    print(json.dumps(value, indent=2, sort_keys=True))


def main():
    p = argparse.ArgumentParser(description="Validate the AppleSilicon P3.03 VMApple platform I/O contract")
    p.add_argument("--contract", required=True)
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("validate")
    sub.add_parser("summary")
    sub.add_parser("self-check")
    v = sub.add_parser("verify-source")
    v.add_argument("--source", required=True)

    args = p.parse_args()
    try:
        data = load_json(args.contract)
        if args.command == "validate":
            print_json(validate(data))
        elif args.command == "summary":
            result = validate(data)
            comps = components_by_id(data)
            print_json({
                "classification": "P3_03_SUMMARY",
                "project_version": data["project_version"],
                "components": list(comps),
                "gic_max_cpus": data["machine_limits"]["max_cpus"],
                "virtual_timer_ppi": comps["architectural_virtual_timer"]["ppi"],
                "fingerprint": result["fingerprint"],
                "runtime_executed": False,
            })
        elif args.command == "self-check":
            print_json(self_check(data))
        elif args.command == "verify-source":
            print_json(verify_source(data, args.source))
    except (OSError, json.JSONDecodeError, ContractError) as exc:
        print(f"P3.03 validation failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

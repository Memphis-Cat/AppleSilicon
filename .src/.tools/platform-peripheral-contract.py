#!/usr/bin/env python3
import argparse
import copy
import hashlib
import json
import pathlib
import re
import sys

EXPECTED_VERSION = "3.4.0.0.0.0"
EXPECTED_OBJECTIVE = "P3.05"
EXPECTED_INFERNO_REVISION = "cc4302a99167abec69b714cfd00c38caece7e7de"
EXPECTED_IDS = [
    "pcie_gpex",
    "virtio_transport_defaults",
    "virtio_network",
    "xhci_usb",
    "usb_default_hid",
    "vmapple_aes_mmio",
    "vmapple_aes_semantics",
    "vmapple_aes_reset",
    "apple_pvg_mmio",
    "apple_pvg_optionalization",
    "modern_vmapple_graphics_status",
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
    if data.get("title") != "PCIe, Peripheral, Crypto and Graphics Contract":
        fail("title mismatch")

    scope = data.get("scope", {})
    if scope.get("machine") != "vmapple":
        fail("machine scope mismatch")
    if scope.get("cpu_contract_owner") != "Part 02":
        fail("CPU ownership must remain Part 02")
    if scope.get("guest_runtime_deferred") is not True:
        fail("guest runtime must remain deferred")
    if scope.get("inferno_source_patch_required") is not False:
        fail("P3.05 must not claim a new Inferno patch is required")

    locks = data.get("source_locks", {})
    inferno = locks.get("inferno", {})
    if inferno.get("revision") != EXPECTED_INFERNO_REVISION:
        fail("Inferno source lock drift")
    expected_inferno = {
        "hw/vmapple/vmapple.c": "89c04c09f705d987ee96c11c1f5f4fc79713bf2e",
        "hw/vmapple/Kconfig": "2382b297672274f27c447b9168cab9425f01ed17",
        "hw/vmapple/aes.c": "3f6c2721bf3d8d46cc21323ef6d2492e28a7020b",
        "hw/usb/hcd-xhci-pci.c": "b93c80b09d8237a1d2a5df0f5c7262fd1a292324",
    }
    if inferno.get("files") != expected_inferno:
        fail("Inferno file locks drifted")

    project_patch = locks.get("project", {}).get("optional_pvg_patch", {})
    if project_patch != {
        "path": ".src/.patches/0002-vmapple-optional-apple-pvg.patch",
        "blob_sha": "04ac7e35c8c15bc6c2d7ef5b1cbc76f0c4875ecd",
    }:
        fail("P1.05 optional-PVG patch lock drifted")

    qemu = locks.get("qemu_reference", {})
    if qemu.get("revision") != "84f07211cc5b4fc6a371559bf8a5de4fb068e648":
        fail("QEMU reference revision drift")
    if qemu.get("release") != "11.1.0":
        fail("QEMU reference release mismatch")
    expected_qemu = {
        "hw/vmapple/vmapple.c": "607181f5177b1c798a7504150ce29aa383b29993",
        "hw/vmapple/Kconfig": "2382b297672274f27c447b9168cab9425f01ed17",
        "hw/vmapple/aes.c": "553e688adbe7e2636b9514c27a2b180af5cc66e5",
        "hw/usb/hcd-xhci-pci.c": "b124251ae3375bf3f6219f920e1d9305b4bc9427",
        "hw/display/apple-gfx-mmio.m": "58beaadd1f108baa9cd0b500cd26c3281f416c4e",
        "hw/display/meson.build": "ffecedbf709e0a1f34e0325755bd0978636a9cef",
        "meson.build": "49a5baf5b52fd257001b81d4212a129a0315cd11",
        "configs/devices/aarch64-softmmu/default.mak": "ad8028cfd482b948a3edc031f40551e0a8b9be00",
        "docs/system/arm/vmapple.rst": "35c329ea5a812ea27b8ea1e6690576a85b8e30d1",
    }
    if qemu.get("files") != expected_qemu:
        fail("QEMU reference file locks drifted")

    c = components_by_id(data)

    pcie = c["pcie_gpex"]
    pcie_values = (
        parse_hex(pcie.get("ecam_base"), "PCIe ECAM base"),
        parse_hex(pcie.get("ecam_size"), "PCIe ECAM size"),
        parse_hex(pcie.get("mmio_base"), "PCIe MMIO base"),
        parse_hex(pcie.get("mmio_size"), "PCIe MMIO size"),
        pcie.get("num_irqs"), pcie.get("spi_base"), pcie.get("spi_last"),
    )
    if pcie_values != (0x40000000, 0x10000000, 0x50000000, 0x1FFF0000, 16, 32, 47):
        fail("GPEX PCIe geometry/IRQ contract mismatch")
    if pcie.get("ownership") != "generic_qemu" or pcie.get("device") != "gpex-pcihost":
        fail("GPEX ownership/device mismatch")
    if pcie["spi_base"] + pcie["num_irqs"] - 1 != pcie["spi_last"]:
        fail("GPEX IRQ range arithmetic mismatch")

    virtio = c["virtio_transport_defaults"]
    if virtio.get("ownership") != "generic_qemu" or virtio.get("disable_legacy") is not True:
        fail("VMApple virtio transport must keep disable-legacy=on")

    net = c["virtio_network"]
    if net.get("ownership") != "generic_qemu" or net.get("device") != "virtio-net-pci":
        fail("virtio network contract mismatch")
    if net.get("guest_contract") != "optional_reference_component":
        fail("networking must remain optional")

    xhci = c["xhci_usb"]
    if xhci.get("ownership") != "generic_qemu" or xhci.get("device") != "qemu-xhci":
        fail("XHCI device contract mismatch")
    if xhci.get("created_when_defaults_enabled") is not True:
        fail("XHCI default-device gate mismatch")
    if (xhci.get("msi_default"), xhci.get("msix_default")) != ("auto", "auto"):
        fail("XHCI MSI/MSI-X defaults changed")
    if xhci.get("conditional_intr_mapping") is not True:
        fail("VMApple macOS XHCI conditional interrupt mapping must remain enabled")
    if xhci.get("pin_irq_event_target") != "interrupter_0_when_msi_and_msix_inactive":
        fail("XHCI pin-IRQ compatibility behavior mismatch")

    hid = c["usb_default_hid"]
    if hid.get("ownership") != "generic_qemu" or hid.get("devices") != ["usb-kbd", "usb-tablet"]:
        fail("default USB HID contract mismatch")
    if hid.get("created_when_defaults_enabled") is not True:
        fail("default HID creation gate mismatch")

    aes_mmio = c["vmapple_aes_mmio"]
    aes_geometry = (
        parse_hex(aes_mmio.get("mmio1_base"), "AES MMIO1 base"),
        parse_hex(aes_mmio.get("mmio1_size"), "AES MMIO1 size"),
        parse_hex(aes_mmio.get("mmio2_base"), "AES MMIO2 base"),
        parse_hex(aes_mmio.get("mmio2_size"), "AES MMIO2 size"),
        aes_mmio.get("spi"), aes_mmio.get("implemented_access_bytes"),
    )
    if aes_geometry != (0x30220000, 0x4000, 0x30230000, 0x4000, 18, 4):
        fail("AES MMIO/IRQ contract mismatch")
    if aes_mmio.get("ownership") != "vmapple_specific":
        fail("AES ownership mismatch")

    aes = c["vmapple_aes_semantics"]
    if aes.get("implemented_commands") != ["KEY", "IV", "DATA", "STORE_IV", "FLAG"]:
        fail("AES implemented command set drifted")
    if aes.get("declared_but_unimplemented_commands") != ["DSB", "SKG", "WRITE_REG"]:
        fail("AES unresolved command set drifted")
    if aes.get("cipher_modes") != ["ECB", "CBC"] or aes.get("aes_key_bits") != [128, 192, 256]:
        fail("AES public cipher capability contract drifted")
    if aes.get("builtin_key_indices") != [1, 2, 3]:
        fail("AES builtin key index contract drifted")
    if aes.get("builtin_key_classification") != "public_emulator_placeholders_not_authentic_apple_secrets":
        fail("AES builtin constants must not be classified as authentic Apple secrets")
    if aes.get("runtime_requirement_of_unimplemented_commands") != "unknown_requires_runtime_evidence":
        fail("unimplemented AES commands must remain evidence-gated")

    reset = c["vmapple_aes_reset"]
    if parse_hex(reset.get("status"), "AES reset status") != 0x3F80:
        fail("AES reset status mismatch")
    if (reset.get("queue_status"), reset.get("irq_status"), reset.get("irq_enable"), reset.get("watermark")) != (2, 0, 0, 0):
        fail("AES reset state mismatch")

    pvg = c["apple_pvg_mmio"]
    pvg_geometry = (
        parse_hex(pvg.get("gfx_base"), "PVG gfx base"),
        parse_hex(pvg.get("gfx_size"), "PVG gfx size"),
        parse_hex(pvg.get("iosfc_base"), "PVG IOSFC base"),
        parse_hex(pvg.get("iosfc_size"), "PVG IOSFC size"),
        pvg.get("iosfc_spi"), pvg.get("gfx_spi"),
    )
    if pvg_geometry != (0x30200000, 0x10000, 0x30210000, 0x10000, 16, 17):
        fail("Apple PVG MMIO/IRQ contract mismatch")
    if pvg.get("ownership") != "host_framework_dependent" or pvg.get("device") != "apple-gfx-mmio":
        fail("Apple PVG ownership/device mismatch")
    if pvg.get("host_dependencies") != ["ParavirtualizedGraphics.framework", "Metal.framework"]:
        fail("Apple PVG host dependency contract mismatch")

    optional = c["apple_pvg_optionalization"]
    if optional.get("construction") != "qdev_try_new":
        fail("P1.05 PVG optionalization must use qdev_try_new")
    if optional.get("when_unavailable") != "warn_and_continue_without_pvg":
        fail("P1.05 PVG absence policy mismatch")
    if optional.get("fake_gpu_allowed") is not False:
        fail("fake GPU substitution is forbidden")

    modern = c["modern_vmapple_graphics_status"]
    if modern.get("ownership") != "unknown_requires_evidence":
        fail("modern graphics status ownership mismatch")
    if modern.get("qemu_issue") != 2913 or modern.get("qemu_issue_status") != "to_do":
        fail("QEMU modern VMApple graphics issue tracking drifted")
    if modern.get("official_documented_guest_support") != "macOS_12_only":
        fail("official VMApple guest-support boundary changed")
    if modern.get("aarch64_default_build") != "CONFIG_VMAPPLE=n":
        fail("QEMU aarch64 default VMApple build state changed")

    allowed_actions = {"preserve", "validate", "investigate", "defer"}
    for cid, item in c.items():
        if item.get("action") not in allowed_actions:
            fail(f"{cid}: unsupported action")

    rules = data.get("rules", {})
    required_true = [
        "generic_pcie_and_peripherals_are_preserved_until_evidence_disproves_compatibility",
        "vmapple_virtio_transport_disables_legacy_mode",
        "xhci_conditional_interrupt_mapping_must_remain_enabled",
        "xhci_without_msi_or_msix_must_target_interrupter_zero_under_the_compatibility_policy",
        "aes_declared_but_unimplemented_commands_are_not_invented",
        "aes_builtin_constants_are_not_treated_as_real_apple_keys",
        "apple_pvg_remains_host_framework_dependent",
        "p1_05_optional_pvg_behavior_is_preserved",
        "no_fake_gpu_is_introduced",
        "modern_macos_graphics_compatibility_is_not_claimed",
        "no_new_inferno_patch_for_p3_05",
        "guest_runtime_deferred",
    ]
    for key in required_true:
        if rules.get(key) is not True:
            fail(f"rule must remain true: {key}")

    if data.get("next_objective") != "P3.06":
        fail("next objective must be P3.06")

    return {
        "classification": "P3_05_CONTRACT_VALID",
        "component_count": len(c),
        "fingerprint": fingerprint(data),
        "runtime_executed": False,
        "new_patch_required": False,
    }


VMAPPLE_REQUIRED = [
    "[VMAPPLE_APV_GFX] =            { 0x30200000, 0x00010000 }",
    "[VMAPPLE_APV_IOSFC] =          { 0x30210000, 0x00010000 }",
    "[VMAPPLE_AES_1] =              { 0x30220000, 0x00004000 }",
    "[VMAPPLE_AES_2] =              { 0x30230000, 0x00004000 }",
    "[VMAPPLE_PCIE_ECAM] =          { 0x40000000, 0x10000000 }",
    "[VMAPPLE_PCIE_MMIO] =          { 0x50000000, 0x1fff0000 }",
    "[VMAPPLE_APV_IOSFC] = 0x10",
    "[VMAPPLE_APV_GFX] = 0x11",
    "[VMAPPLE_AES_1] = 0x12",
    "[VMAPPLE_PCIE] = 0x20",
    "#define GPEX_NUM_IRQS 16",
    "qdev_new(TYPE_GPEX_HOST)",
    'qdev_prop_set_uint32(dev, "num-irqs", GPEX_NUM_IRQS)',
    'memory_region_init_alias(&vms->ecam_alias, OBJECT(dev), "pcie-ecam"',
    'memory_region_init_alias(mmio_alias, OBJECT(dev), "pcie-mmio"',
    'qemu_create_nic_device("virtio-net-pci", true, NULL)',
    "usb_controller = qdev_new(TYPE_QEMU_XHCI)",
    'usb_create_simple(usb_bus, "usb-kbd")',
    'usb_create_simple(usb_bus, "usb-tablet")',
    '{ TYPE_VIRTIO_PCI, "disable-legacy", "on" }',
    '{ TYPE_XHCI_PCI, "conditional-intr-mapping", "on" }',
    "qdev_new(TYPE_VMAPPLE_AES)",
    'qdev_new("apple-gfx-mmio")',
]

AES_REQUIRED = [
    "#define CMD_KEY           0x1",
    "#define CMD_IV            0x2",
    "#define CMD_DSB           0x3",
    "#define CMD_SKG           0x4",
    "#define CMD_DATA          0x5",
    "#define CMD_STORE_IV      0x6",
    "#define CMD_WRITE_REG     0x7",
    "#define CMD_FLAG          0x8",
    "case CMD_KEY:",
    "case CMD_IV:",
    "case CMD_DATA:",
    "case CMD_STORE_IV:",
    "case CMD_FLAG:",
    "QCRYPTO_CIPHER_MODE_ECB",
    "QCRYPTO_CIPHER_MODE_CBC",
    "QCRYPTO_CIPHER_ALGO_AES_128",
    "QCRYPTO_CIPHER_ALGO_AES_192",
    "QCRYPTO_CIPHER_ALGO_AES_256",
    "s->status = 0x3f80",
    "s->q_status = 2",
    "TYPE_VMAPPLE_AES, 0x4000",
]

XHCI_REQUIRED = [
    "static bool xhci_pci_intr_mapping_conditional",
    "return msix_enabled(pci_dev) || msi_enabled(pci_dev)",
    'DEFINE_PROP_BOOL("conditional-intr-mapping"',
    'DEFINE_PROP_ON_OFF_AUTO("msi"',
    'DEFINE_PROP_ON_OFF_AUTO("msix"',
]

PATCH_REQUIRED = [
    'qdev_try_new("apple-gfx-mmio")',
    'warn_report("VMApple: apple-gfx-mmio unavailable; continuing without Apple PVG")',
    "return;",
]


def require_snippets(label, text, snippets):
    missing = [s for s in snippets if s not in text]
    if missing:
        fail(f"{label} missing source contract: " + " | ".join(missing))


def verify_source(data, vmapple_path, aes_path, xhci_path, patch_path):
    validate(data)
    vmapple = pathlib.Path(vmapple_path).read_text(encoding="utf-8")
    aes = pathlib.Path(aes_path).read_text(encoding="utf-8")
    xhci = pathlib.Path(xhci_path).read_text(encoding="utf-8")
    patch = pathlib.Path(patch_path).read_text(encoding="utf-8")

    require_snippets("vmapple.c", vmapple, VMAPPLE_REQUIRED)
    require_snippets("aes.c", aes, AES_REQUIRED)
    require_snippets("hcd-xhci-pci.c", xhci, XHCI_REQUIRED)
    require_snippets("P1.05 patch", patch, PATCH_REQUIRED)

    for unsupported_case in ("case CMD_DSB:", "case CMD_SKG:", "case CMD_WRITE_REG:"):
        if unsupported_case in aes:
            fail(f"AES command unexpectedly became implemented: {unsupported_case}")

    return {
        "classification": "P3_05_SOURCE_CONTRACT_PASS",
        "vmapple_checks": len(VMAPPLE_REQUIRED),
        "aes_checks": len(AES_REQUIRED),
        "xhci_checks": len(XHCI_REQUIRED),
        "pvg_patch_checks": len(PATCH_REQUIRED),
        "runtime_executed": False,
    }


def self_check(data):
    validate(data)
    passed = []

    def must_fail(label, mutate):
        candidate = copy.deepcopy(data)
        mutate(candidate)
        try:
            validate(candidate)
        except ContractError:
            passed.append(label)
            return
        fail(f"self-check mutation unexpectedly passed: {label}")

    must_fail("pcie_irq_count", lambda d: d["components"][0].__setitem__("num_irqs", 15))
    must_fail("legacy_virtio", lambda d: d["components"][1].__setitem__("disable_legacy", False))
    must_fail("xhci_workaround", lambda d: d["components"][3].__setitem__("conditional_intr_mapping", False))
    must_fail("aes_fake_command", lambda d: d["components"][6].__setitem__("declared_but_unimplemented_commands", ["DSB", "SKG"]))
    must_fail("aes_real_keys_claim", lambda d: d["components"][6].__setitem__("builtin_key_classification", "authentic_apple_keys"))
    must_fail("pvg_fake_gpu", lambda d: d["components"][9].__setitem__("fake_gpu_allowed", True))
    must_fail("modern_graphics_claim", lambda d: d["components"][10].__setitem__("official_documented_guest_support", "macOS_15"))
    must_fail("source_drift", lambda d: d["source_locks"]["inferno"].__setitem__("revision", "deadbeef"))
    must_fail("scope_creep", lambda d: d.__setitem__("next_objective", "P3.07"))

    return {
        "classification": "P3_05_SELF_CHECK_PASS",
        "negative_tests": passed,
        "count": len(passed),
    }


def print_json(value):
    print(json.dumps(value, indent=2, sort_keys=True))


def main():
    parser = argparse.ArgumentParser(description="Validate the AppleSilicon P3.05 VMApple peripheral/crypto/graphics contract")
    parser.add_argument("--contract", required=True)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("validate")
    sub.add_parser("summary")
    sub.add_parser("self-check")
    src = sub.add_parser("verify-source")
    src.add_argument("--vmapple", required=True)
    src.add_argument("--aes", required=True)
    src.add_argument("--xhci", required=True)
    src.add_argument("--pvg-patch", required=True)

    args = parser.parse_args()
    try:
        data = load_json(args.contract)
        if args.command == "validate":
            print_json(validate(data))
        elif args.command == "self-check":
            print_json(self_check(data))
        elif args.command == "summary":
            result = validate(data)
            c = components_by_id(data)
            print_json({
                "classification": "P3_05_SUMMARY",
                "project_version": data["project_version"],
                "pcie_irq_range": [c["pcie_gpex"]["spi_base"], c["pcie_gpex"]["spi_last"]],
                "xhci_conditional_intr_mapping": c["xhci_usb"]["conditional_intr_mapping"],
                "aes_implemented_commands": c["vmapple_aes_semantics"]["implemented_commands"],
                "aes_unimplemented_commands": c["vmapple_aes_semantics"]["declared_but_unimplemented_commands"],
                "pvg_policy": c["apple_pvg_optionalization"]["when_unavailable"],
                "modern_graphics_status": c["modern_vmapple_graphics_status"]["qemu_issue_status"],
                "fingerprint": result["fingerprint"],
                "runtime_executed": False,
                "new_patch_required": False,
            })
        elif args.command == "verify-source":
            print_json(verify_source(data, args.vmapple, args.aes, args.xhci, args.pvg_patch))
    except (OSError, json.JSONDecodeError, ContractError) as exc:
        print(f"P3.05 validation failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
import argparse
import copy
import hashlib
import json
import pathlib
import re
import sys

EXPECTED_VERSION = "3.3.0.0.0.0"
EXPECTED_OBJECTIVE = "P3.04"
EXPECTED_INFERNO_REVISION = "cc4302a99167abec69b714cfd00c38caece7e7de"
EXPECTED_IDS = [
    "bdif_mmio",
    "bdif_device_selectors",
    "bdif_registers",
    "bdif_dma_request",
    "bdif_command_semantics",
    "storage_backend_topology",
    "vmapple_virtio_blk_pci_identity",
    "vmapple_virtio_blk_variant",
    "vmapple_virtio_blk_config_type",
    "vmapple_virtio_blk_barrier",
    "aux_image_input_contract",
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
    if data.get("title") != "Boot Backdoor and Storage Contract":
        fail("title mismatch")

    scope = data.get("scope", {})
    if scope.get("machine") != "vmapple":
        fail("machine scope mismatch")
    if scope.get("cpu_contract_owner") != "Part 02":
        fail("CPU ownership must remain Part 02")
    if scope.get("guest_runtime_deferred") is not True:
        fail("guest runtime must remain deferred")
    if scope.get("inferno_source_patch_required") is not False:
        fail("P3.04 must not claim an Inferno patch is required")

    locks = data.get("source_locks", {})
    inferno = locks.get("inferno", {})
    if inferno.get("revision") != EXPECTED_INFERNO_REVISION:
        fail("Inferno source lock drift")
    expected_inferno_files = {
        "hw/vmapple/vmapple.c": "89c04c09f705d987ee96c11c1f5f4fc79713bf2e",
        "hw/vmapple/bdif.c": "5ccd374581969c0e8c70714fbd82aa0bdb0e189f",
        "hw/vmapple/virtio-blk.c": "5d990e63079714b0fc6deea0caf588f2be6a9241",
    }
    if inferno.get("files") != expected_inferno_files:
        fail("Inferno file locks drifted")

    qemu = locks.get("qemu_reference", {})
    if qemu.get("revision") != "84f07211cc5b4fc6a371559bf8a5de4fb068e648":
        fail("QEMU reference revision drift")
    if qemu.get("release") != "11.1.0":
        fail("QEMU reference release mismatch")
    expected_qemu_files = {
        "hw/vmapple/vmapple.c": "607181f5177b1c798a7504150ce29aa383b29993",
        "hw/vmapple/bdif.c": "4dc10c151d28245b07df2110b892534fda2471d6",
        "hw/vmapple/virtio-blk.c": "9de9aaae0bfc743b25edb30e88f4ebe0c6fdbcfa",
        "docs/system/arm/vmapple.rst": "35c329ea5a812ea27b8ea1e6690576a85b8e30d1",
        "include/hw/pci/pci_ids.h": "16034aaa2c7e4ff8ff881a5f1b380f7d9016b5d4",
        "qapi/virtio.json": "1fc4e38a44da0040fa53216d6bd3b899730b817e",
    }
    if qemu.get("files") != expected_qemu_files:
        fail("QEMU reference file locks drifted")

    c = components_by_id(data)

    bdif = c["bdif_mmio"]
    if (parse_hex(bdif.get("base"), "BDIF base"), parse_hex(bdif.get("size"), "BDIF size"), bdif.get("irq")) != (0x30000000, 0x200000, None):
        fail("BDIF MMIO mapping mismatch")

    selectors = c["bdif_device_selectors"]
    expected_selectors = {
        "device_id_mask": 0xFFFF0000,
        "root": 0x00000000,
        "aux": 0x00010000,
        "usb": 0x00100000,
    }
    for key, expected in expected_selectors.items():
        if parse_hex(selectors.get(key), f"BDIF selector {key}") != expected:
            fail(f"BDIF selector mismatch: {key}")
    if selectors.get("command_serviced") != ["root", "aux"]:
        fail("only root and AUX BDIF commands are source-backed")
    if selectors.get("usb_state") != "declared_but_not_serviced_by_command_handler":
        fail("BDIF USB selector must remain declared-only")

    regs = c["bdif_registers"]
    expected_reads = {
        "status": (0x000, 0x1),
        "cfg": (0x004, 0x2),
        "unk1": (0x008, 0x420),
        "busy": (0x010, 0x1),
        "unk2": (0x400, 0x1),
        "unk3": (0x434, 0x0),
    }
    for name, (offset, value) in expected_reads.items():
        entry = regs.get(name, {})
        if parse_hex(entry.get("offset"), f"{name} offset") != offset or parse_hex(entry.get("read_value"), f"{name} read value") != value:
            fail(f"BDIF register mismatch: {name}")
    cmd = regs.get("command", {})
    if parse_hex(cmd.get("offset"), "BDIF command offset") != 0x408:
        fail("BDIF command register offset mismatch")
    if cmd.get("write_value_semantics") != "guest_physical_address_of_vblk_request":
        fail("BDIF command write semantics drift")
    nxt = regs.get("next_device", {})
    if parse_hex(nxt.get("offset"), "next-device offset") != 0x420:
        fail("BDIF next-device offset mismatch")
    if parse_hex(nxt.get("root_read_value"), "root next-device value") != 0x08000000:
        fail("BDIF root next-device value mismatch")
    if parse_hex(nxt.get("aux_read_value"), "AUX next-device value") != 0x00010000:
        fail("BDIF AUX next-device value mismatch")
    if nxt.get("semantic_name") != "opaque_reference_value":
        fail("unknown BDIF next-device semantics must remain opaque")

    dma = c["bdif_dma_request"]
    if dma.get("sector_bytes") != 512:
        fail("BDIF sector size mismatch")
    if (dma.get("sector_struct_bytes"), dma.get("request_command_bytes"), dma.get("request_bytes")) != (16, 16, 48):
        fail("BDIF request geometry mismatch")
    if dma.get("max_data_bytes") != 128 * 1024 * 1024:
        fail("BDIF maximum request size mismatch")
    if parse_hex(dma.get("read_flags"), "BDIF read flags") != 0x00030001:
        fail("BDIF read flags mismatch")
    if parse_hex(dma.get("write_flags"), "BDIF write flags") != 0x00010001:
        fail("BDIF write flags mismatch")
    if (dma.get("success_value"), dma.get("failure_value"), dma.get("completion_bytes")) != (0, 1, 1):
        fail("BDIF completion contract mismatch")
    if dma.get("field_endianness") != "little_endian_to_cpu":
        fail("BDIF request field endianness mismatch")

    semantics = c["bdif_command_semantics"]
    if semantics.get("read_supported") is not True:
        fail("BDIF read path must remain supported")
    if semantics.get("write_supported") is not False:
        fail("BDIF write support must not be invented")
    if semantics.get("write_behavior") != "recognized_but_returns_failure":
        fail("BDIF write behavior mismatch")
    if semantics.get("sector_offset_formula") != "sector*512+static_offset" or semantics.get("static_offset") != 0:
        fail("BDIF sector offset semantics mismatch")
    if semantics.get("read_destination") != "guest_dma_buffer" or semantics.get("completion_destination") != "guest_retval_address":
        fail("BDIF DMA destination semantics mismatch")
    if semantics.get("runtime_write_requirement") != "unknown_requires_runtime_evidence":
        fail("BDIF write requirement must remain evidence-gated")

    topology = c["storage_backend_topology"]
    expected_topology = {
        "bdif_aux_backend": "IF_PFLASH unit 0 required",
        "bdif_root_backend_preferred": "IF_PFLASH unit 1",
        "bdif_root_backend_fallback": "IF_VIRTIO unit 0",
        "runtime_aux_backend": "if=none drive attached to vmapple-virtio-blk-pci variant=aux",
        "runtime_root_backend": "if=none drive attached to vmapple-virtio-blk-pci variant=root",
    }
    for key, expected in expected_topology.items():
        if topology.get(key) != expected:
            fail(f"storage backend topology mismatch: {key}")
    if topology.get("reference_cli_duplicates_aux_and_root_files_between_preboot_and_runtime_backends") is not True:
        fail("reference backend duplication contract changed")

    identity = c["vmapple_virtio_blk_pci_identity"]
    if identity.get("device") != "vmapple-virtio-blk-pci":
        fail("VMApple virtio-blk device type mismatch")
    if parse_hex(identity.get("pci_vendor_id"), "Apple PCI vendor ID") != 0x106B:
        fail("Apple PCI vendor ID mismatch")
    if parse_hex(identity.get("pci_device_id"), "Apple virtio-blk PCI device ID") != 0x1A00:
        fail("Apple virtio-blk PCI device ID mismatch")
    if identity.get("pci_class") != "PCI_CLASS_STORAGE_SCSI":
        fail("Apple virtio-blk PCI class mismatch")

    variant = c["vmapple_virtio_blk_variant"]
    if variant.get("enum_order") != ["unspecified", "root", "aux"]:
        fail("VMApple virtio-blk variant enum drift")
    if variant.get("valid_runtime_variants") != ["root", "aux"]:
        fail("VMApple virtio-blk runtime variants drift")
    if variant.get("unspecified_behavior") != "device_realization_error":
        fail("unspecified variant must fail realization")

    config_type = c["vmapple_virtio_blk_config_type"]
    if config_type.get("source_field") != "virtio_blk_config.max_secure_erase_sectors":
        fail("Apple type config field mismatch")
    if config_type.get("stored_value") != "apple_type_variant" or config_type.get("store_helper") != "stl_he_p":
        fail("Apple type config write mismatch")
    if config_type.get("config_size_mechanism") != "VIRTIO_BLK_F_ZONED":
        fail("VMApple virtio-blk config-size mechanism mismatch")
    if config_type.get("zoned_semantics") != "not_implemented_config_space_size_only_guest_expected_to_ignore":
        fail("zoned feature must not be promoted to zoned-storage support")

    barrier = c["vmapple_virtio_blk_barrier"]
    if parse_hex(barrier.get("request_type"), "Apple barrier opcode") != 0x10000:
        fail("Apple barrier opcode mismatch")
    if barrier.get("implementation") != "successful_no_op" or barrier.get("completion") != "VIRTIO_BLK_S_OK":
        fail("Apple barrier completion semantics mismatch")
    if barrier.get("diagnostic") != "LOG_UNIMP":
        fail("Apple barrier diagnostic contract mismatch")
    if barrier.get("flush_semantics") != "unknown_requires_runtime_evidence":
        fail("Apple barrier flush semantics must remain evidence-gated")

    aux = c["aux_image_input_contract"]
    if (aux.get("official_reference_trim_block_bytes"), aux.get("official_reference_trim_blocks_skipped"), aux.get("trimmed_bytes")) != (0x4000, 1, 0x4000):
        fail("AUX reference trim contract mismatch")
    if aux.get("artifact_policy") != "local_external_input_not_committed":
        fail("AUX artifact policy mismatch")

    for cid, item in c.items():
        if item.get("action") not in {"validate", "defer"}:
            fail(f"{cid}: unsupported action")
        if cid != "aux_image_input_contract" and item.get("ownership") != "vmapple_specific":
            fail(f"{cid}: ownership must remain vmapple_specific")
    if c["aux_image_input_contract"].get("ownership") != "unknown_requires_evidence":
        fail("AUX input preparation ownership mismatch")

    rules = data.get("rules", {})
    required_true = [
        "bdif_and_vmapple_virtio_blk_are_distinct_boot_phases",
        "bdif_remains_read_only_until_runtime_evidence_requires_write_support",
        "bdif_usb_selector_is_not_promoted_to_supported_storage",
        "reference_backend_duplication_is_preserved",
        "virtio_variant_unspecified_must_fail_realization",
        "apple_pci_identity_is_preserved",
        "apple_barrier_remains_no_op_until_evidence_requires_flush_semantics",
        "zoned_feature_is_not_promoted_to_real_zoned_storage_support",
        "no_proprietary_storage_or_firmware_artifacts_in_repo",
        "no_new_inferno_patch_for_p3_04",
        "guest_runtime_deferred",
    ]
    for key in required_true:
        if rules.get(key) is not True:
            fail(f"rule must remain true: {key}")

    if data.get("next_objective") != "P3.05":
        fail("next objective must be P3.05")

    return {
        "classification": "P3_04_CONTRACT_VALID",
        "component_count": len(c),
        "fingerprint": fingerprint(data),
        "runtime_executed": False,
    }


PINNED_VMAPPLE_SNIPPETS = [
    "[VMAPPLE_BDOOR] =              { 0x30000000, 0x00200000 }",
    "DriveInfo *di_aux = drive_get(IF_PFLASH, 0, 0);",
    "DriveInfo *di_root = drive_get(IF_PFLASH, 0, 1);",
    "di_root = drive_get(IF_VIRTIO, 0, 0);",
    'qdev_prop_set_drive(DEVICE(bdif), "aux", blk_by_legacy_dinfo(di_aux));',
    'qdev_prop_set_drive(DEVICE(bdif), "root", blk_by_legacy_dinfo(di_root));',
]

PINNED_BDIF_SNIPPETS = [
    "#define VMAPPLE_BDIF_SIZE   0x00200000",
    "#define REG_DEVID_MASK      0xffff0000",
    "#define DEVID_ROOT          0x00000000",
    "#define DEVID_AUX           0x00010000",
    "#define DEVID_USB           0x00100000",
    "#define REG_CMD             0x408",
    "#define REG_NEXT_DEVICE     0x420",
    "#define VBLK_DATA_FLAGS_READ  0x00030001",
    "#define VBLK_DATA_FLAGS_WRITE 0x00010001",
    "off = sector.sector * 512ULL + static_off;",
    "if (req.data.len > 128 * MiB)",
    "case VBLK_DATA_FLAGS_READ:",
    "case VBLK_DATA_FLAGS_WRITE:",
    "/* Not needed, iBoot only reads */",
    "dma_memory_write(&address_space_memory, req.retval.addr, &ret, 1",
]

PINNED_VIRTIO_SNIPPETS = [
    "#define VIRTIO_BLK_T_APPLE_BARRIER     0x10000",
    'qemu_log_mask(LOG_UNIMP, "%s: Barrier requests are currently no-ops',
    "virtio_blk_req_complete(req, VIRTIO_BLK_S_OK);",
    "stl_he_p(&blkcfg->max_secure_erase_sectors, dev->apple_type);",
    "VM_APPLE_VIRTIO_BLK_VARIANT_UNSPECIFIED",
    "Variant property must be set to 'aux' or 'root'.",
    "virtio_add_feature(&dev->vdev.parent_obj.host_features, VIRTIO_BLK_F_ZONED);",
    "pci_config_set_vendor_id(vpci_dev->pci_dev.config, PCI_VENDOR_ID_APPLE);",
    "PCI_DEVICE_ID_APPLE_VIRTIO_BLK",
    "pcidev_k->class_id = PCI_CLASS_STORAGE_SCSI;",
]


def verify_source(data, vmapple_path, bdif_path, virtio_path):
    validate(data)
    files = {
        "vmapple": (pathlib.Path(vmapple_path), PINNED_VMAPPLE_SNIPPETS),
        "bdif": (pathlib.Path(bdif_path), PINNED_BDIF_SNIPPETS),
        "virtio-blk": (pathlib.Path(virtio_path), PINNED_VIRTIO_SNIPPETS),
    }
    total = 0
    for label, (path, snippets) in files.items():
        source = path.read_text(encoding="utf-8")
        missing = [s for s in snippets if s not in source]
        if missing:
            fail(f"{label} source contract missing: " + " | ".join(missing))
        total += len(snippets)
    return {
        "classification": "P3_04_SOURCE_CONTRACT_PASS",
        "checks": total,
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

    must_fail("bdif_base", lambda d: d["components"][0].__setitem__("base", "0x30010000"))
    must_fail("usb_promoted", lambda d: d["components"][1].__setitem__("command_serviced", ["root", "aux", "usb"]))
    must_fail("bdif_write_support", lambda d: d["components"][4].__setitem__("write_supported", True))
    must_fail("backend_topology", lambda d: d["components"][5].__setitem__("bdif_aux_backend", "if=none"))
    must_fail("pci_vendor", lambda d: d["components"][6].__setitem__("pci_vendor_id", "0x1af4"))
    must_fail("variant_order", lambda d: d["components"][7].__setitem__("enum_order", ["unspecified", "aux", "root"]))
    must_fail("type_field", lambda d: d["components"][8].__setitem__("source_field", "virtio_blk_config.capacity"))
    must_fail("barrier_flush_assumption", lambda d: d["components"][9].__setitem__("implementation", "real_flush"))
    must_fail("aux_artifact_policy", lambda d: d["components"][10].__setitem__("artifact_policy", "commit_to_repo"))
    must_fail("source_drift", lambda d: d["source_locks"]["inferno"].__setitem__("revision", "deadbeef"))
    must_fail("scope_creep", lambda d: d.__setitem__("next_objective", "P3.07"))

    return {
        "classification": "P3_04_SELF_CHECK_PASS",
        "negative_tests": mutations,
        "count": len(mutations),
    }


def print_json(value):
    print(json.dumps(value, indent=2, sort_keys=True))


def main():
    p = argparse.ArgumentParser(description="Validate the AppleSilicon P3.04 VMApple boot/storage contract")
    p.add_argument("--contract", required=True)
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("validate")
    sub.add_parser("summary")
    sub.add_parser("self-check")
    v = sub.add_parser("verify-source")
    v.add_argument("--vmapple", required=True)
    v.add_argument("--bdif", required=True)
    v.add_argument("--virtio-blk", required=True)

    args = p.parse_args()
    try:
        data = load_json(args.contract)
        if args.command == "validate":
            print_json(validate(data))
        elif args.command == "summary":
            result = validate(data)
            comps = components_by_id(data)
            print_json({
                "classification": "P3_04_SUMMARY",
                "project_version": data["project_version"],
                "bdif_base": comps["bdif_mmio"]["base"],
                "bdif_read_only": not comps["bdif_command_semantics"]["write_supported"],
                "runtime_variants": comps["vmapple_virtio_blk_variant"]["valid_runtime_variants"],
                "pci_vendor_id": comps["vmapple_virtio_blk_pci_identity"]["pci_vendor_id"],
                "pci_device_id": comps["vmapple_virtio_blk_pci_identity"]["pci_device_id"],
                "barrier": comps["vmapple_virtio_blk_barrier"]["implementation"],
                "fingerprint": result["fingerprint"],
                "runtime_executed": False,
            })
        elif args.command == "self-check":
            print_json(self_check(data))
        elif args.command == "verify-source":
            print_json(verify_source(data, args.vmapple, args.bdif, args.virtio_blk))
    except (OSError, json.JSONDecodeError, ContractError) as exc:
        print(f"P3.04 validation failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

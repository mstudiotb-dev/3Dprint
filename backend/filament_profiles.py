"""
Printer / filament / process preset resolution and material-family policies.

Bambu Studio ships one filament preset per printer family (e.g. `Bambu PLA Basic @BBL A1`,
`@BBL A1M`, `@BBL P1S 0.4 nozzle`, `@BBL X1C`). Each lists the printers it supports under
`compatible_printers`. This module picks the right preset for the selected printer instead of
hardcoding `@BBL A1`, and describes how each material family (PLA, PLA Lite, PETG) changes the
rule engine's proposals. Absolute numbers (temperatures, fan, flow) always come from the vendor
profile; the policies below only hold material-specific deltas and safety floors.
"""

from functools import lru_cache
from typing import Any

from printer_catalog import (
    DEFAULT_PRINTER,
    PRINTERS,
    SLICERS,
    VENDOR_FILAMENTS,
    load_creality_k1max_bundle,
    load_snapmaker_u1_bundle,
    needs_cross_vendor_retarget,
    normalize_printer,
    profiles_for,
    source_vendor_of,
    vendor_of,
)
from slicer_launcher import slicer_installed
from profiler import get_system_baseline, resolve_profile

# Filament choices offered in the UI: key -> Bambu preset base name (before " @BBL ...").
# "PETG Creality" is the M.Studio fork's GĐ1 filament: PETG Creality on the K1 Max, with
# values verified on the real Goku-head print (13/11/2026). Other keys on a K1 Max resolve
# to generic Orca names and are NOT verified — see VENDOR_FILAMENTS in printer_catalog.py.
FILAMENTS: dict[str, str] = {
    "PLA Lite": "Bambu PLA Lite",
    "PLA Basic": "Bambu PLA Basic",
    "PETG HF": "Bambu PETG HF",
    "PETG Creality": "Creality PETG",
}
DEFAULT_FILAMENT = "PLA Lite"

# Bambu Studio `curr_bed_type` values -> filament temperature key prefix.
BED_TYPE_TEMP_KEY: dict[str, str] = {
    "Textured PEI Plate": "textured_plate_temp",
    "High Temp Plate": "hot_plate_temp",
    "Cool Plate": "cool_plate_temp",
    "Engineering Plate": "eng_plate_temp",
    "Supertack Plate": "supertack_plate_temp",
}
BED_TYPE_LABEL: dict[str, str] = {
    "Textured PEI Plate": "Textured PEI",
    "High Temp Plate": "Smooth PEI (High Temp)",
    "Cool Plate": "Cool Plate",
    "Engineering Plate": "Engineering Plate",
    "Supertack Plate": "SuperTack Plate",
}
DEFAULT_BED_TYPE = "Textured PEI Plate"

# Material-family deltas used by the rule engine and enforced again at apply time.
MATERIAL_POLICIES: dict[str, dict[str, Any]] = {
    "PLA": {
        "label": "PLA",
        "support_top_z_distance": "0.14",
        "support_interface_spacing": "0.15",
        "min_support_top_z_distance": 0.0,
        "brim_object_gap": "0",
        "screw_brim_object_gap": "0.04",
        "min_brim_object_gap": 0.0,
        "z_hop": "0.8",
        "z_hop_type": "Normal Lift",
        "ironing_flow": "12%",
        "ironing_speed": "30",
        "force_full_overhang_fan": True,
        "weak_layer_adhesion": False,
    },
    "PLA_LITE": {
        "label": "PLA Lite",
        "support_top_z_distance": "0.14",
        "support_interface_spacing": "0.15",
        "min_support_top_z_distance": 0.0,
        "brim_object_gap": "0",
        "screw_brim_object_gap": "0.04",
        "min_brim_object_gap": 0.0,
        "z_hop": "0.8",
        "z_hop_type": "Normal Lift",
        "ironing_flow": "12%",
        "ironing_speed": "30",
        "force_full_overhang_fan": True,
        "weak_layer_adhesion": True,
    },
    "PETG": {
        "label": "PETG",
        # PETG welds to its own supports: keep at least ~one layer of air and a looser interface.
        "support_top_z_distance": "0.2",
        "support_interface_spacing": "0.25",
        "min_support_top_z_distance": 0.2,
        # A zero-gap PETG brim fuses to the part and cannot be peeled cleanly.
        "brim_object_gap": "0.1",
        "screw_brim_object_gap": "0.1",
        "min_brim_object_gap": 0.1,
        # Tall Normal Lift hops add strings on PETG; Bambu's own PETG profile uses Spiral Lift.
        "z_hop": "0.4",
        "z_hop_type": "Spiral Lift",
        "ironing_flow": "10%",
        "ironing_speed": "20",
        "force_full_overhang_fan": False,
        "weak_layer_adhesion": False,
    },
}

# K1 Max PETG policy (M.Studio fork, GĐ1). Same safety floors as the generic PETG
# policy — PETG welds to its supports and to a zero-gap brim on any printer — plus the
# K1 Max specifics proven on the Goku print: seam hidden at the back (Creality Print
# 7.3 has NO separate "Hide Z Seam" key, so `seam_position = aligned_back` is the
# correct setting) and Spiral Lift instead of a tall Normal Lift.
# Retraction is deliberately NOT in here: 0.8mm is inherited from Hyper PETG and is
# UNVERIFIED on the K1 Max — do not hard-code it as a proven value.
PETG_K1MAX_POLICY: dict[str, Any] = {
    "label": "PETG",
    "support_top_z_distance": "0.2",
    "support_interface_spacing": "0.25",
    "min_support_top_z_distance": 0.2,
    "brim_object_gap": "0.1",
    "screw_brim_object_gap": "0.1",
    "min_brim_object_gap": 0.1,
    "z_hop": "0.4",
    "z_hop_type": "Spiral Lift",
    "seam_position": "aligned_back",
    "ironing_flow": "10%",
    "ironing_speed": "20",
    "force_full_overhang_fan": False,
    "weak_layer_adhesion": False,
}

MODEL_FAMILIES = ("PLA", "PLA_LITE", "PETG")


def filament_base_name(value: str) -> str:
    """Accepts a UI key ('PETG HF') or a full preset name ('Bambu PETG HF @BBL A1')."""
    value = (value or "").strip()
    if value in FILAMENTS:
        return FILAMENTS[value]
    if " @" in value:
        return value.split(" @", 1)[0]
    return value or FILAMENTS[DEFAULT_FILAMENT]


def filament_key_for(value: str) -> str:
    """Maps any preset name back to its UI key, defaulting to PLA Lite for unknown names."""
    base = filament_base_name(value)
    for key, b in FILAMENTS.items():
        if b == base:
            return key
    return DEFAULT_FILAMENT


def _pick_compatible(base: str, printer: str, profiles: dict[str, dict]) -> str | None:
    """Shortest instantiable preset named `base` or `base @...` that lists `printer` as compatible.
    (Snapmaker Orca 2.4.1 names its 0.4 nozzle U1 presets without a suffix, e.g. `Generic PLA`.)"""
    matches: list[str] = []
    for name in profiles:
        if name != base and not name.startswith(f"{base} @"):
            continue
        resolved = resolve_profile(name, profiles)
        if str(resolved.get("instantiation", "true")).lower() != "true":
            continue
        if printer in (resolved.get("compatible_printers") or []):
            matches.append(name)
    return min(matches, key=len) if matches else None


def vendor_filament_base(printer: str, filament: str) -> str:
    """Preset base name of a UI filament key (or any preset name) in the printer vendor's catalog."""
    base = filament_base_name(filament)
    if vendor_of(printer) != "bbl" and base in FILAMENTS.values():
        mapping = VENDOR_FILAMENTS[vendor_of(printer)]
        key = filament_key_for(base)
        if key in mapping:
            return mapping[key]
        # A filament key this vendor's map does not know yet (e.g. "PETG Creality"
        # on a Snapmaker printer): fall back to the vendor's PETG entry for PETG
        # families instead of raising KeyError.
        if material_family(base) == "PETG":
            return mapping.get("PETG HF", base)
        return base
    return base


@lru_cache(maxsize=128)
def resolve_filament_preset(printer: str, filament: str) -> str:
    printer = normalize_printer(printer)
    base = vendor_filament_base(printer, filament)
    picked = _pick_compatible(base, printer, profiles_for(printer))
    return picked or f"{base} {PRINTERS[printer]['fallback_filament_suffix']}"


@lru_cache(maxsize=32)
def resolve_process_preset(printer: str, quality: str = "0.20mm Standard") -> str:
    """Process preset of `quality` for the printer; U1 printers use Snapmaker's default process,
    K1 Max printers use the bundled Creality default process (GĐ1: 0.20mm Standard)."""
    printer = normalize_printer(printer)
    if vendor_of(printer) == "snapmaker":
        default = load_snapmaker_u1_bundle()["default_process"].get(printer)
        picked = _pick_compatible(quality, printer, profiles_for(printer))
        return picked or default or f"{quality} {PRINTERS[printer]['fallback_process_suffix']}"
    if vendor_of(printer) == "creality":
        default = load_creality_k1max_bundle()["default_process"].get(printer)
        picked = _pick_compatible(quality, printer, profiles_for(printer))
        return picked or default or f"{quality} {PRINTERS[printer]['fallback_process_suffix']}"
    picked = _pick_compatible(quality, printer, profiles_for(printer))
    return picked or f"{quality} {PRINTERS[printer]['fallback_process_suffix']}"


def system_baseline(printer: str, filament_preset: str = "", process_preset: str = "") -> dict[str, Any]:
    """Machine + filament + process system values merged, read from the printer vendor's presets."""
    printer = normalize_printer(printer)
    return get_system_baseline(printer, filament_preset, process_preset, profiles_for(printer))


def equivalent_filament_preset(printer: str, slot: dict[str, Any]) -> str:
    """Target-vendor preset for a slot the user keeps as-is (support, other materials), matched by
    material type: e.g. `Bambu Support for PLA @BBL A1` -> `Generic Support For PLA` on a U1."""
    if vendor_of(printer) == "bbl":
        base = filament_base_name(slot.get("preset") or "") or FILAMENTS[DEFAULT_FILAMENT]
        return resolve_filament_preset(printer, base)
    fam = slot.get("family")
    ftype = (slot.get("type") or "").upper().replace("-S", "")
    if vendor_of(printer) == "creality":
        # GĐ1: only PETG Creality is a real bundled preset; support/PLA slots fall
        # back to generic Orca names (unverified on the K1 Max).
        candidates = {
            "SUPPORT": ["Generic Support For PLA", "Generic PLA"],
            "PETG": ["Creality PETG"],
            "PLA": ["Generic PLA"],
            "PLA_LITE": ["Generic PLA"],
        }.get(fam or "", [f"Generic {ftype}", "Generic PLA"] if ftype else ["Generic PLA"])
    else:
        candidates = {
            "SUPPORT": ["Generic Support For PLA", "Generic PVA", "Generic PLA"],
            "PETG": ["Generic PETG HF", "Generic PETG"],
            "PLA": ["Generic PLA"],
            "PLA_LITE": ["Generic PLA"],
        }.get(fam or "", [f"Generic {ftype}", "Generic PLA"] if ftype else ["Generic PLA"])
    profiles = profiles_for(printer)
    for base in candidates:
        picked = _pick_compatible(base, printer, profiles)
        if picked:
            return picked
    return resolve_filament_preset(printer, "PLA Basic")


def material_family(preset_name: str, filament_type: str = "") -> str:
    """Classifies a filament slot: PLA, PLA_LITE, PETG, SUPPORT or OTHER."""
    text = f"{preset_name} {filament_type}".lower()
    if "support" in text or "pva" in text or "bvoh" in text:
        return "SUPPORT"
    if "petg" in text or filament_type.upper() in ("PETG", "PET"):
        return "PETG"
    if "pla lite" in text:
        return "PLA_LITE"
    if "pla" in text:
        return "PLA"
    return "OTHER"


def family_group(family: str) -> str:
    """PLA and PLA Lite print with the same physics, so they are retargeted together."""
    return "PLA" if family in ("PLA", "PLA_LITE") else family


def policy_for(filament: str) -> dict[str, Any]:
    fam = material_family(filament_base_name(filament))
    return MATERIAL_POLICIES.get(fam, MATERIAL_POLICIES["PLA"])


def policy_for_printer(filament: str, printer: str) -> dict[str, Any]:
    """K1 Max PETG gets the verified K1 Max policy (incl. `aligned_back` seam);
    every other printer/filament keeps the generic family policy."""
    if vendor_of(printer) == "creality" and material_family(filament_base_name(filament)) == "PETG":
        return PETG_K1MAX_POLICY
    return policy_for(filament)


# Plates the Snapmaker U1 profile set defines temperatures for; any other Bambu plate becomes Textured PEI.
SNAPMAKER_BED_TYPES = ("Textured PEI Plate", "High Temp Plate")

# Plates the K1 Max bundle defines temperatures for (Textured PEI = textured_plate_temp,
# Smooth PEI = High Temp Plate = hot_plate_temp). Same rule as the U1 set.
CREALITY_BED_TYPES = ("Textured PEI Plate", "High Temp Plate")


def bed_type_of(project_settings: dict[str, Any], printer: str | None = None) -> str:
    """The plate the project prints on, mapped to one the target printer actually has."""
    raw = project_settings.get("curr_bed_type")
    if isinstance(raw, list):
        raw = raw[0] if raw else None
    bed = raw if raw in BED_TYPE_TEMP_KEY else DEFAULT_BED_TYPE
    if printer and vendor_of(printer) == "snapmaker" and bed not in SNAPMAKER_BED_TYPES:
        return DEFAULT_BED_TYPE
    if printer and vendor_of(printer) == "creality" and bed not in CREALITY_BED_TYPES:
        return DEFAULT_BED_TYPE
    return bed


def _slot_list(project_settings: dict[str, Any], key: str, n: int) -> list[str]:
    raw = project_settings.get(key)
    vals = raw if isinstance(raw, list) else ([raw] if raw else [])
    return [str(vals[i]) if i < len(vals) else "" for i in range(n)]


def slot_count(project_settings: dict[str, Any]) -> int:
    for key in ("filament_colour", "filament_settings_id", "filament_type"):
        raw = project_settings.get(key)
        if isinstance(raw, list) and raw:
            return len(raw)
    return 1


def describe_filament_slots(project_settings: dict[str, Any]) -> list[dict[str, Any]]:
    """Per-slot author filament info read from the 3MF's project settings."""
    n = slot_count(project_settings)
    presets = _slot_list(project_settings, "filament_settings_id", n)
    types = _slot_list(project_settings, "filament_type", n)
    colours = _slot_list(project_settings, "filament_colour", n)
    slots = []
    for i in range(n):
        fam = material_family(presets[i], types[i])
        slots.append({
            "index": i,
            "preset": presets[i],
            "type": types[i] or ("PLA" if not presets[i] else ""),
            "colour": colours[i],
            "family": fam,
            "role": "support" if fam == "SUPPORT" else "model",
        })
    return slots


def main_model_group(slots: list[dict[str, Any]]) -> str | None:
    for s in slots:
        if s["role"] == "model" and s["family"] in MODEL_FAMILIES:
            return family_group(s["family"])
    return None


def has_mixed_model_families(slots: list[dict[str, Any]]) -> bool:
    groups = {family_group(s["family"]) for s in slots if s["role"] == "model" and s["family"] in MODEL_FAMILIES}
    return len(groups) > 1


def plan_slot_filaments(
    slots: list[dict[str, Any]],
    selected_filament: str,
    slot_overrides: list[str | None] | None = None,
) -> dict[int, str]:
    """
    Decides which filament each slot is retargeted to: {slot_index: UI filament key}.
    Slots not in the result keep the author's settings untouched (e.g. support interfaces).

    Default: retarget only slots in the same material group as the main body (or every slot
    whose material is unknown, e.g. plain STL or files without filament metadata).
    `slot_overrides` (one entry per slot, None = keep author's) replaces the default when given.
    """
    if slot_overrides and len(slot_overrides) == len(slots):
        return {i: filament_key_for(v) for i, v in enumerate(slot_overrides) if v}

    key = filament_key_for(selected_filament)
    main = main_model_group(slots)
    if main is None:
        return {s["index"]: key for s in slots if s["role"] == "model"} or {0: key}
    return {
        s["index"]: key
        for s in slots
        if s["role"] == "model" and family_group(s["family"]) == main
    }


def build_material_context(
    project_settings: dict[str, Any],
    printer: str,
    filament: str,
    slot_overrides: list[str | None] | None = None,
) -> dict[str, Any]:
    """Summary the UI and AI prompt use to explain which presets and plate apply."""
    printer = normalize_printer(printer)
    slots = describe_filament_slots(project_settings)
    plan = plan_slot_filaments(slots, filament, slot_overrides)
    bed = bed_type_of(project_settings, printer)
    retarget = needs_cross_vendor_retarget(project_settings, printer)
    for s in slots:
        target = plan.get(s["index"])
        s["target_filament"] = target
        if target:
            s["target_preset"] = resolve_filament_preset(printer, target)
        else:
            # Kept slots still need a preset that exists on another vendor's printer.
            s["target_preset"] = equivalent_filament_preset(printer, s) if retarget else None
    meta = PRINTERS[printer]
    return {
        "printer_preset": printer,
        "printer_label": meta["label"],
        "printer_vendor": meta["vendor"],
        "kinematics": meta["kinematics"],
        "nozzle": meta["nozzle"],
        "max_tools": meta["max_tools"],
        "slicer": meta["slicer"],
        "source_vendor": source_vendor_of(project_settings),
        "cross_vendor_retarget": retarget,
        "enclosed": meta["enclosed"],
        "filament": filament_key_for(filament),
        "filament_preset": resolve_filament_preset(printer, filament),
        "family": material_family(filament_base_name(filament)),
        "bed_type": bed,
        "bed_label": BED_TYPE_LABEL[bed],
        "slots": slots,
        "mixed_model_families": has_mixed_model_families(slots),
    }


def list_preset_options() -> dict[str, Any]:
    """Printer and filament choices, with the exact vendor preset each pair resolves to."""
    return {
        "printers": [
            {
                "id": p,
                "label": meta["label"],
                "vendor": meta["vendor"],
                "vendor_label": meta["vendor_label"],
                "nozzle": meta["nozzle"],
                "kinematics": meta["kinematics"],
                "enclosed": meta["enclosed"],
                "max_tools": meta["max_tools"],
                "slicer": meta["slicer"],
            }
            for p, meta in PRINTERS.items()
        ],
        "slicers": {sid: {**info, "installed": slicer_installed(sid)} for sid, info in SLICERS.items()},
        "filaments": [
            {
                "id": key,
                "label": key,
                "family": material_family(base),
                "presets": {p: resolve_filament_preset(p, key) for p in PRINTERS},
            }
            for key, base in FILAMENTS.items()
        ],
        "default_printer": DEFAULT_PRINTER,
        "default_filament": DEFAULT_FILAMENT,
    }

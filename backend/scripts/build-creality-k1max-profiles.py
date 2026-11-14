"""
Builds the bundled Creality K1 Max preset file (M.Studio fork, GĐ1).

Unlike `build-snapmaker-u1-profiles.py`, there is no public Creality preset repo to
flatten yet, so this script writes the bundle from the values VERIFIED on a real
K1 Max print — the Goku bust head, printed 13/11/2026 in Creality Print 7.3
(PETG Creality, profiles "Goku Head 0.10" / "Goku Toc 0.10" / "Goku Than 0.12" /
"Goku De 0.16"). Run from `backend/` with no arguments to regenerate the bundle:

    .venv/bin/python scripts/build-creality-k1max-profiles.py

When the real Creality Print 7.3 system presets are exported from the user's PC,
replace VERIFIED below with the flattened vendor presets (same shape as the
Snapmaker bundle) and update `source.verification` — do NOT just edit the JSON
by hand, or the two will drift apart.

Known unverified items (do not present as proven):
- `printer_model_id` ("K1_MAX") and the Creality Print version string a project
  should claim: placeholders until the real system preset is compared.
- Retraction 0.8mm (inherited from Hyper PETG): NOT in this file at all.
- PLA presets: the bundle only ships PETG Creality. Generic PLA names exist in
  the catalog only so filament resolution does not crash; they are not tested.
"""

import json
from pathlib import Path

OUT_PATH = Path(__file__).resolve().parent.parent / "vendor_profiles" / "creality-k1max-presets.json"

PRINTER = "Creality K1 Max 0.4 nozzle"

# Values proven on the real Goku-head print (Creality Print 7.3, K1 Max, 0.4mm).
# Bed: Smooth PEI 75°C first layer / 70°C other layers (NOT 75°C throughout).
VERIFIED = {
    "nozzle_temperature_initial_layer": "245",
    "nozzle_temperature": "240",
    "textured_plate_temp_initial_layer": "75",
    "textured_plate_temp": "70",
    "hot_plate_temp_initial_layer": "75",  # Smooth PEI = High Temp Plate in Orca
    "hot_plate_temp": "70",
    "filament_flow_ratio": "0.97",
    "filament_max_volumetric_speed": "12",
}


def _process(name: str, layer_height: str) -> dict:
    return {
        "type": "process",
        "name": name,
        "from": "system",
        "instantiation": "true",
        "compatible_printers": [PRINTER],
        "layer_height": [layer_height],
        "initial_layer_print_height": ["0.2"],
        "wall_loops": ["3"],
        "top_shell_layers": ["5"],
        "bottom_shell_layers": ["4"],
        "sparse_infill_density": ["15%"],
        "sparse_infill_pattern": ["grid"],
        "top_surface_pattern": ["monotonic"],
        "bottom_surface_pattern": ["monotonic"],
        # Creality Print 7.3 has NO separate "Hide Z Seam" key: aligned_back is
        # the setting that hides the seam at the back of the part.
        "seam_position": ["aligned_back"],
        "enable_support": ["1"],
        "support_type": ["tree(auto)"],
        "support_threshold_angle": ["30"],
        "support_top_z_distance": ["0.2"],
        "support_interface_spacing": ["0.25"],
        "brim_type": ["auto_brim"],
        "brim_width": ["5"],
        "brim_object_gap": ["0.1"],
    }


def build() -> dict:
    machine = {
        "type": "machine",
        "name": PRINTER,
        "from": "system",
        "instantiation": "true",
        "compatible_printers": [PRINTER],
        "printer_model": "Creality K1 Max",
        "printer_model_id": "K1_MAX",  # placeholder — see module docstring
        "printable_area": ["0x0", "300x0", "300x300", "0x300"],
        "printable_height": "300",
        "nozzle_diameter": ["0.4"],
        "min_layer_height": ["0.08"],
        "max_layer_height": ["0.32"],
        "default_print_profile": "0.20mm Standard @Creality K1 Max",
        "gcode_flavor": "klipper",
    }
    filament = {
        "type": "filament",
        "name": "Creality PETG @Creality K1 Max",
        "from": "system",
        "instantiation": "true",
        "compatible_printers": [PRINTER],
        "filament_type": ["PETG"],
        "filament_vendor": ["Creality"],
        "filament_diameter": ["1.75"],
        "filament_flow_ratio": [VERIFIED["filament_flow_ratio"]],
        "filament_max_volumetric_speed": [VERIFIED["filament_max_volumetric_speed"]],
        "nozzle_temperature": [VERIFIED["nozzle_temperature"]],
        "nozzle_temperature_initial_layer": [VERIFIED["nozzle_temperature_initial_layer"]],
        "textured_plate_temp": [VERIFIED["textured_plate_temp"]],
        "textured_plate_temp_initial_layer": [VERIFIED["textured_plate_temp_initial_layer"]],
        "hot_plate_temp": [VERIFIED["hot_plate_temp"]],
        "hot_plate_temp_initial_layer": [VERIFIED["hot_plate_temp_initial_layer"]],
    }
    presets: dict[str, dict] = {PRINTER: machine, filament["name"]: filament}
    for layer in ("0.10", "0.12", "0.16", "0.20"):
        name = f"{layer}mm Standard @Creality K1 Max"
        presets[name] = _process(name, layer)
    return {
        "source": {
            "repository": "https://github.com/mstudiotb-dev/3Dprint",
            "release": "k1max-gd1",
            "verification": (
                "Values verified on a real K1 Max print: Goku bust head, 13/11/2026, "
                "Creality Print 7.3, PETG Creality (nozzle 245/240C, Smooth PEI bed "
                "75/70C, flow 0.97, max volumetric 12 mm3/s). NOT a dump of Creality "
                "Print system presets — pending export from the user's PC for comparison. "
                "Retraction (0.8mm, inherited from Hyper PETG) is UNVERIFIED and not included."
            ),
        },
        "printer_model_id": "K1_MAX",
        "default_process": {PRINTER: "0.20mm Standard @Creality K1 Max"},
        "presets": dict(sorted(presets.items())),
    }


def main() -> None:
    data = build()
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {len(data['presets'])} presets to {OUT_PATH}")


if __name__ == "__main__":
    main()

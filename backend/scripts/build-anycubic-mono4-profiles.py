"""
Builds the bundled Anycubic Photon Mono 4 resin preset file (M.Studio fork, GĐ2).

Unlike `build-snapmaker-u1-profiles.py`, there is no public Anycubic preset
repo to flatten, so this script writes the bundle from the manufacturer-
recommended values in `resin_profiles.py` (single source of truth — do NOT
edit the JSON by hand, or the two will drift apart). Run from `backend/`:

    .venv/bin/python scripts/build-anycubic-mono4-profiles.py

Provenance (read before trusting a number): the Water-Wash Resin 2.0 values
are Anycubic's recommended values for the Photon Mono 4 at 0.05mm layer
height (normal exposure 2.4s, range 2-2.5s; first layer 25-40s; bottom
exposure 30s, 5 bottom layers; light-off 1s; Z lift 5mm at 8mm/s, retract
8mm/s; AA 1). They are NOT verified on the user's own Mono 4 yet — when the
user's Photon Workshop settings are exported, replace the values here and
update `source.verification`. (The user's slicer is CHITUBOX, not Photon
Workshop — Photon Workshop is only a secondary option.)

Known unverified items (do not present as proven):
- `printer_model_id` ("PHOTON_MONO_4"): placeholder until a real Photon
  Workshop project file is compared.
- Resin density: NOT in this file (check the bottle) — resin use is
  estimated in millilitres only, never in grams.
- Lychee / Chitubox equivalents of these settings: Photon Workshop is the
  default slicer; Lychee is a launcher option only, its preset mapping is
  not in this bundle.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from resin_profiles import MONO4, RESIN_BUILD_VOLUME_MM, WATER_WASH_2_0  # noqa: E402

OUT_PATH = Path(__file__).resolve().parent.parent / "vendor_profiles" / "anycubic-mono4-resin-presets.json"

PRINTER = MONO4
RESIN = WATER_WASH_2_0["name"]
RESIN_PRESET_NAME = f"Anycubic {RESIN} @{PRINTER}"


def build() -> dict:
    machine = {
        "type": "machine",
        "name": PRINTER,
        "from": "system",
        "instantiation": "true",
        "compatible_printers": [PRINTER],
        "printer_model": "Photon Mono 4",
        "printer_model_id": "PHOTON_MONO_4",  # placeholder — see module docstring
        "technology": "resin_mlsa",
        "printable_area": ["0x0", "153.4x0", "153.4x87", "0x87"],
        "printable_height": "165",
        "lcd_resolution": ["9024x5120"],
        "xy_resolution_um": ["17"],
        "min_layer_height": ["0.03"],
        "max_layer_height": ["0.15"],
        "vat_capacity_ml": ["390"],
        "default_print_profile": f"0.05mm Standard @{PRINTER}",
    }
    resin = {
        "type": "resin",
        "name": RESIN_PRESET_NAME,
        "from": "system",
        "instantiation": "true",
        "compatible_printers": [PRINTER],
        "resin_type": ["Water-Wash"],
        "resin_vendor": ["Anycubic"],
        "resin_name": [RESIN],
        # The user's own resin (confirmed 14/11/2026): Gray, 1kg bottle.
        # Exposure depends on colour — this preset is for Gray only.
        "resin_colour": [WATER_WASH_2_0["colour"]],
        "resin_bottle_kg": [str(WATER_WASH_2_0["bottle_kg"])],
        "layer_height": [str(WATER_WASH_2_0["layer_height_mm"])],
        "normal_exposure_s": [str(WATER_WASH_2_0["normal_exposure_s"])],
        "normal_exposure_range_s": [WATER_WASH_2_0["normal_exposure_range_s"]],
        "first_layer_exposure_range_s": [WATER_WASH_2_0["first_layer_exposure_range_s"]],
        "bottom_exposure_s": [str(WATER_WASH_2_0["bottom_exposure_s"])],
        "bottom_layers": [str(WATER_WASH_2_0["bottom_layers"])],
        "light_off_delay_s": [str(WATER_WASH_2_0["light_off_delay_s"])],
        "z_lift_distance_mm": [str(WATER_WASH_2_0["z_lift_distance_mm"])],
        "z_lift_speed_mm_s": [str(WATER_WASH_2_0["z_lift_speed_mm_s"])],
        "z_retract_speed_mm_s": [str(WATER_WASH_2_0["z_retract_speed_mm_s"])],
        "anti_aliasing": [str(WATER_WASH_2_0["anti_aliasing"])],
        "recommended_temp_c": [WATER_WASH_2_0["recommended_temp_c"]],
        "wash": [WATER_WASH_2_0["wash"]],
    }
    process = {
        "type": "process",
        "name": f"0.05mm Standard @{PRINTER}",
        "from": "system",
        "instantiation": "true",
        "compatible_printers": [PRINTER],
        "layer_height": [str(WATER_WASH_2_0["layer_height_mm"])],
        "normal_exposure_s": [str(WATER_WASH_2_0["normal_exposure_s"])],
        "bottom_exposure_s": [str(WATER_WASH_2_0["bottom_exposure_s"])],
        "bottom_layers": [str(WATER_WASH_2_0["bottom_layers"])],
        "light_off_delay_s": [str(WATER_WASH_2_0["light_off_delay_s"])],
        "z_lift_distance_mm": [str(WATER_WASH_2_0["z_lift_distance_mm"])],
        "z_lift_speed_mm_s": [str(WATER_WASH_2_0["z_lift_speed_mm_s"])],
        "z_retract_speed_mm_s": [str(WATER_WASH_2_0["z_retract_speed_mm_s"])],
        "anti_aliasing": [str(WATER_WASH_2_0["anti_aliasing"])],
    }
    presets: dict[str, dict] = {PRINTER: machine, RESIN_PRESET_NAME: resin, process["name"]: process}
    return {
        "source": {
            "repository": "https://github.com/mstudiotb-dev/3Dprint",
            "release": "resin-mono4-gd2",
            "verification": (
                "Manufacturer-recommended values from Anycubic for Water-Wash "
                "Resin 2.0 on the Photon Mono 4 (0.05mm layer): normal exposure "
                "2.4s (range 2-2.5s), first layer 25-40s, bottom exposure 30s, "
                "5 bottom layers, light-off 1s, Z lift 5mm, lift 8mm/s, retract "
                "8mm/s, AA 1. NOT verified on the user's own Mono 4 yet — "
                "compare with the user's CHITUBOX settings before printing."
            ),
        },
        "printer_model_id": "PHOTON_MONO_4",
        "default_process": {PRINTER: f"0.05mm Standard @{PRINTER}"},
        "presets": dict(sorted(presets.items())),
    }


def main() -> None:
    data = build()
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {len(data['presets'])} presets to {OUT_PATH}")


if __name__ == "__main__":
    main()

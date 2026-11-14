"""
Resin (MSLA) printer / resin preset data — M.Studio fork, GĐ2.

The upstream LayerZero engine is FDM-only: nozzle / bed / flow / brim / .3mf
patching. Resin printing has none of those; its parameters are exposure time,
bottom exposure, lift distance/speed and layer height, and its workflow starts
from an STL in Photon Workshop / Lychee, not from a Bambu .3mf. This module
holds the resin data as a separate, parallel module so the FDM pipeline
(`profiler.py`, `patcher.py`, `filament_profiles.py` FDM policies) is untouched.

Preset provenance — read this before trusting a number:
- The Water-Wash Resin 2.0 values below are the MANUFACTURER-RECOMMENDED
  values from Anycubic's product page for the Photon Mono 4 at 0.05mm layer
  height. They are a starting point, NOT numbers proven on the user's own
  Mono 4. The user has not printed with them yet; compare against the
  settings in the user's own Photon Workshop before printing.
- Anycubic also states: first layer 25-40s, normal exposure 2-2.5s for this
  resin; recommended ambient temperature 20-35°C; in summer (>30°C without
  temperature control) reduce exposure by 0.5-1s, in winter (<10°C) increase
  it by 0.5-1s. Resin colour also changes the exposure — this preset is for
  the user's GRAY resin; do not reuse it for another colour without a test.
- Slicer: the user slices with CHITUBOX (primary), Photon Workshop is only
  a secondary option. CHITUBOX produces the .ctb print file itself;
  LayerZero does NOT write .ctb files — the resin preset values below must
  be entered in CHITUBOX (or opened there from the exported model file).
- No other numbers are invented here: anything not published by Anycubic for
  this printer/resin pair is left out (e.g. resin density is NOT in this
  file — check the bottle label — so `resin_checks` estimates millilitres
  from volume only, never grams).
"""

from copy import deepcopy
from typing import Any

MONO4 = "Anycubic Photon Mono 4"

# Build volume of the Photon Mono 4 in mm (X, Y, Z). Vat capacity is 0.39 L.
RESIN_BUILD_VOLUME_MM: tuple[float, float, float] = (153.4, 87.0, 165.0)
RESIN_VAT_CAPACITY_ML = 390.0

# Layer heights the Mono 4 supports, per Anycubic's specification.
RESIN_LAYER_HEIGHT_RANGE_MM: tuple[float, float] = (0.03, 0.15)

# Minimum wall thickness (mm) for a hollow resin part to survive printing and
# post-curing without cracking. Taken from the user's own MStudio Tách Part 3D
# tool, which already enforces this rule for resin parts.
MIN_WALL_THICKNESS_MM = 1.2

# Minimum number of drain holes for a hollowed resin part (one is never
# enough: trapped resin needs an inlet and an outlet).
MIN_DRAIN_HOLES = 2

WATER_WASH_2_0: dict[str, Any] = {
    "name": "Water-Wash Resin 2.0",
    "vendor": "Anycubic",
    "printer": MONO4,
    # The user's own resin (confirmed 14/11/2026, shop UniTak3D): Gray, 1kg bottle.
    # Exposure depends on colour — this preset is for GRAY; another colour
    # may need a different exposure, do not reuse it blindly.
    "colour": "Gray",
    "bottle_kg": 1,
    # Manufacturer-recommended values, Photon Mono 4, 0.05mm layer height.
    "layer_height_mm": 0.05,
    "normal_exposure_s": 2.4,
    "normal_exposure_range_s": "2-2.5",
    "first_layer_exposure_range_s": "25-40",
    "bottom_exposure_s": 30.0,
    "bottom_layers": 5,
    "light_off_delay_s": 1.0,
    "z_lift_distance_mm": 5.0,
    "z_lift_speed_mm_s": 8.0,
    "z_retract_speed_mm_s": 8.0,
    "anti_aliasing": 1,
    "recommended_temp_c": "20-35",
    "wash": "water",
    "wash_note": "Rửa bằng nước sạch, KHÔNG dùng IPA.",
    "cure_note": "Sấy UV sau khi rửa và để khô.",
    "provenance": (
        "Manufacturer-recommended values from Anycubic for Water-Wash Resin 2.0 "
        "on the Photon Mono 4 (0.05mm layer). NOT verified on the user's own "
        "printer yet — compare with the user's CHITUBOX settings."
    ),
}

RESIN_PRESETS: dict[str, dict[str, Any]] = {
    WATER_WASH_2_0["name"]: WATER_WASH_2_0,
}


def get_resin_preset(name: str) -> dict[str, Any]:
    """A copy of the named resin preset; raises KeyError for unknown resins."""
    return deepcopy(RESIN_PRESETS[name])


def list_resin_presets() -> dict[str, dict[str, Any]]:
    """All resin presets, keyed by resin name."""
    return deepcopy(RESIN_PRESETS)


def temperature_exposure_note(temp_c: float | None) -> str:
    """Anycubic's temperature guidance for this resin, in Vietnamese.

    Returns an empty string when no temperature is given (nothing to adjust).
    The adjustment is a range, not a precise number — the user still has to
    confirm it against a test print.
    """
    if temp_c is None:
        return ""
    if temp_c > 30:
        return (
            "Nhiệt độ phòng trên 30°C: Anycubic khuyến nghị giảm thời gian phơi "
            "sáng 0.5–1 giây so với preset (nhựa loãng hơn, cure nhanh hơn)."
        )
    if temp_c < 10:
        return (
            "Nhiệt độ phòng dưới 10°C: Anycubic khuyến nghị tăng thời gian phơi "
            "sáng 0.5–1 giây so với preset (nhựa đặc hơn, cure chậm hơn)."
        )
    return "Nhiệt độ phòng 20–35°C: dùng đúng preset, không cần chỉnh exposure."

"""
Resin support tests: Anycubic Photon Mono 4 + Water-Wash Resin 2.0 (M.Studio fork, GĐ2).

Run from `backend/`:  .venv/bin/python -m unittest discover -s tests -v

The preset numbers here are Anycubic's MANUFACTURER-RECOMMENDED values for the
Photon Mono 4 at 0.05mm layer height — the tests pin them so a later edit
cannot silently change a number the user has not verified on his own printer.
If the user's CHITUBOX settings differ, update `resin_profiles.py`
(and the bundle builder) and these tests together.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from filament_profiles import build_material_context, list_preset_options, resolve_filament_preset, resolve_process_preset  # noqa: E402
from material_advice_cards import build_material_advice_cards  # noqa: E402
from printer_catalog import is_resin_printer, load_anycubic_mono4_bundle, profiles_for  # noqa: E402
from resin_checks import (  # noqa: E402
    build_resin_audit,
    check_build_volume,
    check_hollow,
    check_suction_cup,
    check_wall_thickness,
    estimate_print_time_minutes,
    estimate_resin_ml,
    suggest_support_class,
)
from resin_profiles import (  # noqa: E402
    MIN_DRAIN_HOLES,
    MIN_WALL_THICKNESS_MM,
    RESIN_BUILD_VOLUME_MM,
    get_resin_preset,
    temperature_exposure_note,
)
from slicer_launcher import slicer_installed, slicer_not_installed_message  # noqa: E402

MONO4 = "Anycubic Photon Mono 4"
RESIN = "Water-Wash Resin 2.0"


class TestResinPresetNumbers(unittest.TestCase):
    def test_water_wash_preset_matches_manufacturer_values(self):
        p = get_resin_preset(RESIN)
        self.assertEqual(p["layer_height_mm"], 0.05)
        self.assertEqual(p["normal_exposure_s"], 2.4)
        self.assertEqual(p["normal_exposure_range_s"], "2-2.5")
        self.assertEqual(p["first_layer_exposure_range_s"], "25-40")
        self.assertEqual(p["bottom_exposure_s"], 30.0)
        self.assertEqual(p["bottom_layers"], 5)
        self.assertEqual(p["light_off_delay_s"], 1.0)
        self.assertEqual(p["z_lift_distance_mm"], 5.0)
        self.assertEqual(p["z_lift_speed_mm_s"], 8.0)
        self.assertEqual(p["z_retract_speed_mm_s"], 8.0)
        self.assertEqual(p["anti_aliasing"], 1)
        self.assertEqual(p["wash"], "water")
        # The user's own resin (confirmed 14/11/2026, shop UniTak3D): Gray, 1kg.
        self.assertEqual(p["colour"], "Gray")
        self.assertEqual(p["bottle_kg"], 1)

    def test_temperature_rule(self):
        self.assertIn("giảm", temperature_exposure_note(32))
        self.assertIn("tăng", temperature_exposure_note(8))
        self.assertIn("không cần chỉnh", temperature_exposure_note(25))
        self.assertEqual(temperature_exposure_note(None), "")

    def test_preset_provenance_says_manufacturer_not_user_verified(self):
        p = get_resin_preset(RESIN)
        self.assertIn("Manufacturer", p["provenance"])
        self.assertIn("NOT verified", p["provenance"])


class TestMono4Catalog(unittest.TestCase):
    def test_mono4_is_resin_printer(self):
        self.assertTrue(is_resin_printer(MONO4))
        self.assertFalse(is_resin_printer("Bambu Lab A1 0.4 nozzle"))

    def test_mono4_build_volume_and_slicer(self):
        self.assertEqual(RESIN_BUILD_VOLUME_MM, (153.4, 87.0, 165.0))

    def test_mono4_bundle(self):
        bundle = load_anycubic_mono4_bundle()
        self.assertIn(MONO4, bundle["presets"])
        self.assertIn("Anycubic Water-Wash Resin 2.0 @Anycubic Photon Mono 4", bundle["presets"])
        self.assertIn("0.05mm Standard @Anycubic Photon Mono 4", bundle["presets"])
        machine = bundle["presets"][MONO4]
        self.assertEqual(machine["printable_height"], "165")
        self.assertEqual(machine["technology"], "resin_mlsa")
        self.assertIn("NOT verified", bundle["source"]["verification"])

    def test_profiles_for_mono4(self):
        profiles = profiles_for(MONO4)
        self.assertIn("Anycubic Water-Wash Resin 2.0 @Anycubic Photon Mono 4", profiles)

    def test_resolve_presets(self):
        self.assertEqual(resolve_filament_preset(MONO4, RESIN),
                         "Anycubic Water-Wash Resin 2.0 @Anycubic Photon Mono 4")
        self.assertEqual(resolve_process_preset(MONO4),
                         "0.05mm Standard @Anycubic Photon Mono 4")


class TestPresetOptions(unittest.TestCase):
    def test_list_preset_options_has_resin_section(self):
        opts = list_preset_options()
        self.assertIn(MONO4, opts["resin"]["printers"])
        self.assertEqual(opts["resin"]["build_volume_mm"], [153.4, 87.0, 165.0])
        self.assertIn(RESIN, opts["resin"]["presets"])
        self.assertEqual(opts["resin"]["presets"][RESIN]["normal_exposure_s"], 2.4)
        mono4 = next(p for p in opts["printers"] if p["id"] == MONO4)
        self.assertEqual(mono4["technology"], "resin")
        # The user slices with CHITUBOX (confirmed 14/11/2026); Photon
        # Workshop is only a secondary option.
        self.assertEqual(mono4["slicer"], "chitubox")
        self.assertIn("chitubox", opts["slicers"])
        self.assertEqual(opts["slicers"]["chitubox"]["label"], "CHITUBOX")
        self.assertIn("photon_workshop", opts["slicers"])
        self.assertIn("lychee", opts["slicers"])

    def test_material_context_is_resin(self):
        ctx = build_material_context({}, MONO4, RESIN)
        self.assertEqual(ctx["family"], "RESIN")
        self.assertEqual(ctx["filament"], RESIN)
        self.assertEqual(ctx["slots"], [])
        self.assertIn("resin_preset", ctx)
        self.assertEqual(ctx["resin_preset"]["normal_exposure_s"], 2.4)


class TestResinChecks(unittest.TestCase):
    def test_fits_inside_volume(self):
        self.assertEqual(check_build_volume((100, 50, 120)), [])

    def test_exceeds_volume_height(self):
        cards = check_build_volume((100, 50, 200))
        self.assertEqual(len(cards), 1)
        self.assertIn("165", cards[0]["desc"])

    def test_exceeds_volume_footprint(self):
        cards = check_build_volume((200, 100, 100))
        self.assertEqual(len(cards), 1)

    def test_rotated_footprint_fits(self):
        # 87x153.4 fits when rotated (X/Y swap is allowed on the plate).
        self.assertEqual(check_build_volume((87, 153.4, 100)), [])

    def test_wall_thickness(self):
        self.assertEqual(check_wall_thickness(2.0), [])
        self.assertEqual(len(check_wall_thickness(0.8)), 1)
        self.assertEqual(check_wall_thickness(None), [])
        self.assertEqual(len(check_wall_thickness(1.2)), 0)
        self.assertIn("1.2", check_wall_thickness(0.8)[0]["desc"])

    def test_hollow_needs_two_drain_holes(self):
        self.assertEqual(check_hollow(True, 2), [])
        self.assertEqual(len(check_hollow(True, 0)), 1)
        self.assertEqual(len(check_hollow(True, 1)), 1)
        self.assertEqual(check_hollow(False, 0), [])

    def test_suction_cup(self):
        self.assertEqual(check_suction_cup(500), [])
        self.assertEqual(len(check_suction_cup(5000)), 1)
        self.assertEqual(check_suction_cup(None), [])

    def test_estimates(self):
        # 100 cm3 solid = 100 ml; 60% hollow = 40 ml.
        self.assertEqual(estimate_resin_ml(100_000), 100.0)
        self.assertEqual(estimate_resin_ml(100_000, 0.6), 40.0)
        self.assertEqual(estimate_resin_ml(0), 0.0)
        # 165mm tall at 0.05mm layers: 3300 layers x (2.4+1+0.625+0.625)s.
        minutes = estimate_print_time_minutes(165)
        self.assertAlmostEqual(minutes, 3300 * 4.65 / 60, places=1)
        self.assertEqual(suggest_support_class(5_000), "light")
        self.assertEqual(suggest_support_class(30_000), "medium")
        self.assertEqual(suggest_support_class(200_000), "heavy")

    def test_build_resin_audit(self):
        audit = build_resin_audit(
            size_mm=(200, 100, 200), volume_mm3=100_000,
            min_wall_mm=0.8, enclosed_volume=True, drain_holes=0,
            flat_base_area_mm2=5000,
        )
        self.assertEqual(len(audit["cards"]), 4)
        self.assertEqual(audit["estimates"]["resin_ml"], 100.0)
        self.assertEqual(audit["estimates"]["support_class"], "heavy")
        clean = build_resin_audit(size_mm=(100, 50, 100), volume_mm3=10_000,
                                  min_wall_mm=2.0, enclosed_volume=False)
        self.assertEqual(clean["cards"], [])


class TestResinCardsAndLauncher(unittest.TestCase):
    def test_resin_advice_cards(self):
        cards = build_material_advice_cards({}, MONO4, RESIN, {})
        ids = {c["id"] for c in cards}
        self.assertIn("card_resin_water_wash", ids)
        self.assertIn("card_resin_safety", ids)
        self.assertIn("card_resin_exposure_starting_point", ids)
        self.assertIn("card_resin_hollow_drain", ids)
        wash = next(c for c in cards if c["id"] == "card_resin_water_wash")
        self.assertIn("KHÔNG dùng IPA", wash["desc"])
        safety = next(c for c in cards if c["id"] == "card_resin_safety")
        self.assertIn("KHÔNG được đổ xuống cống", safety["desc"])

    def test_slicer_not_installed_message(self):
        msg = slicer_not_installed_message("chitubox")
        self.assertIn("CHITUBOX", msg)
        self.assertIn("https://www.chitubox.com", msg)
        msg_pw = slicer_not_installed_message("photon_workshop")
        self.assertIn("Photon Workshop", msg_pw)
        self.assertIn("https://www.anycubic.com", msg_pw)
        self.assertEqual(slicer_not_installed_message("unknown_slicer"), "")
        # On this machine no resin slicer is installed; the check must
        # report that honestly instead of claiming otherwise.
        self.assertFalse(slicer_installed("chitubox"))
        self.assertFalse(slicer_installed("photon_workshop"))
        self.assertFalse(slicer_installed("lychee"))


if __name__ == "__main__":
    unittest.main()

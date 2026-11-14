"""
Creality K1 Max support (M.Studio fork, GĐ1): printer catalog, bundled K1 Max
presets with the Goku-print-verified PETG numbers, Bambu -> K1 Max project
retargeting, PETG advice cards and the 300x300x300 build volume.

Run from `backend/`:  .venv/bin/python -m unittest discover -s tests -v
K1 Max tests use the bundled presets and always run; Bambu-baseline tests need
Bambu Studio installed.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from build_volume_cards import oversized_objects  # noqa: E402
from cross_vendor_config import build_cross_vendor_config  # noqa: E402
from filament_profiles import (  # noqa: E402
    list_preset_options,
    policy_for_printer,
    resolve_filament_preset,
    resolve_process_preset,
    system_baseline,
)
from material_advice_cards import build_material_advice_cards  # noqa: E402
from printer_catalog import (  # noqa: E402
    PRINTERS,
    load_creality_k1max_bundle,
    needs_cross_vendor_retarget,
    profiles_for,
    source_vendor_of,
)
from profiler import resolve_profile  # noqa: E402
from slicer_launcher import slicer_installed  # noqa: E402

K1MAX = "Creality K1 Max 0.4 nozzle"

BAMBU_CFG = {
    "printer_settings_id": "Bambu Lab A1 0.4 nozzle",
    "printer_model": "Bambu Lab A1",
    "print_settings_id": "0.20mm Standard @BBL A1",
    "curr_bed_type": "Textured PEI Plate",
    "filament_settings_id": ["Bambu PETG HF @BBL A1"],
    "filament_type": ["PETG"],
    "filament_colour": ["#FFFFFF"],
    "filament_map": ["1"],
    "flush_volumes_matrix": ["0"],
    "layer_height": "0.12",
    "wall_loops": "3",
    "sparse_infill_density": "25%",
    "enable_support": "1",
    "version": "02.08.02.61",
}


class K1MaxCatalogTests(unittest.TestCase):
    def test_printer_is_corexy_enclosed_300mm(self):
        meta = PRINTERS[K1MAX]
        self.assertEqual(meta["vendor"], "creality")
        self.assertEqual(meta["vendor_label"], "Creality")
        self.assertEqual(meta["kinematics"], "corexy")
        self.assertTrue(meta["enclosed"])
        self.assertEqual(meta["nozzle"], "0.4")
        self.assertEqual(meta["slicer"], "creality_print")
        self.assertIsNone(meta["max_tools"])

    def test_bundle_machine_is_300x300x300(self):
        bundle = load_creality_k1max_bundle()
        machine = bundle["presets"][K1MAX]
        self.assertEqual(machine["printer_model"], "Creality K1 Max")
        self.assertEqual(machine["printable_height"], "300")
        self.assertIn("300x300", machine["printable_area"])
        self.assertEqual(bundle["default_process"][K1MAX], "0.20mm Standard @Creality K1 Max")
        self.assertIn("Goku", bundle["source"]["verification"])

    def test_petg_creality_resolves_to_compatible_preset(self):
        name = resolve_filament_preset(K1MAX, "PETG Creality")
        self.assertEqual(name, "Creality PETG @Creality K1 Max")
        compat = resolve_profile(name, profiles_for(K1MAX)).get("compatible_printers", [])
        self.assertIn(K1MAX, compat)

    def test_petg_numbers_are_the_goku_verified_ones(self):
        baseline = system_baseline(K1MAX, "Creality PETG @Creality K1 Max")
        self.assertEqual(baseline["nozzle_temperature_initial_layer"], ["245"])
        self.assertEqual(baseline["nozzle_temperature"], ["240"])
        self.assertEqual(baseline["textured_plate_temp_initial_layer"], ["75"])
        self.assertEqual(baseline["textured_plate_temp"], ["70"])
        self.assertEqual(baseline["filament_flow_ratio"], ["0.97"])
        self.assertEqual(baseline["filament_max_volumetric_speed"], ["12"])

    def test_process_preset_and_policy(self):
        self.assertEqual(resolve_process_preset(K1MAX), "0.20mm Standard @Creality K1 Max")
        policy = policy_for_printer("PETG Creality", K1MAX)
        self.assertEqual(policy["support_top_z_distance"], "0.2")
        self.assertEqual(policy["brim_object_gap"], "0.1")
        self.assertEqual(policy["z_hop_type"], "Spiral Lift")
        self.assertEqual(policy["seam_position"], "aligned_back")
        self.assertNotIn("retraction", str(policy).lower())

    def test_presets_endpoint_lists_k1max(self):
        opts = list_preset_options()
        ids = [p["id"] for p in opts["printers"]]
        self.assertIn(K1MAX, ids)
        self.assertIn("creality_print", opts["slicers"])
        self.assertEqual(opts["slicers"]["creality_print"]["label"], "Creality Print")
        petg = [f for f in opts["filaments"] if f["id"] == "PETG Creality"][0]
        self.assertEqual(petg["presets"][K1MAX], "Creality PETG @Creality K1 Max")
        self.assertEqual(petg["family"], "PETG")


class VendorDetectionTests(unittest.TestCase):
    def test_source_vendor(self):
        self.assertEqual(source_vendor_of(BAMBU_CFG), "bbl")
        self.assertEqual(source_vendor_of({"printer_settings_id": K1MAX}), "creality")
        self.assertEqual(source_vendor_of({"printer_model": "Creality K1 Max"}), "creality")

    def test_retarget_needed_only_across_vendors(self):
        self.assertTrue(needs_cross_vendor_retarget(BAMBU_CFG, K1MAX))
        self.assertFalse(needs_cross_vendor_retarget(BAMBU_CFG, "Bambu Lab P1S 0.4 nozzle"))
        self.assertFalse(needs_cross_vendor_retarget({"printer_settings_id": K1MAX}, K1MAX))


class CrossVendorConfigTests(unittest.TestCase):
    def setUp(self):
        self.cfg, self.plan, self.keys = build_cross_vendor_config(BAMBU_CFG, K1MAX, "PETG Creality")

    def test_identity_is_k1max_system_presets(self):
        cfg = self.cfg
        self.assertEqual(cfg["printer_settings_id"], K1MAX)
        self.assertEqual(cfg["printer_model"], "Creality K1 Max")
        self.assertEqual(cfg["print_settings_id"], "0.20mm Standard @Creality K1 Max")
        self.assertEqual(cfg["filament_settings_id"], ["Creality PETG @Creality K1 Max"])
        presets = profiles_for(K1MAX)
        for name in [cfg["print_settings_id"], *cfg["filament_settings_id"]]:
            self.assertIn(name, presets)

    def test_no_ams_keys_and_seam_is_aligned_back(self):
        cfg = self.cfg
        self.assertFalse([k for k in cfg if k.startswith("ams_")])
        # Preset values are per-slot lists in Orca-style configs.
        self.assertIn("aligned_back", cfg["seam_position"])
        self.assertIn("0.2", cfg["support_top_z_distance"])
        self.assertIn("0.1", cfg["brim_object_gap"])

    def test_temperatures_in_retargeted_config(self):
        cfg = self.cfg
        self.assertEqual(cfg["nozzle_temperature_initial_layer"], ["245"])
        self.assertEqual(cfg["nozzle_temperature"], ["240"])
        self.assertEqual(cfg["textured_plate_temp_initial_layer"], ["75"])
        self.assertEqual(cfg["textured_plate_temp"], ["70"])

    def test_slot_order_and_colour_kept(self):
        self.assertEqual(self.cfg["filament_colour"], ["#FFFFFF"])
        self.assertEqual(self.plan, {0: "PETG Creality"})


class AdviceAndVolumeTests(unittest.TestCase):
    def test_k1max_petg_advice_cards(self):
        cards = build_material_advice_cards(BAMBU_CFG, K1MAX, "PETG Creality", {})
        ids = [c["id"] for c in cards]
        self.assertIn("card_petg_drying", ids)
        self.assertIn("card_k1max_petg_enclosure", ids)
        self.assertIn("card_k1max_bed_cool", ids)
        enclosure = [c for c in cards if c["id"] == "card_k1max_petg_enclosure"][0]
        self.assertIn("1–2cm", enclosure["desc"])

    def test_build_volume_is_300mm(self):
        machine = resolve_profile(K1MAX, profiles_for(K1MAX))
        big = [{"name": "Goku bust", "size_mm": (200.0, 200.0, 400.0)}]
        self.assertEqual(len(oversized_objects(big, machine)), 1)
        fits = [{"name": "Goku head", "size_mm": (73.0, 71.0, 73.0)}]
        self.assertEqual(oversized_objects(fits, machine), [])


class SlicerLauncherTests(unittest.TestCase):
    def test_creality_print_not_installed_on_this_linux_box(self):
        # No Creality Print on the build VM: the launcher must say so plainly
        # instead of pretending it can open the slicer.
        self.assertFalse(slicer_installed("creality_print"))


if __name__ == "__main__":
    unittest.main()

"""
Resin-specific geometry checks for the Anycubic Photon Mono 4 — M.Studio
fork, GĐ2.

These checks are deliberately separate from the FDM rule engine
(`patcher.py` / `build_volume_cards.py`): resin failure modes are different
(suction cups, closed hollows trapping liquid resin, walls too thin to
survive curing, parts taller than a 165mm Z axis), and the FDM fixes
(brim, Z-hop, wall loops) do not apply.

Every function here is pure and works on plain numbers, so it can be tested
without a printer, a slicer, or a mesh file. Thresholds come from:
- Mono 4 build volume 153.4 x 87 x 165mm (Anycubic specification).
- Minimum wall thickness 1.2mm and the hollow + drain-hole rules, taken from
  the user's own MStudio Tách Part 3D tool, which already enforces them for
  resin parts.
- The tilt suggestion (30-45 deg) is the standard resin practice for
  avoiding large flat areas parallel to the build plate; it is advice, not a
  measured value.

Card shape matches the rest of LayerZero (`material_advice_cards._card`):
id / pillar / title / desc / pill_text / archetype / action_type / approved.
"""

from typing import Any

from resin_profiles import (
    MIN_DRAIN_HOLES,
    MIN_WALL_THICKNESS_MM,
    RESIN_BUILD_VOLUME_MM,
    RESIN_VAT_CAPACITY_ML,
    get_resin_preset,
)

# A flat area this large, printed parallel to the build plate, acts like a
# suction cup on every lift: it can rip the part off its supports or crack
# the FEP film. 1000 mm^2 (~32x32mm) is a conservative heuristic, not a
# measured threshold — the card says so.
SUCTION_CUP_FLAT_AREA_MM2 = 1000.0

# Support-size heuristic by part volume. Resin supports are light / medium /
# heavy by tip size, not by FDM tree settings; the exact tip diameters are
# chosen in the slicer, this only picks the class.
SUPPORT_VOLUME_LIMITS_CM3 = (10.0, 50.0)


def _card(card_id: str, title: str, desc: str, pill: str, archetype: str) -> dict[str, Any]:
    return {
        "id": card_id,
        "pillar": "safety",
        "object_id": "global",
        "object_tag": "Resin · Toàn bộ project",
        "archetype": archetype,
        "title": title,
        "desc": desc,
        "pill_text": pill,
        "action_type": "RESIN_ADVICE",
        "param_value": 0.0,
        "approved": False,
    }


def check_build_volume(
    size_mm: tuple[float, float, float],
    build_volume: tuple[float, float, float] = RESIN_BUILD_VOLUME_MM,
) -> list[dict[str, Any]]:
    """Warns when a part does not fit the Mono 4 (153.4 x 87 x 165mm).

    The footprint may be rotated on the plate (X/Y swap is allowed), but the
    height cannot: Z is fixed at 165mm. A part that fits in neither
    orientation must be split first — the user's MStudio Tách Part 3D tool
    does exactly that.
    """
    w, d, h = (float(v) for v in size_mm)
    bx, by, bz = build_volume
    fits_xy = (w <= bx and d <= by) or (w <= by and d <= bx)
    fits_z = h <= bz
    if fits_xy and fits_z:
        return []
    over = []
    if not fits_xy:
        over.append(f"mặt đáy {w:.0f}x{d:.0f}mm vượt khay {bx:.0f}x{by:.0f}mm")
    if not fits_z:
        over.append(f"cao {h:.0f}mm vượt chiều cao in {bz:.0f}mm")
    return [_card(
        "card_resin_exceeds_build_volume",
        f"Chi tiết vượt khổ in của Photon Mono 4 ({bx:.0f}x{by:.0f}x{bz:.0f}mm)",
        (
            f"Chi tiết {w:.0f}x{d:.0f}x{h:.0f}mm: {'; '.join(over)}. "
            "Mono 4 chỉ in được tối đa 153.4x87x165mm — tượng lớn như Goku/Vegeto "
            "bắt buộc phải tách part trước khi in (dùng MStudio Tách Part 3D), "
            "không thể scale cả tượng xuống vì sẽ mất chi tiết."
        ),
        f"Khổ in {bx:.0f}x{by:.0f}x{bz:.0f}mm",
        "Kích thước máy in",
    )]


def check_wall_thickness(min_wall_mm: float | None) -> list[dict[str, Any]]:
    """Warns when the thinnest wall is below 1.2mm (resin minimum)."""
    if min_wall_mm is None:
        return []
    if min_wall_mm >= MIN_WALL_THICKNESS_MM:
        return []
    return [_card(
        "card_resin_thin_wall",
        f"Thành mỏng nhất {min_wall_mm:.2f}mm — dưới mức tối thiểu resin 1.2mm",
        (
            f"Thành {min_wall_mm:.2f}mm mỏng hơn mức tối thiểu {MIN_WALL_THICKNESS_MM}mm "
            "cho in resin: chi tiết dễ nứt khi gỡ support, khi rửa và khi sấy UV. "
            "Tăng độ dày thành lên tối thiểu 1.2mm (tượng trưng bày nên để 2mm) "
            "hoặc in đặc thay vì rỗng ở vùng này."
        ),
        "Thành tối thiểu 1.2mm",
        "Độ dày thành",
    )]


def check_hollow(enclosed_volume: bool, drain_holes: int) -> list[dict[str, Any]]:
    """Hollow parts need drain holes; a closed hollow traps liquid resin.

    A hollow part with no drain holes will trap uncured resin inside: it
    leaks later, cracks the part from the inside, and wastes resin. Two
    holes minimum (inlet + outlet); one hole alone does not drain.
    """
    if not enclosed_volume:
        return []
    if drain_holes >= MIN_DRAIN_HOLES:
        return []
    return [_card(
        "card_resin_drain_holes",
        "Part rỗng nhưng chưa có đủ lỗ thoát resin",
        (
            f"Part rỗng ruột có {drain_holes} lỗ thoát — cần tối thiểu {MIN_DRAIN_HOLES} lỗ "
            "(1 lỗ vào, 1 lỗ ra) để resin lỏng chảy ra hết khi in xong. Rỗng kín "
            "sẽ nhốt resin chưa cure bên trong: sau này rò rỉ, nứt part từ trong ra, "
            "và phí resin. Đục lỗ ở mặt khuất (đáy, mặt sau) để không lộ khi trưng bày."
        ),
        f"Cần tối thiểu {MIN_DRAIN_HOLES} lỗ thoát",
        "Rỗng ruột",
    )]


def check_suction_cup(flat_base_area_mm2: float | None) -> list[dict[str, Any]]:
    """Warns when a large flat area sits parallel to the build plate."""
    if flat_base_area_mm2 is None or flat_base_area_mm2 < SUCTION_CUP_FLAT_AREA_MM2:
        return []
    return [_card(
        "card_resin_suction_cup",
        "Đáy phẳng lớn — nguy cơ hút chân không khi nhấc bàn",
        (
            f"Diện tích đáy phẳng khoảng {flat_base_area_mm2:.0f}mm² nằm song song với bàn in. "
            "Mỗi lần bàn nhấc lên, mặt phẳng này hút chặt vào film FEP như giác hút: "
            "có thể kéo bung part khỏi support hoặc rách film. Nghiêng part 30–45° "
            "để mặt phẳng không còn song song với bàn, hoặc khoét rỗng + đục lỗ thoát."
        ),
        "Nghiêng part 30–45°",
        "Hướng in",
    )]


def suggest_support_class(volume_mm3: float) -> str:
    """Light / medium / heavy resin supports by part volume (heuristic)."""
    cm3 = volume_mm3 / 1000.0
    if cm3 < SUPPORT_VOLUME_LIMITS_CM3[0]:
        return "light"
    if cm3 < SUPPORT_VOLUME_LIMITS_CM3[1]:
        return "medium"
    return "heavy"


def estimate_resin_ml(volume_mm3: float, hollow_fraction: float = 0.0) -> float:
    """Millilitres of resin for a part. Volume only — no density is assumed.

    1 mm^3 = 0.001 ml. `hollow_fraction` is the share of the volume removed
    by hollowing (0.0 = solid, e.g. 0.6 = 60% rỗng). Grams are deliberately
    NOT estimated: resin density is not in the preset (check the bottle).
    """
    if volume_mm3 <= 0:
        return 0.0
    hollow_fraction = min(max(hollow_fraction, 0.0), 0.95)
    return round(volume_mm3 / 1000.0 * (1.0 - hollow_fraction), 2)


def estimate_print_time_minutes(height_mm: float, resin_name: str = "Water-Wash Resin 2.0") -> float:
    """Rough print time from the resin preset: layers x time per layer.

    Time per layer = normal exposure + light-off delay + lift time + retract
    time. Bottom layers are slower (longer exposure) but few, so they are
    counted at the normal rate and the result is rounded down slightly by
    the caller if precision matters. This is an estimate for planning, not
    a slicer prediction.
    """
    preset = get_resin_preset(resin_name)
    if height_mm <= 0:
        return 0.0
    layers = height_mm / preset["layer_height_mm"]
    per_layer_s = (
        preset["normal_exposure_s"]
        + preset["light_off_delay_s"]
        + preset["z_lift_distance_mm"] / preset["z_lift_speed_mm_s"]
        + preset["z_lift_distance_mm"] / preset["z_retract_speed_mm_s"]
    )
    return round(layers * per_layer_s / 60.0, 1)


def build_resin_audit(
    size_mm: tuple[float, float, float],
    volume_mm3: float = 0.0,
    min_wall_mm: float | None = None,
    enclosed_volume: bool = False,
    drain_holes: int = 0,
    flat_base_area_mm2: float | None = None,
    hollow_fraction: float = 0.0,
    resin_name: str = "Water-Wash Resin 2.0",
) -> dict[str, Any]:
    """All resin checks for one part, plus resin usage and time estimates.

    Returns {"cards": [...], "estimates": {...}}. An empty cards list means
    no resin-specific problem was found — it does NOT mean the print is
    guaranteed (exposure still has to be confirmed against a test print).
    """
    cards: list[dict[str, Any]] = []
    cards += check_build_volume(size_mm)
    cards += check_wall_thickness(min_wall_mm)
    cards += check_hollow(enclosed_volume, drain_holes)
    cards += check_suction_cup(flat_base_area_mm2)
    ml = estimate_resin_ml(volume_mm3, hollow_fraction)
    return {
        "cards": cards,
        "estimates": {
            "resin_ml": ml,
            "vat_capacity_ml": RESIN_VAT_CAPACITY_ML,
            "vat_refills": 0 if ml <= RESIN_VAT_CAPACITY_ML else round(ml / RESIN_VAT_CAPACITY_ML, 1),
            "print_time_minutes": estimate_print_time_minutes(size_mm[2], resin_name),
            "support_class": suggest_support_class(volume_mm3),
            "resin": resin_name,
        },
    }

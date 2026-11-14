"""
Material-specific diagnostic cards (PLA / PLA Lite / PETG).

Most cards are `MATERIAL_ADVICE`: guidance the slicer cannot apply (drying, glue, door),
shown without an approve toggle. `SWITCH_BED_PLATE` is actionable: it moves the project to
Textured PEI when the vendor profile marks the current plate unsupported for this filament.

M.Studio fork, GĐ2: resin cards (Water-Wash Resin 2.0 on the Anycubic Photon Mono 4) are
returned instead of the FDM cards when the printer is a resin printer — bed plates, drying
and enclosure advice do not apply to resin. The resin preset numbers in these cards are
Anycubic's manufacturer-recommended values, NOT verified on the user's own Mono 4.
"""

from typing import Any

from filament_profiles import (
    BED_TYPE_LABEL,
    BED_TYPE_TEMP_KEY,
    PRINTERS,
    bed_type_of,
    describe_filament_slots,
    family_group,
    main_model_group,
    material_family,
    filament_base_name,
    policy_for,
)
from profiler import fmt_val


def _card(card_id: str, title: str, desc: str, pill: str, archetype: str,
          action: str = "MATERIAL_ADVICE", approved: bool = False) -> dict[str, Any]:
    return {
        "id": card_id,
        "pillar": "safety",
        "object_id": "global",
        "object_tag": "Vật liệu · Toàn bộ project",
        "archetype": archetype,
        "title": title,
        "desc": desc,
        "pill_text": pill,
        "action_type": action,
        "param_value": 0.0,
        "approved": approved,
    }


def _resin_advice_cards() -> list[dict[str, Any]]:
    """Resin advice for Water-Wash Resin 2.0 on the Photon Mono 4 (GĐ2).

    These are safety / handling cards, not slicer fixes — resin has no bed
    plate, no drying step and no enclosure door. Exposure numbers are
    Anycubic's manufacturer-recommended values (see `resin_profiles.py`).
    """
    return [
        _card(
            "card_resin_water_wash",
            "Rửa bằng nước sạch — KHÔNG dùng IPA",
            (
                "Water-Wash Resin 2.0 rửa được bằng nước sạch, KHÔNG dùng IPA. "
                "Rửa kỹ trong nước, để khô hẳn rồi mới sấy UV — part còn ướt mà sấy "
                "sẽ để lại vệt trắng. Thay nước rửa khi nước đã đục."
            ),
            "Rửa nước · Sấy UV sau khi khô",
            "Rửa & sấy",
        ),
        _card(
            "card_resin_safety",
            "Đeo găng + thông gió — KHÔNG đổ nước rửa resin xuống cống",
            (
                "Resin chưa cure gây kích ứng da và có hại nếu hít phải: đeo găng tay "
                "nitrile, mở cửa/thông gió khi in và rửa. Nước rửa có resin KHÔNG được "
                "đổ xuống cống — phơi nắng/UV cho resin trong nước kết tủa rồi lọc bỏ "
                "như rác thải nguy hại."
            ),
            "Găng nitrile · Thông gió · Không đổ cống",
            "An toàn",
        ),
        _card(
            "card_resin_exposure_starting_point",
            "Preset 2.4s là số hãng khuyến nghị — in test trước khi in thật",
            (
                "Preset Water-Wash Resin 2.0 (layer 0.05mm, exposure 2.4s, đáy 30s x 5 lớp) "
                "là số Anycubic khuyến nghị cho Photon Mono 4, CHƯA phải số đã in thành công "
                "trên máy của bạn. In 1 mẫu test exposure (cones / AmeraLabs) trước, rồi "
                "chỉnh theo kết quả thật. Nhiệt độ phòng 20–35°C: hè trên 30°C giảm 0.5–1s, "
                "đông dưới 10°C tăng 0.5–1s."
            ),
            "Exposure 2.4s · In test trước",
            "Preset khởi điểm",
        ),
        _card(
            "card_resin_hollow_drain",
            "Part rỗng: thành tối thiểu 1.2mm, tối thiểu 2 lỗ thoát resin",
            (
                "Rỗng ruột tiết kiệm resin nhưng thành dưới 1.2mm dễ nứt khi rửa và sấy UV. "
                "Mọi hốc kín cần tối thiểu 2 lỗ thoát (1 vào, 1 ra) để resin lỏng chảy hết — "
                "rỗng kín sẽ nhốt resin chưa cure bên trong và nứt part từ trong ra. "
                "Đục lỗ ở mặt khuất (đáy, mặt sau) để không lộ khi trưng bày."
            ),
            "Thành ≥1.2mm · Tối thiểu 2 lỗ thoát",
            "Rỗng ruột",
        ),
    ]


def build_material_advice_cards(
    orig_cfg: dict[str, Any],
    printer: str,
    filament: str,
    sys_def: dict[str, Any],
    has_screws: bool = False,
) -> list[dict[str, Any]]:
    # GĐ2: resin printers get resin cards instead of the FDM ones.
    if PRINTERS.get(printer, {}).get("technology") == "resin":
        return _resin_advice_cards()
    family = material_family(filament_base_name(filament))
    label = policy_for(filament)["label"]
    enclosed = PRINTERS.get(printer, {}).get("enclosed", False)
    vendor = PRINTERS.get(printer, {}).get("vendor_label", "Bambu Lab")
    cards: list[dict[str, Any]] = []

    # 1. Author designed the project for a different material family than the one selected.
    author_group = main_model_group(describe_filament_slots(orig_cfg)) if orig_cfg else None
    if author_group and author_group != family_group(family):
        cards.append(_card(
            "card_material_mismatch",
            f"File gốc dùng {author_group}, bạn đang chọn {label}",
            (
                f"Tác giả cấu hình project cho {author_group}. LayerZero sẽ áp nhiệt độ, quạt, flow và khe hở Support "
                f"theo profile {label} của {vendor} cho các slot thân mẫu; slot Support/Interface được giữ nguyên."
            ),
            f"Chuyển thân mẫu sang {label} · Giữ nguyên slot Support",
            "Đổi vật liệu",
        ))

    # 2. Current plate is unsupported for this filament (vendor temperature 0).
    bed = bed_type_of(orig_cfg, printer)
    bed_key = f"{BED_TYPE_TEMP_KEY[bed]}_initial_layer"
    # Only a vendor value explicitly set to 0 means "unsupported"; a missing key means no profiles installed.
    if bed_key in sys_def and fmt_val(sys_def[bed_key]) in ("0", ""):
        cards.append(_card(
            "card_switch_bed_plate",
            f"{label} không hỗ trợ {BED_TYPE_LABEL[bed]}",
            (
                f"Profile {vendor} đặt nhiệt độ {BED_TYPE_LABEL[bed]} = 0 cho {label}, tức là không nên in trên mặt bàn này "
                f"(PETG có thể dính chết vào Cool Plate; PLA không bám tốt trên Engineering Plate). "
                f"Hãy thay sang tấm Textured PEI trên máy."
            ),
            "Chuyển project sang Textured PEI Plate",
            "Mặt bàn in",
            action="SWITCH_BED_PLATE",
            approved=True,
        ))

    if family == "PETG":
        cards.append(_card(
            "card_petg_drying",
            "Sấy khô PETG trước khi in",
            (
                "PETG hút ẩm nhanh. Nhựa ẩm gây kéo tơ, bọt khí, bề mặt rỗ và lớp in yếu. "
                "Bambu khuyến nghị sấy khoảng 65°C trong 8 giờ; giữ cuộn nhựa trong hộp kín có hạt hút ẩm khi in lâu."
            ),
            "Sấy 65°C · 8 giờ trước khi in",
            "Bảo quản vật liệu",
        ))
        if bed == "High Temp Plate":
            cards.append(_card(
                "card_petg_smooth_pei_glue",
                "PETG trên Smooth PEI: bôi keo làm lớp tách",
                (
                    "PETG có thể bám quá chặt vào Smooth PEI và làm rách lớp PEI khi gỡ mẫu. "
                    "Bôi một lớp keo dán mỏng để làm lớp tách (release agent), hoặc dùng Textured PEI không cần keo."
                ),
                "Bôi keo mỏng hoặc dùng Textured PEI",
                "Mặt bàn in",
            ))

    if family in ("PLA", "PLA_LITE") and enclosed:
        cards.append(_card(
            "card_pla_open_enclosure",
            "Mở cửa hoặc nắp máy khi in PLA",
            (
                "PLA mềm ra ở khoảng 45°C. Trên máy kín như P1S/X1C, buồng in nóng lên có thể gây kẹt nhựa (heat creep) "
                "và cong vênh. Mở cửa trước hoặc nắp trên khi in PLA."
            ),
            "Mở cửa trước / nắp trên",
            "Máy in kín",
        ))

    if family == "PLA_LITE" and has_screws:
        cards.append(_card(
            "card_pla_lite_strength",
            "PLA Lite bám lớp yếu hơn PLA Basic",
            (
                "PLA Lite là PLA giá rẻ, phù hợp mẫu trưng bày và bản thử. Với ốc vít và chi tiết chịu lực, "
                "LayerZero tăng số vòng tường và nhiệt độ đầu phun; nếu cần bền hơn nữa, hãy in bằng PLA Basic."
            ),
            "Tăng tường + 5°C đầu phun · Cân nhắc PLA Basic",
            "Độ bền vật liệu",
        ))

    return cards

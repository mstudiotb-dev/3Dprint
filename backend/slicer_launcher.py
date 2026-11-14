"""
Finds the installed slicer for a printer and opens an exported .3mf in it.

Bambu Studio opens Bambu Lab printers; Snapmaker Orca opens the Snapmaker U1. Snapmaker Orca's
`snapmaker-orca://open?file=` URL scheme only downloads HTTP(S) URLs, so local files are passed
to the app directly: by bundle id on macOS, by executable path on Windows and Linux.

M.Studio fork, GĐ2: CHITUBOX opens the Anycubic Photon Mono 4 (resin) — it is the slicer
the user actually uses (confirmed 14/11/2026); Photon Workshop is only a secondary option
and Lychee Slicer a third. Resin workflow starts from an STL, not a .3mf — `open_in_slicer`
still works the same way (pass the file path to the app); CHITUBOX itself slices to the
.ctb print file, LayerZero does not write .ctb. Windows paths for CHITUBOX / Photon
Workshop / Lychee are candidate paths, unverified on the user's PC —
`slicer_installed` reports honestly and `slicer_not_installed_message` tells the user where
to download it instead of silently falling back.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

MAC_APPS: dict[str, dict[str, object]] = {
    "bambu_studio": {"bundle_id": "com.bambulab.bambu-studio", "names": ("BambuStudio.app", "Bambu Studio.app")},
    "snapmaker_orca": {"bundle_id": "com.snapmaker.snapmaker-orca", "names": ("Snapmaker Orca.app", "Snapmaker_Orca.app")},
    # GĐ2: CHITUBOX is the user's resin slicer. Its macOS bundle id is unverified — the
    # `mdfind` lookup uses it, but the .app name list is the primary match. Photon Workshop
    # bundle id is likewise unverified; Lychee's is com.mango3d.lychee.
    "chitubox": {"bundle_id": "com.chitubox.chitubox", "names": ("CHITUBOX.app", "Chitubox.app")},
    "photon_workshop": {"bundle_id": "com.anycubic.photon-workshop", "names": ("Photon Workshop.app", "PhotonWorkshop.app")},
    "lychee": {"bundle_id": "com.mango3d.lychee", "names": ("LycheeSlicer.app", "Lychee Slicer.app")},
}
WINDOWS_EXES: dict[str, tuple[str, str]] = {
    "bambu_studio": ("Bambu Studio", "bambu-studio.exe"),
    "snapmaker_orca": ("Snapmaker_Orca", "snapmaker-orca.exe"),
    # GĐ2: candidate exe names/paths — unverified on the user's PC. `_windows_exe` only
    # checks %ProgramW6432% / %ProgramFiles% / %ProgramFiles(x86)% / %LOCALAPPDATA% roots.
    # CHITUBOX's usual install folder is "CHITUBOX" with exe "CHITUBOX.exe".
    "chitubox": ("CHITUBOX", "CHITUBOX.exe"),
    "photon_workshop": ("Photon Workshop", "PhotonWorkshop.exe"),
    "lychee": ("Lychee Slicer", "LycheeSlicer.exe"),
}
LINUX_COMMANDS: dict[str, tuple[str, ...]] = {
    "bambu_studio": ("bambu-studio", "BambuStudio"),
    "snapmaker_orca": ("snapmaker-orca", "Snapmaker_Orca"),
    "chitubox": ("chitubox", "CHITUBOX"),
    "photon_workshop": ("photon-workshop", "PhotonWorkshop"),
    "lychee": ("lychee-slicer", "LycheeSlicer"),
}

# Where to download a slicer that is not installed, shown to the user as-is.
SLICER_DOWNLOADS: dict[str, tuple[str, str]] = {
    "bambu_studio": ("Bambu Studio", "https://bambulab.com/en/download/studio"),
    "snapmaker_orca": ("Snapmaker Orca", "https://github.com/Snapmaker/OrcaSlicer/releases/latest"),
    "chitubox": ("CHITUBOX", "https://www.chitubox.com"),
    "photon_workshop": ("Photon Workshop", "https://www.anycubic.com"),
    "lychee": ("Lychee Slicer", "https://mango3d.io/lychee-slicer/"),
}


def _mac_app_path(slicer: str) -> Path | None:
    info = MAC_APPS[slicer]
    for root in (Path("/Applications"), Path.home() / "Applications"):
        for name in info["names"]:  # type: ignore[union-attr]
            if (root / name).exists():
                return root / name
    try:
        out = subprocess.run(
            ["mdfind", f"kMDItemCFBundleIdentifier == '{info['bundle_id']}'"],
            capture_output=True, text=True, timeout=3, check=False,
        ).stdout.split("\n")[0].strip()
        return Path(out) if out else None
    except (OSError, subprocess.SubprocessError):
        return None


def _windows_exe(slicer: str) -> Path | None:
    folder, exe = WINDOWS_EXES[slicer]
    for env in ("ProgramW6432", "ProgramFiles", "ProgramFiles(x86)", "LOCALAPPDATA"):
        base = os.environ.get(env)
        if base and (Path(base) / folder / exe).exists():
            return Path(base) / folder / exe
    return None


def _linux_command(slicer: str) -> str | None:
    return next((c for c in LINUX_COMMANDS[slicer] if shutil.which(c)), None)


def slicer_installed(slicer: str) -> bool:
    if slicer not in MAC_APPS:
        return False
    if sys.platform == "darwin":
        return _mac_app_path(slicer) is not None
    if sys.platform == "win32":
        return _windows_exe(slicer) is not None
    return _linux_command(slicer) is not None


def slicer_not_installed_message(slicer: str) -> str:
    """Vietnamese message shown when the printer's slicer is not installed.

    Returns an empty string for unknown slicers (nothing useful to say) — the
    caller shows the file in the file manager instead.
    """
    info = SLICER_DOWNLOADS.get(slicer)
    if not info:
        return ""
    label, url = info
    return (
        f"Chưa tìm thấy {label} trên máy này nên không mở tự động được. "
        f"File đã lưu sẵn — tải {label} tại {url} rồi mở file bằng tay, "
        "hoặc bấm nút mở thư mục để lấy file."
    )


def open_in_slicer(slicer: str, target: Path) -> None:
    """Opens `target` in the given slicer, falling back to the system default .3mf handler."""
    try:
        if sys.platform == "darwin":
            app = _mac_app_path(slicer)
            subprocess.Popen(["open", "-a", str(app), str(target)] if app else ["open", str(target)])
        elif sys.platform == "win32":
            exe = _windows_exe(slicer)
            if exe:
                subprocess.Popen([str(exe), str(target)])
            else:
                os.startfile(str(target))  # type: ignore[attr-defined]
        else:
            cmd = _linux_command(slicer)
            subprocess.Popen([cmd, str(target)] if cmd else ["xdg-open", str(target)])
    except Exception:
        reveal_in_file_manager(target)


def reveal_in_file_manager(target: Path) -> None:
    """Reveals the exported file in macOS Finder, Windows Explorer, or the Linux file manager."""
    try:
        if sys.platform == "darwin":
            subprocess.Popen(["open", "-R", str(target)])
        elif sys.platform == "win32":
            subprocess.Popen(["explorer", f"/select,{target}"])
        else:
            subprocess.Popen(["xdg-open", str(target.parent)])
    except Exception:
        pass

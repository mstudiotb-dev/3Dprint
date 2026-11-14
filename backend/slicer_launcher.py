"""
Finds the installed slicer for a printer and opens an exported .3mf in it.

Bambu Studio opens Bambu Lab printers; Snapmaker Orca opens the Snapmaker U1; Creality Print
opens the Creality K1 Max (M.Studio fork, GĐ1). Snapmaker Orca's `snapmaker-orca://open?file=`
URL scheme only downloads HTTP(S) URLs, so local files are passed to the app directly: by
bundle id on macOS, by executable path on Windows and Linux.

Creality Print on Windows is looked up under the usual install folders; if it is not found
the caller falls back to the system's default .3mf handler and the user should open the
exported file in Creality Print by hand — the launcher never pretends it opened the app.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

MAC_APPS: dict[str, dict[str, object]] = {
    "bambu_studio": {"bundle_id": "com.bambulab.bambu-studio", "names": ("BambuStudio.app", "Bambu Studio.app")},
    "snapmaker_orca": {"bundle_id": "com.snapmaker.snapmaker-orca", "names": ("Snapmaker Orca.app", "Snapmaker_Orca.app")},
}
WINDOWS_EXES: dict[str, tuple[str, str]] = {
    "bambu_studio": ("Bambu Studio", "bambu-studio.exe"),
    "snapmaker_orca": ("Snapmaker_Orca", "snapmaker-orca.exe"),
}
# Creality Print's install folder / exe name varies by version, so try the usual
# candidates in order instead of guessing a single path.
WINDOWS_EXE_CANDIDATES: dict[str, tuple[tuple[str, str], ...]] = {
    "creality_print": (
        ("Creality Print", "CrealityPrint.exe"),
        ("Creality Print", "Creality Print.exe"),
        ("Creality Print 7.3", "CrealityPrint.exe"),
        ("Creality Print 7.3", "Creality Print.exe"),
    ),
}
LINUX_COMMANDS: dict[str, tuple[str, ...]] = {
    "bambu_studio": ("bambu-studio", "BambuStudio"),
    "snapmaker_orca": ("snapmaker-orca", "Snapmaker_Orca"),
    "creality_print": ("creality-print", "CrealityPrint"),
}


def _mac_app_path(slicer: str) -> Path | None:
    if slicer not in MAC_APPS:
        return None  # no verified macOS bundle id for this slicer yet; caller falls back
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
    candidates: tuple[tuple[str, str], ...] = WINDOWS_EXE_CANDIDATES.get(
        slicer, (WINDOWS_EXES[slicer],) if slicer in WINDOWS_EXES else ()
    )
    for folder, exe in candidates:
        for env in ("ProgramW6432", "ProgramFiles", "ProgramFiles(x86)", "LOCALAPPDATA"):
            base = os.environ.get(env)
            if base and (Path(base) / folder / exe).exists():
                return Path(base) / folder / exe
    return None


def _linux_command(slicer: str) -> str | None:
    if slicer not in LINUX_COMMANDS:
        return None
    return next((c for c in LINUX_COMMANDS[slicer] if shutil.which(c)), None)


def slicer_installed(slicer: str) -> bool:
    if slicer not in MAC_APPS and slicer not in WINDOWS_EXES and slicer not in WINDOWS_EXE_CANDIDATES and slicer not in LINUX_COMMANDS:
        return False
    if sys.platform == "darwin":
        return _mac_app_path(slicer) is not None
    if sys.platform == "win32":
        return _windows_exe(slicer) is not None
    return _linux_command(slicer) is not None


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

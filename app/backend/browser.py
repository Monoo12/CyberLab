"""Apertura del navegador real del sistema en modo app (paso `connect`).

Multiplataforma: intenta Chrome/Chromium/Edge en modo --app (sin barra de
direcciones); si no encuentra ninguno, cae a webbrowser.open. Devuelve el Popen
(si abrio un binario) para poder cerrarlo en el reset de la mision.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import webbrowser

# Candidatos por SO (nombre en PATH o ruta tipica)
_WINDOWS = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]
_LINUX = ["google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "microsoft-edge"]


def _find_browser() -> str | None:
    import os

    candidates = _WINDOWS if sys.platform.startswith("win") else _LINUX
    for c in candidates:
        if "/" in c or "\\" in c:
            if os.path.exists(c):
                return c
        else:
            found = shutil.which(c)
            if found:
                return found
    return None


def open_app_mode(url: str, kiosk: bool = False):
    """Abre `url` en modo app. Devuelve subprocess.Popen o None."""
    browser = _find_browser()
    if browser:
        args = [browser, f"--app={url}"]
        if kiosk:
            args.append("--kiosk")
        try:
            return subprocess.Popen(args)
        except Exception as exc:
            print(f"[browser] fallo modo app ({exc}); uso webbrowser")
    webbrowser.open(url)
    return None

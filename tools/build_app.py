"""Genera el bundle portable de la app con PyInstaller.

Uso (en la PC destino, corriendo en SU sistema operativo):
    python tools/build_app.py

Resultado: dist/CyberLab/  (carpeta autocontenida). Se copia config.example.toml
como config.toml externo y editable junto al ejecutable, si no existe.

PyInstaller NO cross-compila: para un .exe de Windows correr esto en Windows;
para un binario de Linux, correrlo en Linux. Misma base de codigo, dos artefactos.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main():
    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        print("Falta PyInstaller:  pip install -r requirements-dev.txt")
        sys.exit(1)

    cmd = [sys.executable, "-m", "PyInstaller", "--noconfirm", str(ROOT / "cyberlab.spec")]
    print("$", " ".join(cmd))
    subprocess.run(cmd, cwd=ROOT, check=True)

    dist = ROOT / "dist" / "CyberLab"
    cfg = dist / "config.toml"
    if dist.exists() and not cfg.exists():
        shutil.copyfile(ROOT / "config.example.toml", cfg)
        print("[build] config.toml externo copiado a", cfg)
    print("[build] listo ->", dist)


if __name__ == "__main__":
    main()

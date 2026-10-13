# -*- mode: python ; coding: utf-8 -*-
# Spec de PyInstaller para la app del visitante (Cyber Lab).
# Build one-folder (mas robusto para tkinter/customtkinter).
# config.toml queda EXTERNO y editable junto al ejecutable (no se embebe).
import os

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

datas = collect_data_files("customtkinter")
# Incluir iconos/pngs del panel visual SOLO si la carpeta existe y tiene algo util.
# En un clon limpio puede no existir (git no versiona carpetas vacias, salvo el
# .gitkeep): sin esta guarda, PyInstaller aborta con "Unable to find app/assets".
if os.path.isdir("app/assets") and any(
    f != ".gitkeep" for f in os.listdir("app/assets")
):
    datas += [("app/assets", "app/assets")]

hiddenimports = (
    collect_submodules("customtkinter")
    + ["paramiko", "serial", "PIL", "PIL.ImageTk"]
)

a = Analysis(
    ["app/main.py"],
    pathex=["."],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="CyberLab",
    debug=False,
    strip=False,
    upx=False,
    console=False,      # app GUI (sin consola)
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="CyberLab",
)

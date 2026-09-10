# -*- mode: python ; coding: utf-8 -*-
# Spec de PyInstaller para la app del visitante (Cyber Lab).
# Build one-folder (mas robusto para tkinter/customtkinter).
# config.toml queda EXTERNO y editable junto al ejecutable (no se embebe).
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

datas = collect_data_files("customtkinter")
# incluir iconos/pngs del panel visual si existen
datas += [("app/assets", "app/assets")]

hiddenimports = (
    collect_submodules("customtkinter")
    + ["paramiko", "serial", "PIL", "PIL.ImageTk", "nmap"]
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

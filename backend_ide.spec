# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller specification file for Backend Development IDE on Windows and cross-platform."""

import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_all, collect_data_files, collect_submodules

block_cipher = None

# Collect all resources and dynamic imports for heavy dependencies
datas = [
    ("src/backend_ide/ui/resources", "backend_ide/ui/resources"),
]
binaries = []
hiddenimports = [
    "PySide6",
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtWidgets",
    "PySide6.QtSvg",
    "PySide6.QtPrintSupport",
    "qtawesome",
    "psycopg",
    "pymysql",
    "pyodbc",
    "sqlite3",
    "sqlalchemy",
    "pydantic",
    "jinja2",
    "sqlglot",
    "structlog",
    "keyring",
    "backend_ide",
]

# Collect all qtawesome fonts and icons
qta_datas, qta_binaries, qta_hidden = collect_all("qtawesome")
datas.extend(qta_datas)
binaries.extend(qta_binaries)
hiddenimports.extend(qta_hidden)

# Collect PySide6 plugins
pyside_datas, pyside_binaries, pyside_hidden = collect_all("PySide6")
datas.extend(pyside_datas)
binaries.extend(pyside_binaries)
hiddenimports.extend(pyside_hidden)

a = Analysis(
    ["src/backend_ide/main.py"],
    pathex=["src"],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "numpy", "pandas"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="BackendDevelopmentIDE",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # Windowed GUI application
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="BackendDevelopmentIDE",
)

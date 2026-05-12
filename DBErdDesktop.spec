# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_all


pyside_datas, pyside_binaries, pyside_hiddenimports = collect_all("PySide6")
sqlalchemy_datas, sqlalchemy_binaries, sqlalchemy_hiddenimports = collect_all("sqlalchemy")

hiddenimports = [
    *pyside_hiddenimports,
    *sqlalchemy_hiddenimports,
    "pymysql",
    "psycopg",
    "psycopg_binary",
    "pyodbc",
    "oracledb",
    "sshtunnel",
    "paramiko",
    "cryptography.fernet",
    "greenlet",
    "sqlalchemy.dialects.mysql.pymysql",
    "sqlalchemy.dialects.postgresql.psycopg",
    "sqlalchemy.dialects.mssql.pyodbc",
    "sqlalchemy.dialects.oracle.oracledb",
]

a = Analysis(
    ["run.py"],
    pathex=[],
    binaries=[*pyside_binaries, *sqlalchemy_binaries],
    datas=[*pyside_datas, *sqlalchemy_datas, ("db_erd_desktop/qml", "db_erd_desktop/qml")],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="DBErdDesktop",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

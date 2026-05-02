# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

project_dir = Path.cwd()
icon_file = project_dir / 'assets' / 'lumidesk.ico'
version_file = project_dir / 'version_info.txt'

hiddenimports = []
hiddenimports += collect_submodules('holidays')
hiddenimports += collect_submodules('lunar_python')

datas = []
datas += collect_data_files('holidays')
datas += collect_data_files('lunar_python')
datas += [(str(project_dir / 'assets'), 'assets')]

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[str(project_dir)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='LumiDesk',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(icon_file),
    version=str(version_file),
)

# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['scripts\\main_pipeline.py'],
    pathex=[],
    binaries=[],
    datas=[('scripts\\blender_worker.py', '.'), ('scripts\\blender_extract.py', '.'), ('scripts\\blender_unwrap_bake.py', '.')],
    hiddenimports=['scripts.meshy_feeder', 'requests'],
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
    name='chriseurolog3d',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

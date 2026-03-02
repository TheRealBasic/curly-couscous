# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['run.py'],
    pathex=[],
    binaries=[],
    datas=[('templates', 'templates'), ('static', 'static'), ('config.yaml', '.')],
    hiddenimports=[
        'uvicorn.logging',
        'uvicorn.loops',
        'uvicorn.protocols',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # `websockets` is optional for this app and can break modulegraph analysis on
    # older Python builds (for example 3.10.0). We do not serve websocket
    # endpoints, so excluding it keeps the executable HTTP dashboard functional.
    excludes=['websockets', 'uvicorn.protocols.websockets.websockets_impl'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='gasdock-cert-manager',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
)

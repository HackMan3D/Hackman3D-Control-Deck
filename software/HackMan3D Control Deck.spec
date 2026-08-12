# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_submodules

hiddenimports = [
    'AppKit', 'ApplicationServices', 'Foundation', 'Quartz', 'objc',
]
hiddenimports += collect_submodules('pynput')


a = Analysis(
    ['run.py'],
    pathex=['src'],
    binaries=[],
    datas=[('src/hackman_control_deck/assets', 'hackman_control_deck/assets')],
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
    [],
    exclude_binaries=True,
    name='HackMan3D Control Deck',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['src/hackman_control_deck/assets/hcd_app_icon.icns'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='HackMan3D Control Deck',
)
app = BUNDLE(
    coll,
    name='HackMan3D Control Deck.app',
    icon='src/hackman_control_deck/assets/hcd_app_icon.icns',
    bundle_identifier='com.hackman3d.control-deck',
    info_plist={
        'CFBundleShortVersionString': '1.5.5',
        'CFBundleVersion': '1.5.5',
        'LSMinimumSystemVersion': '12.0',
    },
)

# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files
from PyInstaller.utils.hooks import collect_dynamic_libs

datas = []
binaries = []
datas += collect_data_files('vosk')
binaries += collect_dynamic_libs('vosk')

# Add logo file to bundled data
datas += [('logo_inlader.jpg', '.')]

# Add Vosk model folder to bundled data
datas += [('vosk-model-small-pl-0.22', 'vosk-model-small-pl-0.22')]


a = Analysis(
    ['simple_gui.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=['vosk', 'vosk.Model', 'vosk.KaldiRecognizer'],
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
    name='RobotDrawingSystem',
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
    icon=['insta.png'],
)

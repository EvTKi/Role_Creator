# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['ui.py'],
    pathex=['.'],
    binaries=[],
    datas=[('config.json', '.'), ('modules', 'modules')],
    hiddenimports=['main', 'ui', 'modules.config_manager', 'modules.csv_processor', 'modules.csv_reader', 'modules.file_manager', 'modules.logger_manager', 'modules.xml_generator', 'PyQt5', 'PyQt5.QtWidgets', 'PyQt5.QtCore', 'PyQt5.QtGui', 'lxml', 'lxml.etree', 'lxml._elementpath', 'chardet', 'chardet.universaldetector'],
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
    name='Конвертер CSV-RDF',
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

# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path
block_cipher = None

# Spec executes with working directory set to project root; use '.' as pathex
project_root = Path('.')
pathex = [str(project_root.resolve())]

a = Analysis(
    ['main.py'],
    pathex=pathex,
    binaries=[
        ('C:\\Windows\\System32\\msvcp140.dll', '.'),
        ('C:\\Windows\\System32\\vcruntime140.dll', '.'),
        ('C:\\Windows\\System32\\vcruntime140_1.dll', '.')
    ],
    datas=[
        (str(project_root / 'assets'), 'assets'),
        (str(project_root / 'version.json'), '.'),
        (str(project_root / 'file_version_info.txt'), '.'),
    ],
    hiddenimports=[
        'winrt.windows.ui.notifications',
        'winrt.windows.data.xml.dom',
        'winrt._winrt_windows_ui_notifications',
        'winrt._winrt_windows_data_xml_dom',
        'winrt.windows.security.credentials.ui',
        'winrt.windows.security',
        'winrt._winrt_windows_security_credentials_ui',
        'winrt.windows.foundation',
        'winrt.windows.foundation.collections',
        'winrt._winrt_windows_foundation',
        'winrt._winrt_windows_foundation_collections',
        'winrt.runtime',
        'winrt._winrt',
        'PySide6.QtNetwork',
        'plyer.platforms.win.notification',
        'appdirs',
        'win32com',
        'win32com.client',
        'win32com.propsys',
        'win32api',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    name='DigitalWellbeing',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon=str(project_root / 'assets' / 'icons' / 'app_icon.ico'),
    version=str(project_root / 'file_version_info.txt') if (project_root / 'file_version_info.txt').exists() else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    name='DigitalWellbeing',
)

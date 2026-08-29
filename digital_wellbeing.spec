# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path
block_cipher = None

# Spec executes with working directory set to project root; use '.' as pathex
project_root = Path('.')
pathex = [str(project_root.resolve())]

a = Analysis(
    ['main.py'],
    pathex=pathex,
    binaries=[],
    datas=[
        (str(project_root / 'assets'), 'assets'),
        (str(project_root / 'version.json'), '.'),
        (str(project_root / 'file_version_info.txt'), '.'),
    ],
    hiddenimports=[
        # WinRT Windows Hello / UserConsentVerifier
        # PyInstaller cannot auto-detect these due to dynamic WinRT loading
        'winrt.windows.security.credentials.ui',
        'winrt.windows.security',
        'winrt._winrt_windows_security_credentials_ui',
        'winrt.windows.foundation',
        'winrt.windows.foundation.collections',
        'winrt._winrt_windows_foundation',
        'winrt._winrt_windows_foundation_collections',
        'winrt.runtime',
        'winrt._winrt',
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
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

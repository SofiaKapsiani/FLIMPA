# PyInstaller spec for FLIMPA 2.0.0 (macOS .app / Windows .exe)
# Usage: pyinstaller --clean --noconfirm FLIMPA.spec
#
# Windows → single-file dist/FLIMPA.exe
# macOS   → folder + FLIMPA.app bundle (onefile is slow/fragile on macOS GUIs)

import sys
from pathlib import Path

ROOT = Path(SPECPATH)

block_cipher = None
ONEFILE = sys.platform.startswith("win")

datas = [
    (str(ROOT / "icon"), "icon"),
    (str(ROOT / "sample_data"), "sample_data"),
]

hiddenimports = [
    "PySide6.QtSvg",
    "skimage.filters",
    "skimage.morphology",
    "skimage.measure",
    "skimage.segmentation",
]

a = Analysis(
    [str(ROOT / "main.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
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

if ONEFILE:
    # Single standalone .exe (all libraries packed inside)
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.zipfiles,
        a.datas,
        [],
        name="FLIMPA",
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
        icon=str(ROOT / "icon" / "icon_f.ico"),
    )
else:
    # Folder build + .app on macOS
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name="FLIMPA",
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
        icon=str(ROOT / "icon" / "icon_f.ico"),
    )

    coll = COLLECT(
        exe,
        a.binaries,
        a.zipfiles,
        a.datas,
        strip=False,
        upx=True,
        upx_exclude=[],
        name="FLIMPA",
    )

    if sys.platform == "darwin":
        app = BUNDLE(
            coll,
            name="FLIMPA.app",
            icon=str(ROOT / "icon" / "icon_f.ico"),
            bundle_identifier="org.flimpa.app",
            version="2.0.0",
        )

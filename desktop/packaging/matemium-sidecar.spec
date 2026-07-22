# PyInstaller spec — Matemium engine sidecar (desktop)
#
# Build:
#   ./desktop/scripts/build-sidecar.sh
#
# Output:
#   dist/matemium-sidecar                    (Linux/macOS)
#   dist/matemium-sidecar.exe                (Windows)
#
# Runtime deps (not bundled — user/system must provide):
#   ffmpeg, pdflatex/TeX Live (see desktop/packaging/README.md)
#
# Tauri externalBin:
#   desktop/src-tauri/binaries/matemium-sidecar-<target-triple>

import sys
from pathlib import Path

from PyInstaller.utils.hooks import (
    collect_data_files,
    collect_dynamic_libs,
    collect_submodules,
    copy_metadata,
)

ROOT = Path(SPECPATH).resolve().parent.parent
HOOKS = Path(SPECPATH).resolve() / "hooks"

block_cipher = None

# Manim + engine graph
# NOTE (PAD Phase 1 + Phase 10): We keep full collection so that lazy imports inside handlers
# (matemium/lazy.py + per-function imports) succeed at runtime in the frozen binary.
# The "minimal control plane" is achieved at *runtime* (no top-level import of manim/canvas
# when the sidecar process starts — ping/get_status stay cheap).
# Intelligence features (lancedb etc) are optional and loaded lazily; not forced into base binary.
# See build scripts for size guards and asset manifest handling (separate from binary).
# Future work may split lite vs full or use PyInstaller's runtime hooks / multipackage.
hiddenimports = []
hiddenimports += collect_submodules("manim")
hiddenimports += collect_submodules("canvas")
hiddenimports += collect_submodules("matemium")
hiddenimports += collect_submodules("tiktoken_ext")
hiddenimports += collect_submodules("binaryornot")
hiddenimports += collect_submodules("manimpango")
hiddenimports += [
    "manim.__main__",
    "manim._config",
    "manim.renderer.cairo_renderer",
    "manim.renderer.opengl_renderer",
    "manimpango",
    "manimpango.utils",
    "manimpango.register_font",
    "importlib.metadata",
    "email.utils",
    "xml.etree.ElementTree",
]

binaries = []
binaries += collect_dynamic_libs("manimpango")
binaries += collect_dynamic_libs("av")

datas = []
datas += collect_data_files("manim", include_py_files=False)
datas += collect_data_files("matemium", includes=["templates/**"])
datas += collect_data_files("binaryornot", include_py_files=True)

# Package metadata (manim, pillow, etc.)
for pkg in (
    "manim",
    "pillow",
    "numpy",
    "scipy",
    "networkx",
    "mapbox-earcut",
):
    try:
        datas += copy_metadata(pkg)
    except Exception:
        pass

a = Analysis(
    [str(Path(SPECPATH).resolve() / "sidecar_entry.py")],
    pathex=[str(ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[str(HOOKS)],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "matplotlib",
        "matplotlib.tests",
        "numpy.tests",
        "pytest",
        "IPython",
        "jupyter",
        "notebook",
        "server",           # never import server into sidecar
        "website",          # no such package
        "desktop",          # no such package
    ],
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
    name="matemium-sidecar",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

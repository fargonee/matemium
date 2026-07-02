"""PyInstaller hook — collect matemium + canvas submodules for the sidecar.

Phase 10: Intelligence (lancedb, embeddings) and MCP are optional/lazy; collect only core.
If building with intelligence extras, they will be picked up via hiddenimports in spec.
"""

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

hiddenimports = (
    collect_submodules("matemium")
    + collect_submodules("canvas")
)

datas = collect_data_files("matemium", includes=["templates/**"])
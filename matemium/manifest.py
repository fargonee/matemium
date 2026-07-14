"""Asset manifest loading and validation for Matemium local/offline dependencies."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class AssetManifestEntry:
    id: str
    name: str
    url: str
    sha256: str
    size: int
    extract: bool
    extract_format: str
    install_path: str
    platforms: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AssetManifestEntry:
        """Parse and validate entry fields from dictionary."""
        required = ["id", "name", "url", "sha256", "size", "extract", "extract_format", "install_path", "platforms"]
        missing = [f for f in required if f not in data]
        if missing:
            raise ValueError(f"Asset manifest entry is missing required fields: {', '.join(missing)}")

        return cls(
            id=str(data["id"]),
            name=str(data["name"]),
            url=str(data["url"]),
            sha256=str(data["sha256"]),
            size=int(data["size"]),
            extract=bool(data["extract"]),
            extract_format=str(data["extract_format"]),
            install_path=str(data["install_path"]),
            platforms=[str(p) for p in data["platforms"]],
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert entry to JSON-serializable dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "url": self.url,
            "sha256": self.sha256,
            "size": self.size,
            "extract": self.extract,
            "extract_format": self.extract_format,
            "install_path": self.install_path,
            "platforms": self.platforms,
        }


@dataclass(frozen=True)
class AssetManifest:
    version: str
    assets: list[AssetManifestEntry]
    notes: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AssetManifest:
        """Parse and validate full asset manifest from dictionary."""
        if "version" not in data:
            raise ValueError("Asset manifest is missing required 'version' field")
        if "assets" not in data or not isinstance(data["assets"], list):
            raise ValueError("Asset manifest is missing required 'assets' list field")

        assets = [AssetManifestEntry.from_dict(item) for item in data["assets"]]
        notes = data.get("notes")
        if notes is not None:
            notes = str(notes)

        return cls(
            version=str(data["version"]),
            assets=assets,
            notes=notes,
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert manifest to JSON-serializable dictionary."""
        res: dict[str, Any] = {
            "version": self.version,
            "assets": [a.to_dict() for a in self.assets],
        }
        if self.notes is not None:
            res["notes"] = self.notes
        return res


def load_manifest(manifest_path: Path | str) -> AssetManifest:
    """Load, parse, and validate an AssetManifest from a JSON file path."""
    path = Path(manifest_path)
    if not path.is_file():
        raise FileNotFoundError(f"Manifest file not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    return AssetManifest.from_dict(data)

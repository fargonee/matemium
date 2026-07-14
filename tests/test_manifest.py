"""Unit tests for the Matemium local asset manifest loader and validator."""

from __future__ import annotations

from pathlib import Path
import pytest

from matemium.manifest import AssetManifest, AssetManifestEntry, load_manifest

REPO_ROOT = Path(__file__).resolve().parent.parent
REAL_MANIFEST_PATH = REPO_ROOT / "shared" / "assets" / "manifest.json"


def test_load_real_manifest() -> None:
    """Verify that the real manifest.json parses perfectly and includes our GGUF models."""
    manifest = load_manifest(REAL_MANIFEST_PATH)

    assert manifest.version == "2026-07-12"
    assert len(manifest.assets) >= 4  # TinyTex + 3 LLM models

    # Verify model details
    assets_by_id = {a.id: a for a in manifest.assets}

    # 1. Qwen 3B
    assert "llm-qwen-coder-3b-q4" in assets_by_id
    qwen3b = assets_by_id["llm-qwen-coder-3b-q4"]
    assert qwen3b.name == "Qwen-2.5-Coder-3B-Instruct (Q4_K_M GGUF)"
    assert qwen3b.sha256 == "724fb256bec1ff062b2f65e4569e871ad2e95ab2a3989723d1769c54294730b7"
    assert qwen3b.size == 2104932800
    assert qwen3b.extract is False
    assert "linux" in qwen3b.platforms

    # 2. Qwen 7B
    assert "llm-qwen-coder-7b-q4" in assets_by_id
    qwen7b = assets_by_id["llm-qwen-coder-7b-q4"]
    assert qwen7b.name == "Qwen-2.5-Coder-7B-Instruct (Q4_K_M GGUF)"
    assert qwen7b.sha256 == "509287f78cb4d4cf6b3843734733b914b2c158e43e22a7f4bf5e963800894d3c"
    assert qwen7b.size == 4683073504
    assert qwen7b.extract is False

    # 3. Llama 8B
    assert "llm-llama-8b-q4" in assets_by_id
    llama8b = assets_by_id["llm-llama-8b-q4"]
    assert llama8b.name == "Llama-3-8B-Instruct (Q4_K_M GGUF)"
    assert llama8b.sha256 == "4903067381e3753e2629f9d20c52df0e43b675bed2735bc3efea351c7d07454d"
    assert llama8b.size == 4915000000


def test_manifest_validation_failures() -> None:
    """Verify that the manifest loader rejects invalid and incomplete payloads."""
    # Missing required field inside entry
    incomplete_entry_dict = {
        "id": "bad-asset",
        "name": "Bad Asset",
        "url": "http://example.com/file.gguf"
        # missing size, sha256, platforms, etc.
    }

    with pytest.raises(ValueError, match="Asset manifest entry is missing required fields"):
        AssetManifestEntry.from_dict(incomplete_entry_dict)

    # Missing required root fields
    bad_manifest_dict = {
        "version": "1.0"
        # missing assets list
    }

    with pytest.raises(ValueError, match="Asset manifest is missing required 'assets' list field"):
        AssetManifest.from_dict(bad_manifest_dict)


def test_manifest_symmetry() -> None:
    """Verify serialization symmetry via to_dict and from_dict."""
    original_dict = {
        "id": "test-asset",
        "name": "Test Asset",
        "url": "https://example.com/asset.zip",
        "sha256": "abcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcd",
        "size": 12345,
        "extract": True,
        "extract_format": "zip",
        "install_path": "bin/test",
        "platforms": ["linux", "windows"]
    }

    entry = AssetManifestEntry.from_dict(original_dict)
    assert entry.to_dict() == original_dict

    manifest_dict = {
        "version": "2026-07-12",
        "assets": [original_dict],
        "notes": "Testing notes capability"
    }

    manifest = AssetManifest.from_dict(manifest_dict)
    assert manifest.to_dict() == manifest_dict

#!/usr/bin/env python3
"""Fail fast when a Matemium desktop release is internally inconsistent."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SEMVER = re.compile(r"^v?(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")


def fail(message: str) -> None:
    raise SystemExit(f"release check failed: {message}")


def text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def match_version(path: str, pattern: str) -> str:
    found = re.search(pattern, text(path), flags=re.MULTILINE)
    if not found:
        fail(f"could not read version from {path}")
    return found.group(1)


def main() -> None:
    if len(sys.argv) != 2 or not (tag_match := SEMVER.fullmatch(sys.argv[1])):
        fail("usage: scripts/check_release.py vMAJOR.MINOR.PATCH")
    tag = sys.argv[1] if sys.argv[1].startswith("v") else f"v{sys.argv[1]}"
    expected = tag.removeprefix("v")

    versions = {
        "pyproject.toml": match_version("pyproject.toml", r'^version = "([^"]+)"'),
        "matemium/__version__.py": match_version(
            "matemium/__version__.py", r'^__version__ = "([^"]+)"'
        ),
        "desktop/app/package.json": json.loads(
            text("desktop/app/package.json")
        )["version"],
        "desktop/app/package-lock.json": json.loads(
            text("desktop/app/package-lock.json")
        )["version"],
        "desktop/src-tauri/Cargo.toml": match_version(
            "desktop/src-tauri/Cargo.toml", r'^version = "([^"]+)"'
        ),
        "desktop/src-tauri/Cargo.lock": match_version(
            "desktop/src-tauri/Cargo.lock",
            r'^name = "matemium-desktop"\nversion = "([^"]+)"',
        ),
        "desktop/src-tauri/tauri.conf.json": json.loads(
            text("desktop/src-tauri/tauri.conf.json")
        )["version"],
    }
    mismatches = {path: version for path, version in versions.items() if version != expected}
    if mismatches:
        fail(f"expected {expected} in every version source, got {mismatches}")

    if f"## [{expected}]" not in text("CHANGELOG.md"):
        fail(f"CHANGELOG.md has no {expected} release section")

    manifest = json.loads(text("shared/assets/manifest.json"))
    bundled_manifest = json.loads(text("desktop/src-tauri/binaries/manifest.json"))
    if bundled_manifest != manifest:
        fail("desktop binary manifest is out of sync with shared/assets/manifest.json")
    if not manifest.get("assets"):
        fail("asset manifest is empty")
    for asset in manifest["assets"]:
        digest = asset.get("sha256", "")
        if not re.fullmatch(r"[0-9a-f]{64}", digest):
            fail(f"asset {asset.get('id')} does not have a real SHA-256")
        if not str(asset.get("url", "")).startswith("https://"):
            fail(f"asset {asset.get('id')} does not use HTTPS")
        if int(asset.get("size", 0)) <= 0:
            fail(f"asset {asset.get('id')} has no positive size")

    config = json.loads(text("desktop/src-tauri/tauri.conf.json"))
    resources = config.get("bundle", {}).get("resources", {})
    if not {"LICENSE.txt", "THIRD_PARTY_NOTICES.txt"}.issubset(resources.values()):
        fail("desktop bundle does not include license and third-party notices")

    server_url = json.loads(text("desktop/app/src/config.json")).get("serverUrl", "")
    if not server_url.startswith("https://") or any(
        marker in server_url for marker in ("localhost", "example.com", "placeholder")
    ):
        fail("desktop app does not have a production HTTPS server URL")

    for required in (
        ".nvmrc",
        ".python-version",
        "DEVELOPMENT.md",
        "LICENSE",
        "requirements-dev.txt",
        "requirements-desktop.txt",
        "rust-toolchain.toml",
        "uv.lock",
        "server/uv.lock",
        "desktop/app/package-lock.json",
        "website/package-lock.json",
        "docs/pnpm-lock.yaml",
        "desktop/src-tauri/Cargo.lock",
        "desktop/THIRD_PARTY_NOTICES.md",
        "RELEASING.md",
        ".github/workflows/build-linux.yml",
        ".github/workflows/build-windows.yml",
        ".github/workflows/build-macos.yml",
        ".github/workflows/publish-release.yml",
    ):
        if not (ROOT / required).is_file():
            fail(f"missing {required}")

    diff_check = subprocess.run(
        ["git", "diff", "--check"], cwd=ROOT, text=True, capture_output=True
    )
    if diff_check.returncode:
        fail(diff_check.stdout.strip() or diff_check.stderr.strip())

    print(f"release check passed for {tag}")
    for path, version in versions.items():
        print(f"  {path}: {version}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
generate_manifest.py

Generates a MicroPython OTA-compatible manifest.json with SHA-256 hashes,
and updates version.txt using semantic versioning.

Usage:
    python generate_manifest.py --bump [patch|minor|major]

Example:
    python generate_manifest.py --bump patch
"""

import os
import json
import argparse
import hashlib

EXCLUDE = {
    "manifest.json", "version.txt", "generate_manifest.py",
    ".git", "__pycache__"
}

def sha256sum(path):
    """Return SHA-256 hash of file contents."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(4096):
            h.update(chunk)
    return h.hexdigest()

def collect_files(root):
    """Collect valid files and return dict: {path: sha256}"""
    result = {}
    for dirpath, _, filenames in os.walk(root):
        for fname in filenames:
            if (
                fname in EXCLUDE or
                fname.startswith("_") or
                fname.startswith(".")
            ):
                continue
            full = os.path.join(dirpath, fname)
            rel = os.path.relpath(full, root).replace("\\", "/")
            result[rel] = sha256sum(full)
    return result

def bump_version(current, level):
    major, minor, patch = map(int, current.strip().split("."))
    return {
        "major": f"{major+1}.0.0",
        "minor": f"{major}.{minor+1}.0",
        "patch": f"{major}.{minor}.{patch+1}"
    }[level]

def main():
    parser = argparse.ArgumentParser(description="Generate manifest.json + version.txt for OTA")
    parser.add_argument("--bump", choices=["major", "minor", "patch"], default="patch",
                        help="Semver bump level (default: patch)")
    args = parser.parse_args()

    # Load current version
    current = "0.0.0"
    if os.path.exists("version.txt"):
        with open("version.txt") as f:
            current = f.read().strip()

    new_version = bump_version(current, args.bump)
    print(f"🔄 Bumping version: {current} → {new_version}")

    # Collect files + hashes
    files = collect_files(".")
    if not files:
        print("⚠️ No valid files found.")
        return

    with open("manifest.json", "w") as f:
        json.dump({"version": new_version, "files": files}, f, indent=2)
    print(f"📦 Wrote manifest.json with {len(files)} files.")

    with open("version.txt", "w") as f:
        f.write(new_version)
    print(f"✅ Updated version.txt to {new_version}")

    print("\n📋 Included files:")
    for fpath in sorted(files):
        print("   •", fpath)

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""Build and verify Timely skill and Fusion Bridge release ZIPs."""

import shutil
import sys
import tempfile
import zipfile
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SKILL = ROOT / "skills/fusion-cad-job-builder"
BRIDGE = SKILL / "assets/FusionCadJobRunner"
DIST = ROOT / "dist"
EXCLUDED_PARTS = {"__pycache__", ".env", "config.json"}


def allowed(path):
    return not any(part in EXCLUDED_PARTS for part in path.parts) and not path.name.endswith((".pyc", ".pyo")) and ".secret" not in path.name.lower()


def add_tree(archive, source, prefix=""):
    for path in sorted(source.rglob("*")):
        if path.is_file() and allowed(path.relative_to(source)):
            archive.write(path, (Path(prefix) / path.relative_to(source)).as_posix())


def public_config():
    values = {}
    env_path = ROOT / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8-sig").splitlines():
            if line.strip() and not line.lstrip().startswith("#") and "=" in line:
                name, value = line.split("=", 1)
                values[name.strip()] = value.strip().strip('"').strip("'")
    url = values.get("SUPABASE_URL", "")
    key = values.get("SUPABASE_PUBLISHABLE_KEY") or values.get("SUPABASE_KEY", "")
    if not url.startswith("https://") or not key.startswith("sb_publishable_"):
        raise RuntimeError("A modern Supabase publishable key is required; secret/service-role keys are refused")
    return {"supabase_url": url.rstrip("/"), "supabase_publishable_key": key}


def build():
    DIST.mkdir(exist_ok=True)
    skill_zip = DIST / "maker-cad-fusion-skill.zip"
    bridge_zip = DIST / "fusion-local-bridge.zip"
    config = public_config()
    config_bytes = (json.dumps(config, indent=2) + "\n").encode("utf-8")
    with zipfile.ZipFile(skill_zip, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.write(SKILL / "SKILL.md", "SKILL.md")
        add_tree(archive, SKILL / "scripts", "scripts")
        add_tree(archive, SKILL / "references", "references")
        archive.writestr("scripts/public_config.json", config_bytes)
    with zipfile.ZipFile(bridge_zip, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(BRIDGE.rglob("*")):
            if path.is_file() and allowed(path.relative_to(BRIDGE)) and path.name != "config.example.json":
                archive.write(path, (Path("FusionCadJobRunner") / path.relative_to(BRIDGE)).as_posix())
        archive.writestr("FusionCadJobRunner/config.example.json", config_bytes)
    verify(skill_zip, bridge_zip)
    return skill_zip, bridge_zip


def verify(skill_zip, bridge_zip):
    forbidden = (".env", "/config.json", "__pycache__", ".pyc", ".secret")
    with zipfile.ZipFile(skill_zip) as archive:
        names = archive.namelist()
        required = {"SKILL.md"}
        if not required.issubset(names) or not any(x.startswith("scripts/") for x in names) or not any(x.startswith("references/") for x in names):
            raise RuntimeError("Timely ZIP root is invalid")
        if any(any(term in name.lower() for term in forbidden) for name in names):
            raise RuntimeError("private file found in Timely ZIP")
    with zipfile.ZipFile(bridge_zip) as archive:
        names = archive.namelist()
        if "FusionCadJobRunner/FusionCadJobRunner.py" not in names or "FusionCadJobRunner/FusionCadJobRunner.manifest" not in names:
            raise RuntimeError("Bridge ZIP root is invalid")
        if any(any(term in name.lower() for term in forbidden) for name in names):
            raise RuntimeError("private file found in Bridge ZIP")


if __name__ == "__main__":
    try:
        files = build()
        print("PASS: " + ", ".join(str(path) for path in files))
    except Exception as exc:
        print("FAIL: " + str(exc), file=sys.stderr)
        raise

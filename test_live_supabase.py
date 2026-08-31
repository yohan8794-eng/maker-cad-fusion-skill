#!/usr/bin/env python3
"""Opt-in live RPC smoke test. Reads .env and never prints credentials."""

import importlib.util
import json
import secrets
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def env_values():
    values = {}
    for line in (ROOT / ".env").read_text(encoding="utf-8-sig").splitlines():
        if line.strip() and not line.lstrip().startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def main():
    bridge = load("bridge_client_live", ROOT / "skills/fusion-cad-job-builder/assets/FusionCadJobRunner/bridge_client.py")
    timely = load("bridge_api_live", ROOT / "skills/fusion-cad-job-builder/scripts/bridge_api.py")
    env = env_values()
    config = {
        "supabase_url": env["SUPABASE_URL"],
        "supabase_publishable_key": env.get("SUPABASE_PUBLISHABLE_KEY") or env["SUPABASE_KEY"],
        "device_id": str(uuid.uuid4()),
        "device_token": secrets.token_urlsafe(48),
        "pairing_code": bridge.new_pairing_code(),
    }
    runner = bridge.BridgeClient(config)
    client = timely.BridgeApi(config["supabase_url"], config["supabase_publishable_key"])
    registered = runner.register()
    heartbeat = runner.heartbeat()
    online = client.bridge_status(config["pairing_code"])
    fixture = json.loads((ROOT / "skills/fusion-cad-job-builder/assets/examples/mounting-plate.json").read_text(encoding="utf-8"))
    queued, job_token = client.enqueue(config["pairing_code"], fixture)
    first = runner.claim_next()
    second = runner.claim_next()
    finished = runner.finish(first["id"], "completed", {"smoke_test": True})
    status = client.job_status(first["id"], job_token)
    assert registered["status"] == "online"
    assert heartbeat["status"] == "online"
    assert online["status"] == "online"
    assert queued["status"] == "queued"
    assert first["status"] == "running"
    assert second is None
    assert finished["status"] == "completed"
    assert status["status"] == "completed"
    print(json.dumps({"registration": "PASS", "heartbeat": "PASS", "pairing": "PASS", "device_filter": "PASS", "atomic_claim": "PASS", "duplicate_prevention": "PASS", "completion": "PASS"}))


if __name__ == "__main__":
    main()


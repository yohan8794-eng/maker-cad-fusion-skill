#!/usr/bin/env python3

import importlib.util
import json
import tempfile
import unittest
import urllib.request
import zipfile
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
SKILL = HERE.parent
PROJECT = SKILL.parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


bridge_client = load("bridge_client", SKILL / "assets/FusionCadJobRunner/bridge_client.py")


class FakeResponse:
    def __init__(self, payload):
        self.payload = json.dumps(payload).encode()
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def read(self): return self.payload


class PublicMvpTests(unittest.TestCase):
    def test_device_identity_is_persisted_and_safe(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            example = root / "config.example.json"
            example.write_text(json.dumps({"supabase_url": "https://example.supabase.co", "supabase_publishable_key": "sb_publishable_test"}), encoding="utf-8")
            config = bridge_client.load_or_create_config(root / "config.json", example)
            again = bridge_client.load_or_create_config(root / "config.json", example)
            self.assertEqual(config, again)
            self.assertEqual(len(config["pairing_code"]), 10)
            self.assertGreaterEqual(len(config["device_token"]), 32)
            self.assertNotEqual(config["device_id"], config["device_token"])

    @mock.patch.object(urllib.request, "urlopen")
    def test_registration_heartbeat_filter_and_finish_rpc(self, urlopen):
        urlopen.return_value = FakeResponse({"status": "online"})
        config = {"supabase_url": "https://example.supabase.co", "supabase_publishable_key": "sb_publishable_test", "device_id": "11111111-1111-1111-1111-111111111111", "device_token": "t" * 48, "pairing_code": "ABCDEFG234"}
        client = bridge_client.BridgeClient(config)
        client.register(); client.heartbeat(); client.claim_next(); client.finish("22222222-2222-2222-2222-222222222222", "completed", {"ok": True})
        urls = [call.args[0].full_url for call in urlopen.call_args_list]
        self.assertTrue(urls[0].endswith("/rpc/register_device"))
        self.assertTrue(urls[1].endswith("/rpc/device_heartbeat"))
        self.assertTrue(urls[2].endswith("/rpc/claim_next_cad_job"))
        self.assertTrue(urls[3].endswith("/rpc/finish_cad_job"))
        claim_body = json.loads(urlopen.call_args_list[2].args[0].data)
        self.assertEqual(claim_body["p_device_id"], config["device_id"])

    def test_sql_enforces_atomic_device_claim_and_terminal_state(self):
        sql = (PROJECT / "schema.sql").read_text(encoding="utf-8").lower()
        self.assertIn("target_device_id=p_device_id and status='queued'", sql)
        self.assertIn("for update skip locked", sql)
        self.assertIn("claimed_by=p_device_id", sql)
        self.assertIn("and status='running'", sql)
        self.assertIn("('completed','failed')", sql)
        self.assertIn("enable row level security", sql)
        self.assertIn("revoke all on public.devices, public.cad_jobs from anon, authenticated", sql)
        self.assertNotIn("service_role", (SKILL / "assets/FusionCadJobRunner/config.example.json").read_text(encoding="utf-8").lower())

    def test_dist_zip_roots_and_no_private_files(self):
        dist = PROJECT / "dist"
        skill_zip = dist / "maker-cad-fusion-skill.zip"
        bridge_zip = dist / "fusion-local-bridge.zip"
        if not skill_zip.exists() or not bridge_zip.exists():
            self.skipTest("distribution ZIPs not built yet")
        with zipfile.ZipFile(skill_zip) as archive:
            names = set(archive.namelist())
            self.assertIn("SKILL.md", names)
            self.assertTrue(any(x.startswith("scripts/") for x in names))
            self.assertTrue(any(x.startswith("references/") for x in names))
            self.assertFalse(any(".env" in x or Path(x).name == "config.json" or "__pycache__" in x or x.endswith(".pyc") for x in names))
            public_config = json.loads(archive.read("scripts/public_config.json"))
            self.assertTrue(public_config["supabase_publishable_key"].startswith("sb_publishable_"))
        with zipfile.ZipFile(bridge_zip) as archive:
            names = set(archive.namelist())
            self.assertIn("FusionCadJobRunner/FusionCadJobRunner.py", names)
            self.assertIn("FusionCadJobRunner/FusionCadJobRunner.manifest", names)
            self.assertFalse(any(Path(x).name == "config.json" or "__pycache__" in x or x.endswith(".pyc") for x in names))
            public_config = json.loads(archive.read("FusionCadJobRunner/config.example.json"))
            self.assertTrue(public_config["supabase_publishable_key"].startswith("sb_publishable_"))


if __name__ == "__main__":
    unittest.main()

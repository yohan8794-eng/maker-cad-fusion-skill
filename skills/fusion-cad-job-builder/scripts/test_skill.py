#!/usr/bin/env python3

import importlib.util
import json
import unittest
import urllib.request
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


validator = load("validator", HERE / "validate_cad_job.py")
supabase = load("supabase_jobs", HERE / "supabase_jobs.py")
bridge_api = load("bridge_api", HERE / "bridge_api.py")


class FakeResponse:
    def __init__(self, payload):
        self.payload = json.dumps(payload).encode()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return self.payload


class SkillTests(unittest.TestCase):
    def test_example_is_valid(self):
        job = json.loads((ROOT / "assets/examples/mounting-plate.json").read_text(encoding="utf-8"))
        errors, warnings = validator.validate(job)
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    def test_missing_and_bad_values_fail(self):
        errors, _ = validator.validate({"schema_version": "1.0", "units": "cm", "operations": []})
        self.assertTrue(any("missing required field" in error for error in errors))
        self.assertTrue(any("units" in error for error in errors))

    def test_close_hole_warns(self):
        job = json.loads((ROOT / "assets/examples/mounting-plate.json").read_text(encoding="utf-8"))
        job["operations"][2]["centres"][0] = [-39, -24]
        errors, warnings = validator.validate(job)
        self.assertEqual(errors, [])
        self.assertTrue(any("edge distance" in warning for warning in warnings))

    def test_rectangular_pattern_contract(self):
        job = json.loads((ROOT / "assets/examples/mounting-plate.json").read_text(encoding="utf-8"))
        job["operations"].append({"id": "copies", "type": "pattern", "pattern_type": "rectangular", "source_ref": "base_body", "x_count": 3, "x_spacing": 100, "y_count": 1, "y_spacing": 0})
        errors, _ = validator.validate(job)
        self.assertEqual(errors, [])

    @mock.patch.object(urllib.request, "urlopen")
    def test_enqueue_request(self, urlopen):
        urlopen.return_value = FakeResponse([{"id": "job-1", "status": "queued"}])
        client = supabase.CadJobsClient("https://example.supabase.co", "publishable-test-key")
        result = client.enqueue({"schema_version": "1.0"}, "ABCDEFG234", "j" * 43)
        request = urlopen.call_args.args[0]
        self.assertEqual(request.method, "POST")
        self.assertEqual(request.full_url, "https://example.supabase.co/rest/v1/rpc/enqueue_cad_job")
        self.assertNotIn("publishable-test-key", json.dumps(result))

    @mock.patch.object(urllib.request, "urlopen")
    def test_pairing_and_heartbeat_status(self, urlopen):
        urlopen.return_value = FakeResponse({"device_id": "device-1", "status": "online"})
        client = bridge_api.BridgeApi("https://example.supabase.co", "publishable-test-key")
        result = client.bridge_status("abcDefg234")
        self.assertEqual(result["status"], "online")
        body = json.loads(urlopen.call_args.args[0].data)
        self.assertEqual(body["p_pairing_code"], "ABCDEFG234")


if __name__ == "__main__":
    unittest.main()

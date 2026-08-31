#!/usr/bin/env python3
"""Compatibility wrapper for the device-paired Bridge API."""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path


class SupabaseError(RuntimeError):
    pass


class CadJobsClient:
    def __init__(self, url=None, key=None, timeout=15):
        self.url = (url or os.getenv("SUPABASE_URL", "")).rstrip("/")
        self.key = key or os.getenv("SUPABASE_PUBLISHABLE_KEY") or os.getenv("SUPABASE_KEY", "")
        self.timeout = timeout
        if not self.url or not self.key:
            raise SupabaseError("SUPABASE_URL and SUPABASE_PUBLISHABLE_KEY are required")

    def request(self, method, path, body=None, prefer=None):
        data = None if body is None else json.dumps(body, separators=(",", ":")).encode("utf-8")
        headers = {"apikey": self.key, "Authorization": f"Bearer {self.key}", "Accept": "application/json"}
        if data is not None:
            headers["Content-Type"] = "application/json"
        if prefer:
            headers["Prefer"] = prefer
        request = urllib.request.Request(f"{self.url}/rest/v1/{path}", data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                raw = response.read()
                return json.loads(raw) if raw else None
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:1000]
            raise SupabaseError(f"Supabase HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise SupabaseError(f"Supabase connection failed: {exc.reason}") from exc

    def rpc(self, name, body):
        return self.request("POST", f"rpc/{name}", body)

    def bridge_status(self, pairing_code):
        return self.rpc("resolve_pairing_code", {"p_pairing_code": pairing_code.strip().upper()})

    def enqueue(self, job, pairing_code, job_token):
        return self.rpc("enqueue_cad_job", {"p_pairing_code": pairing_code.strip().upper(), "p_input_json": job, "p_job_token": job_token})


def main(argv=None):
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    enqueue = sub.add_parser("enqueue")
    enqueue.add_argument("job", type=Path)
    enqueue.add_argument("--pairing-code", required=True)
    enqueue.add_argument("--job-token", required=True)
    status = sub.add_parser("bridge-status")
    status.add_argument("pairing_code")
    args = parser.parse_args(argv)
    try:
        client = CadJobsClient()
        if args.command == "enqueue":
            result = client.enqueue(json.loads(args.job.read_text(encoding="utf-8")), args.pairing_code, args.job_token)
        else:
            result = client.bridge_status(args.pairing_code)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (OSError, json.JSONDecodeError, SupabaseError) as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

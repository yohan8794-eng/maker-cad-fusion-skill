#!/usr/bin/env python3
"""Timely-side pairing, heartbeat, submission and status client."""

import argparse
import json
import os
import secrets
import sys
import urllib.error
import urllib.request
from pathlib import Path


class BridgeApiError(RuntimeError):
    pass


class BridgeApi:
    def __init__(self, url=None, key=None, timeout=15):
        bundled = {}
        bundled_path = Path(__file__).with_name("public_config.json")
        if bundled_path.exists():
            bundled = json.loads(bundled_path.read_text(encoding="utf-8"))
        self.url = (url or os.getenv("SUPABASE_URL") or bundled.get("supabase_url", "")).rstrip("/")
        self.key = key or os.getenv("SUPABASE_PUBLISHABLE_KEY") or os.getenv("SUPABASE_KEY") or bundled.get("supabase_publishable_key", "")
        self.timeout = timeout
        if not self.url or not self.key:
            raise BridgeApiError("SUPABASE_URL and SUPABASE_PUBLISHABLE_KEY are required")

    def rpc(self, name, body):
        data = json.dumps(body, separators=(",", ":")).encode("utf-8")
        request = urllib.request.Request(
            f"{self.url}/rest/v1/rpc/{name}", data=data,
            headers={"apikey": self.key, "Authorization": f"Bearer {self.key}", "Content-Type": "application/json", "Accept": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                raw = response.read()
                return json.loads(raw) if raw else None
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:1000]
            raise BridgeApiError(f"Supabase HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise BridgeApiError(f"Supabase connection failed: {exc.reason}") from exc

    def bridge_status(self, pairing_code):
        return self.rpc("resolve_pairing_code", {"p_pairing_code": pairing_code.strip().upper()})

    def enqueue(self, pairing_code, job, job_token=None):
        token = job_token or secrets.token_urlsafe(32)
        result = self.rpc("enqueue_cad_job", {"p_pairing_code": pairing_code.strip().upper(), "p_input_json": job, "p_job_token": token})
        return result, token

    def job_status(self, job_id, job_token):
        return self.rpc("get_cad_job_status", {"p_job_id": str(job_id), "p_job_token": job_token})


def main(argv=None):
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    status = sub.add_parser("bridge-status")
    status.add_argument("pairing_code")
    enqueue = sub.add_parser("enqueue")
    enqueue.add_argument("pairing_code")
    enqueue.add_argument("job", type=Path)
    poll = sub.add_parser("job-status")
    poll.add_argument("job_id")
    poll.add_argument("job_token")
    args = parser.parse_args(argv)
    try:
        client = BridgeApi()
        if args.command == "bridge-status":
            result = client.bridge_status(args.pairing_code)
        elif args.command == "enqueue":
            result, token = client.enqueue(args.pairing_code, json.loads(args.job.read_text(encoding="utf-8")))
            result = {"job": result, "job_token": token}
        else:
            result = client.job_status(args.job_id, args.job_token)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (OSError, json.JSONDecodeError, BridgeApiError) as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

"""Standard-library client and local identity management for FusionCadJobRunner."""

import json
import secrets
import urllib.error
import urllib.request
import uuid
from pathlib import Path

BRIDGE_VERSION = "0.2.0"
CONFIG_PATH = Path(__file__).with_name("config.json")
EXAMPLE_PATH = Path(__file__).with_name("config.example.json")
PAIRING_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


class BridgeClientError(RuntimeError):
    pass


def new_pairing_code(length=10):
    return "".join(secrets.choice(PAIRING_ALPHABET) for _ in range(length))


def load_or_create_config(path=CONFIG_PATH, example_path=EXAMPLE_PATH):
    path = Path(path)
    if path.exists():
        config = json.loads(path.read_text(encoding="utf-8"))
    else:
        config = json.loads(Path(example_path).read_text(encoding="utf-8"))
        config.update({
            "device_id": str(uuid.uuid4()),
            "device_token": secrets.token_urlsafe(48),
            "pairing_code": new_pairing_code(),
        })
        path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    required = ("supabase_url", "supabase_publishable_key", "device_id", "device_token", "pairing_code")
    missing = [name for name in required if not config.get(name) or str(config[name]).startswith("YOUR_")]
    if missing:
        raise BridgeClientError("Bridge config is incomplete: " + ", ".join(missing))
    return config


class BridgeClient:
    def __init__(self, config, timeout=15):
        self.config = config
        self.url = config["supabase_url"].rstrip("/")
        self.key = config["supabase_publishable_key"]
        self.timeout = timeout

    def rpc(self, name, body):
        data = json.dumps(body, separators=(",", ":")).encode("utf-8")
        request = urllib.request.Request(
            self.url + "/rest/v1/rpc/" + name,
            data=data,
            headers={"apikey": self.key, "Authorization": "Bearer " + self.key, "Content-Type": "application/json", "Accept": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                raw = response.read()
                return json.loads(raw) if raw else None
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:1000]
            raise BridgeClientError("Supabase HTTP %s: %s" % (exc.code, detail)) from exc
        except urllib.error.URLError as exc:
            raise BridgeClientError("Supabase connection failed: %s" % exc.reason) from exc

    def _device_body(self):
        return {"p_device_id": self.config["device_id"], "p_device_token": self.config["device_token"]}

    def register(self):
        body = self._device_body()
        body.update({"p_pairing_code": self.config["pairing_code"], "p_bridge_version": BRIDGE_VERSION})
        return self.rpc("register_device", body)

    def heartbeat(self):
        body = self._device_body()
        body["p_bridge_version"] = BRIDGE_VERSION
        return self.rpc("device_heartbeat", body)

    def claim_next(self):
        return self.rpc("claim_next_cad_job", self._device_body())

    def finish(self, job_id, status, result=None, error=None):
        body = self._device_body()
        body.update({"p_job_id": str(job_id), "p_status": status, "p_result_json": result, "p_error_message": error})
        return self.rpc("finish_cad_job", body)


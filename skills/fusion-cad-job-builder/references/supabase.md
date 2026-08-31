# Supabase device bridge

Use the bundled public endpoint configuration or `SUPABASE_URL` plus `SUPABASE_PUBLISHABLE_KEY`. Accept legacy `SUPABASE_KEY` only for compatibility. Never put a service-role/secret key in Timely, GitHub, or the Fusion Add-in.

The public tables are not accessed directly. RLS and revoked table grants deny `anon`/`authenticated` table access. Use only these RPCs:

- `register_device`: register a UUID device ID, hashed high-entropy device token, 10-character pairing code, version, and initial heartbeat.
- `device_heartbeat`: authenticate the device token and update `last_seen`.
- `resolve_pairing_code`: return ONLINE when the matching device heartbeat is within 90 seconds.
- `enqueue_cad_job`: require a valid pairing code and ONLINE device; create a Job for that device only.
- `claim_next_cad_job`: authenticate the device and atomically claim one targeted queued Job with `FOR UPDATE SKIP LOCKED`.
- `finish_cad_job`: allow only the device that claimed a running Job to set `completed` or `failed`.
- `get_cad_job_status`: require the high-entropy per-Job token returned at enqueue.

Lifecycle: `queued → running → completed|failed`. Never query or create a global queue. Never retry a running/completed Job as the same row.

The repository root `schema.sql` is the authoritative database definition. The public repository is https://github.com/yohan8794-eng/maker-cad-fusion-skill.


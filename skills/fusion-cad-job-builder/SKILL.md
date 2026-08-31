---
name: fusion-cad-job-builder
description: Turn natural-language maker-part requests into validated CAD Job JSON and send them to the user's paired Fusion 360 Local Bridge. Use for mounting plates, simple brackets, sensor/motor/PCB mounts, adapter plates, and simple parametric parts built from rectangles, circles, extrudes, cuts, holes, fillets, and body patterns.
---

# Fusion CAD Job Builder

Use a Bridge-first, fail-closed workflow. Never claim Fusion or Supabase succeeded without reading the returned state.

## 1. Require a connected Bridge

Ask for the user's 10-character pairing code if the conversation has none. Check it before asking CAD questions:

```powershell
python scripts\bridge_api.py bridge-status <PAIRING_CODE>
```

Continue only when the result is `online` and `last_seen` is within 90 seconds. Never enqueue a global or unpaired job.

If missing, unknown, or offline, stop submission and explain directly in chat:

1. “Fusion 360에서 모델을 자동 생성하려면 최초 1회 Fusion Local Bridge 설치가 필요합니다.”
2. Download: https://github.com/yohan8794-eng/maker-cad-fusion-skill/releases/latest/download/fusion-local-bridge.zip
3. Extract the ZIP, start Fusion 360, open `Utilities > Scripts and Add-Ins`, add the `FusionCadJobRunner` folder, and run it.
4. Enable `Run on Startup` so it starts with Fusion.
5. Enter the pairing code shown by Fusion in this chat, then check status again.

Do not merely send the user to a README. Give these steps in the conversation. Read [LOCAL_FUSION_SETUP.md](references/LOCAL_FUSION_SETUP.md) when detailed help is needed.

## 2. Clarify the design

Classify as `mounting_plate`, `bracket`, `simple_mount`, `sensor_mount`, `motor_mount`, `pcb_mount`, or `adapter_plate`. Normalize dimensions to mm. Ask one compact group of blocking questions for overall size/thickness, hole diameter/count/placement/extent, bracket legs, and requested edge treatment.

Do not invent functional dimensions. Put accepted non-critical defaults in `assumptions`. Read [HOW_TO_USE.md](references/HOW_TO_USE.md) for family-specific questions.

## 3. Build and validate

Build operations in dependency order: `sketch` → `extrude`/cut → `hole` → `pattern` → `fillet`. Emit JSON matching [CAD_JOB_SCHEMA.md](references/CAD_JOB_SCHEMA.md) and [cad-job.schema.json](references/cad-job.schema.json), then run:

```powershell
python scripts\validate_cad_job.py <job.json>
```

Fix all errors. Report manufacturing warnings rather than silently changing geometry.

Stable Bridge operations are rectangle/circle sketches on construction planes, new/join/cut extrudes, explicit holes, vertical/all-edge fillets, and rectangular/circular **body** patterns. Chamfer, face-attached sketches, feature patterns, and advanced bracket topology are contract/planning-only until live Fusion verification; do not submit them as supported automation.

## 4. Submit and report

Only after Bridge ONLINE and validation PASS:

```powershell
python scripts\bridge_api.py enqueue <PAIRING_CODE> <job.json>
python scripts\bridge_api.py job-status <JOB_ID> <JOB_TOKEN>
```

Keep the returned job token private. Poll until `completed` or `failed`. On completion, summarize the created design and returned result. On failure, report the error and consult [TROUBLESHOOTING.md](references/TROUBLESHOOTING.md). Never expose keys, device tokens, job tokens, passwords, `.env`, or `config.json`.

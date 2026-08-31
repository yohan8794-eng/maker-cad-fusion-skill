#!/usr/bin/env python3
"""Dependency-free structural and manufacturability checks for CAD Job v1.0."""

import argparse
import json
import math
import sys
from pathlib import Path

ALLOWED_PARTS = {"mounting_plate", "bracket", "simple_mount", "sensor_mount", "motor_mount", "pcb_mount", "adapter_plate"}
ALLOWED_TYPES = {"sketch", "extrude", "hole", "fillet", "pattern"}


def _positive(value, label, errors):
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value) or value <= 0:
        errors.append(f"{label} must be a finite number greater than zero")


def validate(job):
    errors, warnings = [], []
    if not isinstance(job, dict):
        return ["job must be a JSON object"], warnings
    for key in ("schema_version", "name", "part_type", "units", "parameters", "operations"):
        if key not in job:
            errors.append(f"missing required field: {key}")
    if job.get("schema_version") != "1.0":
        errors.append("schema_version must be '1.0'")
    if job.get("part_type") not in ALLOWED_PARTS:
        errors.append("part_type is not in the supported maker-part families")
    if job.get("units") != "mm":
        errors.append("units must be 'mm'")
    coordinates = job.get("coordinate_system")
    if not isinstance(coordinates, dict):
        errors.append("coordinate_system must be an object")
    else:
        if coordinates.get("handedness") != "right":
            errors.append("coordinate_system.handedness must be 'right'")
        if coordinates.get("origin") not in {"center", "lower_left", "assembly_datum"}:
            errors.append("coordinate_system.origin is invalid")
        bounds = coordinates.get("expected_bounds")
        if not isinstance(bounds, dict) or any(not isinstance(bounds.get(key), list) or len(bounds[key]) != 3 for key in ("min", "max")):
            errors.append("coordinate_system.expected_bounds must contain 3D min and max arrays")
        elif any(bounds["min"][i] >= bounds["max"][i] for i in range(3)):
            errors.append("coordinate_system.expected_bounds min must be below max on every axis")
    if not isinstance(job.get("name"), str) or not job.get("name", "").strip():
        errors.append("name must be a non-empty string")
    parameters = job.get("parameters", {})
    if not isinstance(parameters, dict):
        errors.append("parameters must be an object")
    else:
        for name, value in parameters.items():
            _positive(value, f"parameters.{name}", errors)

    operations = job.get("operations", [])
    if not isinstance(operations, list) or len(operations) < 2:
        errors.append("operations must contain at least sketch and extrude")
        return errors, warnings

    seen = set()
    base_rectangles = {}
    body_thickness = {}
    for index, op in enumerate(operations):
        prefix = f"operations[{index}]"
        if not isinstance(op, dict):
            errors.append(f"{prefix} must be an object")
            continue
        op_id, op_type = op.get("id"), op.get("type")
        if not isinstance(op_id, str) or not op_id:
            errors.append(f"{prefix}.id must be a non-empty string")
        elif op_id in seen:
            errors.append(f"duplicate operation id: {op_id}")
        if op_type not in ALLOWED_TYPES:
            errors.append(f"{prefix}.type is unsupported")
        for ref_name in ("profile_ref", "body_ref", "source_ref"):
            if ref_name in op and op[ref_name] not in seen:
                errors.append(f"{prefix}.{ref_name} must reference an earlier operation")

        if op_type == "sketch":
            if op.get("plane") not in {"xy", "yz", "xz"}:
                errors.append(f"{prefix}.plane must be xy, yz, or xz")
            if op.get("shape") == "rectangle":
                _positive(op.get("width"), f"{prefix}.width", errors)
                _positive(op.get("height"), f"{prefix}.height", errors)
                if isinstance(op_id, str):
                    base_rectangles[op_id] = (op.get("width"), op.get("height"), op.get("origin", [0, 0]))
            elif op.get("shape") == "circle":
                _positive(op.get("diameter"), f"{prefix}.diameter", errors)
            else:
                errors.append(f"{prefix}.shape must be rectangle or circle")
        elif op_type == "extrude":
            _positive(op.get("distance"), f"{prefix}.distance", errors)
            if op.get("operation") not in {"new_body", "join", "cut", "intersect"}:
                errors.append(f"{prefix}.operation is invalid")
            if isinstance(op_id, str):
                body_thickness[op_id] = op.get("distance")
            if op.get("distance", 0) < 1.2 and job.get("process", "").upper() == "FDM":
                warnings.append(f"{prefix}: FDM thickness below 1.2 mm")
        elif op_type == "hole":
            _positive(op.get("diameter"), f"{prefix}.diameter", errors)
            centres = op.get("centres")
            if not isinstance(centres, list) or not centres:
                errors.append(f"{prefix}.centres must be a non-empty array")
            elif any(not isinstance(p, list) or len(p) != 2 or not all(isinstance(v, (int, float)) for v in p) for p in centres):
                errors.append(f"{prefix}.centres must contain [x, y] number pairs")
            if op.get("extent") not in {"through_all", "blind"}:
                errors.append(f"{prefix}.extent must be through_all or blind")
            if op.get("extent") == "blind":
                _positive(op.get("depth"), f"{prefix}.depth", errors)

            body_ref = op.get("body_ref")
            extrude = next((x for x in operations[:index] if x.get("id") == body_ref), None)
            rect = base_rectangles.get(extrude.get("profile_ref")) if extrude else None
            if rect and isinstance(centres, list) and isinstance(op.get("diameter"), (int, float)):
                width, height, origin = rect
                if all(isinstance(v, (int, float)) for v in (width, height)) and isinstance(origin, list) and len(origin) == 2:
                    minimum = max(op["diameter"], 2.0)
                    ox, oy = origin
                    for point in centres:
                        if isinstance(point, list) and len(point) == 2 and all(isinstance(v, (int, float)) for v in point):
                            x, y = point
                            edge = min(x - ox, y - oy, ox + width - x, oy + height - y)
                            if edge < minimum:
                                warnings.append(f"{prefix}: hole centre {point} edge distance {edge:g} mm is below recommended {minimum:g} mm")
        elif op_type == "fillet":
            _positive(op.get("radius"), f"{prefix}.radius", errors)
            if op.get("edge_selection") not in {"all", "top", "bottom", "vertical"}:
                errors.append(f"{prefix}.edge_selection is invalid")
            thickness = body_thickness.get(op.get("body_ref"))
            if op.get("edge_selection") != "vertical" and isinstance(thickness, (int, float)) and isinstance(op.get("radius"), (int, float)) and op["radius"] > thickness / 2:
                warnings.append(f"{prefix}: radius exceeds half the body thickness; verify selected edges")
        elif op_type == "pattern":
            if op.get("pattern_type") not in {"rectangular", "circular"}:
                errors.append(f"{prefix}.pattern_type is invalid")
            if op.get("pattern_type") == "rectangular":
                counts = (op.get("x_count", 1), op.get("y_count", 1))
                if any(not isinstance(count, int) or isinstance(count, bool) or count < 1 for count in counts) or max(counts) < 2:
                    errors.append(f"{prefix}: x_count/y_count must be positive integers and one must be at least 2")
                for axis in ("x", "y"):
                    count, spacing = op.get(f"{axis}_count", 1), op.get(f"{axis}_spacing", 0)
                    if count > 1:
                        _positive(spacing, f"{prefix}.{axis}_spacing", errors)
            elif op.get("pattern_type") == "circular":
                count = op.get("count")
                if not isinstance(count, int) or isinstance(count, bool) or count < 2:
                    errors.append(f"{prefix}.count must be an integer of at least 2")
                if op.get("axis", "z") not in {"x", "y", "z"}:
                    errors.append(f"{prefix}.axis must be x, y, or z")
                angle = op.get("total_angle", 360)
                if not isinstance(angle, (int, float)) or angle <= 0 or angle > 360:
                    errors.append(f"{prefix}.total_angle must be greater than 0 and at most 360")
        if isinstance(op_id, str):
            seen.add(op_id)
    return errors, list(dict.fromkeys(warnings))


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("job", type=Path)
    args = parser.parse_args(argv)
    try:
        job = json.loads(args.job.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"valid": False, "errors": [str(exc)], "warnings": []}, ensure_ascii=False, indent=2))
        return 2
    errors, warnings = validate(job)
    print(json.dumps({"valid": not errors, "errors": errors, "warnings": warnings}, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())

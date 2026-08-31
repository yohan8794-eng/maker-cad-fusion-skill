"""Device-paired Supabase bridge. Live Fusion verification is required."""

import json
import queue
import threading
import time
import traceback

import adsk.core
import adsk.fusion

try:
    from .bridge_client import BridgeClient, BridgeClientError, load_or_create_config
except ImportError:  # Fusion may load an Add-in as a top-level module.
    from bridge_client import BridgeClient, BridgeClientError, load_or_create_config

EVENT_ID = "timely.fusion-cad-job.v1"
POLL_SECONDS = 3
HEARTBEAT_SECONDS = 30
_app = None
_event = None
_handler = None
_stop = threading.Event()
_jobs = queue.Queue()
_poller = None
_client = None


def _poll():
    last_heartbeat = 0
    while not _stop.wait(POLL_SECONDS):
        try:
            now = time.time()
            if now - last_heartbeat >= HEARTBEAT_SECONDS:
                _client.heartbeat()
                last_heartbeat = now
            row = _client.claim_next()
            if not row:
                continue
            _jobs.put(row)
            _app.fireCustomEvent(EVENT_ID)
        except Exception:
            # Avoid Fusion API calls and UI from this worker thread.
            time.sleep(POLL_SECONDS)


def _cm(mm):
    return float(mm) / 10.0


def _find_body(component, name):
    for body in component.bRepBodies:
        if body.name == name:
            return body
    return None


def _execute(job):
    design = adsk.fusion.Design.cast(_app.activeProduct)
    if not design:
        raise RuntimeError("No active Fusion design")
    component = design.rootComponent
    refs = {}
    for operation in job["operations"]:
        kind, op_id = operation["type"], operation["id"]
        if kind == "sketch":
            planes = {"xy": component.xYConstructionPlane, "yz": component.yZConstructionPlane, "xz": component.xZConstructionPlane}
            sketch = component.sketches.add(planes[operation.get("plane", "xy")])
            sketch.name = op_id
            if operation["shape"] == "rectangle":
                ox, oy = operation.get("origin", [0, 0])
                sketch.sketchCurves.sketchLines.addTwoPointRectangle(
                    adsk.core.Point3D.create(_cm(ox), _cm(oy), 0),
                    adsk.core.Point3D.create(_cm(ox + operation["width"]), _cm(oy + operation["height"]), 0),
                )
            elif operation["shape"] == "circle":
                cx, cy = operation.get("centre", [0, 0])
                sketch.sketchCurves.sketchCircles.addByCenterRadius(adsk.core.Point3D.create(_cm(cx), _cm(cy), 0), _cm(operation["diameter"]) / 2)
            refs[op_id] = sketch
        elif kind == "extrude":
            sketch = refs[operation["profile_ref"]]
            profile = sketch.profiles.item(0)
            features = component.features.extrudeFeatures
            modes = {"new_body": adsk.fusion.FeatureOperations.NewBodyFeatureOperation, "join": adsk.fusion.FeatureOperations.JoinFeatureOperation, "cut": adsk.fusion.FeatureOperations.CutFeatureOperation, "intersect": adsk.fusion.FeatureOperations.IntersectFeatureOperation}
            ext_input = features.createInput(profile, modes[operation.get("operation", "new_body")])
            ext_input.setDistanceExtent(False, adsk.core.ValueInput.createByReal(_cm(operation["distance"])))
            feature = features.add(ext_input)
            body = feature.bodies.item(0)
            body.name = op_id
            refs[op_id] = body
        elif kind == "hole":
            body = refs[operation["body_ref"]]
            top = max(body.faces, key=lambda face: face.boundingBox.maxPoint.z)
            for number, (x, y) in enumerate(operation["centres"], 1):
                sketch = component.sketches.add(top)
                sketch.name = f"{op_id}_{number}"
                sketch.sketchPoints.add(adsk.core.Point3D.create(_cm(x), _cm(y), 0))
                holes = component.features.holeFeatures
                hole_input = holes.createSimpleInput(adsk.core.ValueInput.createByReal(_cm(operation["diameter"])))
                hole_input.setPositionBySketchPoint(sketch.sketchPoints.item(0))
                if operation["extent"] == "through_all":
                    hole_input.setAllExtent(adsk.fusion.ExtentDirections.PositiveExtentDirection)
                else:
                    hole_input.setDistanceExtent(adsk.core.ValueInput.createByReal(_cm(operation["depth"])))
                holes.add(hole_input)
            refs[op_id] = body
        elif kind == "fillet":
            body = refs[operation["body_ref"]]
            edges = adsk.core.ObjectCollection.create()
            selection = operation.get("edge_selection", "vertical")
            for edge in body.edges:
                dz = abs(edge.boundingBox.maxPoint.z - edge.boundingBox.minPoint.z)
                if selection == "all" or (selection == "vertical" and dz > 1e-6):
                    edges.add(edge)
            fillets = component.features.filletFeatures
            fillet_input = fillets.createInput()
            fillet_input.edgeSetInputs.addConstantRadiusEdgeSet(edges, adsk.core.ValueInput.createByReal(_cm(operation["radius"])), True)
            refs[op_id] = fillets.add(fillet_input)
        elif kind == "pattern":
            body = refs[operation["source_ref"]]
            entities = adsk.core.ObjectCollection.create()
            entities.add(body)
            if operation["pattern_type"] == "rectangular":
                patterns = component.features.rectangularPatternFeatures
                pattern_input = patterns.createInput(
                    entities,
                    component.xConstructionAxis,
                    adsk.core.ValueInput.createByReal(operation.get("x_count", 1)),
                    adsk.core.ValueInput.createByReal(_cm(operation.get("x_spacing", 0))),
                    adsk.fusion.PatternDistanceType.SpacingPatternDistanceType,
                )
                pattern_input.setDirectionTwo(
                    component.yConstructionAxis,
                    adsk.core.ValueInput.createByReal(operation.get("y_count", 1)),
                    adsk.core.ValueInput.createByReal(_cm(operation.get("y_spacing", 0))),
                )
                refs[op_id] = patterns.add(pattern_input)
            else:
                axes = {"x": component.xConstructionAxis, "y": component.yConstructionAxis, "z": component.zConstructionAxis}
                patterns = component.features.circularPatternFeatures
                pattern_input = patterns.createInput(entities, axes[operation.get("axis", "z")])
                pattern_input.quantity = adsk.core.ValueInput.createByReal(operation["count"])
                pattern_input.totalAngle = adsk.core.ValueInput.createByString(str(operation.get("total_angle", 360)) + " deg")
                refs[op_id] = patterns.add(pattern_input)
        else:
            raise ValueError("Unsupported operation: " + str(kind))
    return {"operation_count": len(job["operations"]), "design": design.parentDocument.name}


class JobHandler(adsk.core.CustomEventHandler):
    def notify(self, args):
        while True:
            try:
                row = _jobs.get_nowait()
            except queue.Empty:
                return
            try:
                result = _execute(row["input_json"])
                _client.finish(row["id"], "completed", result=result)
            except Exception:
                _client.finish(row["id"], "failed", error=traceback.format_exc()[-4000:])


def run(context):
    global _app, _event, _handler, _poller, _client
    _app = adsk.core.Application.get()
    try:
        config = load_or_create_config()
        _client = BridgeClient(config)
        _client.register()
        _stop.clear()
        _event = _app.registerCustomEvent(EVENT_ID)
        _handler = JobHandler()
        _event.add(_handler)
        _poller = threading.Thread(target=_poll, name="FusionCadJobPoller", daemon=True)
        _poller.start()
        _app.userInterface.messageBox("Fusion Local Bridge is ONLINE.\n\nPairing code: " + config["pairing_code"] + "\n\nEnter this code in Timely.")
    except Exception as exc:
        _app.userInterface.messageBox("Fusion Local Bridge could not start:\n" + str(exc))


def stop(context):
    global _event, _handler, _poller
    _stop.set()
    if _poller:
        _poller.join(timeout=2)
    if _event and _handler:
        _event.remove(_handler)
    if _app:
        _app.unregisterCustomEvent(EVENT_ID)
    _event = _handler = _poller = None

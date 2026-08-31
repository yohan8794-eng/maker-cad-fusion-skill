# Fusion360MCP mapping

The installed MCP uses centimetres. Divide every millimetre value by 10 immediately before invoking a Fusion tool.

| CAD Job operation | Existing MCP call |
|---|---|
| rectangle sketch | `create_sketch`, then `draw_rectangle` |
| circle sketch | `create_sketch`, then `draw_circle` |
| extrude | `extrude` |
| hole | `create_hole` once per centre |
| rectangular pattern | `rectangular_pattern` |
| circular pattern | `circular_pattern` |
| fillet | `fillet` |
| inspect | `get_scene_info`, `get_object_info` |
| export | `export_step`, `export_stl`, `export_f3d` |

Do not infer success from a sent command. Require a non-error response and inspect the resulting scene. Record operation ID and tool error on failure.

Re-read the active design at session start. After each geometry-changing command, discard cached face/edge indices and inspect again. Compare measured bounds to `coordinate_system.expected_bounds`; body/feature counts alone do not prove correct geometry.

The current installed tools expose rectangular/circular body patterns. Treat hole-feature or sketch-feature patterning as unsupported until a diagnostic model verifies it. Four explicit hole centres are preferable to an unverified hole pattern.

## Live verification checklist

1. Start Fusion 360 and run `Fusion360MCP` from Scripts and Add-Ins.
2. Require `ping` and `get_scene_info` to succeed.
3. Execute the mounting-plate example in a new unsaved design.
4. Verify one body, four holes, 80 x 50 x 3 mm overall size, and R2 vertical edges.
5. Export a temporary STEP and open or re-import it.
6. Mark the skill live-verified only after all checks pass.

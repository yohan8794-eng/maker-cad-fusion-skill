# CAD Job contract

Use schema version `1.0`. Use millimetres at the job boundary; the Fusion MCP adapter converts mm to its centimetre arguments. Use `ValueInput.createByString("<value> mm")` inside direct Fusion API code when supported to avoid implicit-unit mistakes.

## Required semantics

- `part_type`: `mounting_plate`, `bracket`, or `simple_mount`.
- `parameters`: named source dimensions for review and future regeneration.
- `coordinate_system`: right-handed world coordinates, chosen origin strategy, and expected bounding box for verification.
- `operations`: ordered, stable IDs. References such as `profile_ref`, `body_ref`, and `source_ref` must point to an earlier operation ID.
- `sketch`: use `rectangle` with width/height and an origin, or `circle` with diameter and centre.
- `extrude`: use a positive distance and one of `new_body`, `join`, `cut`, `intersect`.
- `hole`: specify diameter, centres, target body, and `through_all` or a positive blind depth.
- `fillet`: specify radius and semantic edge selection: `all`, `top`, `bottom`, or `vertical`.
- `pattern`: set `source_ref` to a body operation. For `rectangular`, provide `x_count`, `x_spacing`, `y_count`, and `y_spacing` (a direction may use count 1 and spacing 0). For `circular`, provide `count`, `axis` (`x`, `y`, or `z`), and `total_angle` in degrees. Installed MCP support is body-pattern oriented; do not claim patterned hole/features are supported until a live diagnostic proves it.

Named `parameters` are authoritative job inputs. Version 1.0 guarantees deterministic job regeneration and feature history, not fully constrained Fusion sketches or expression-linked Fusion user parameters.

## Job lifecycle

`queued -> claimed -> running -> succeeded|failed`. A worker must claim one job before execution and write a structured result or error. Retrying must create a new attempt or use an atomic claim; never let two runners execute the same queued row.

## Example

See [../assets/examples/mounting-plate.json](../assets/examples/mounting-plate.json). It describes an 80 x 50 x 3 mm plate with four 3.2 mm through holes, 5 mm edge offsets, and R2 vertical fillets.

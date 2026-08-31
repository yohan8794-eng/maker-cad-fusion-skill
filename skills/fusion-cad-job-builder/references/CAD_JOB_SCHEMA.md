# CAD Job 1.0

정식 기계 검증 규격은 `cad-job.schema.json`입니다.

필수 root 필드: `schema_version`, `name`, `part_type`, `units`, `coordinate_system`, `parameters`, `operations`.

- `units`: 항상 `mm`
- `coordinate_system.handedness`: `right`
- `part_type`: `mounting_plate`, `bracket`, `simple_mount`, `sensor_mount`, `motor_mount`, `pcb_mount`, `adapter_plate`
- operation ID는 앞선 operation만 참조합니다.
- `hole.extent=through_all`은 임의 깊이로 바꾸지 않습니다.
- operation 순서는 sketch, extrude/cut, hole, pattern, fillet입니다.

대표 fixture는 `assets/examples/mounting-plate.json`이며 80×50×3 mm 판, Ø3.2 관통홀 4개, 가장자리 5 mm, 수직 모서리 R2를 표현합니다.


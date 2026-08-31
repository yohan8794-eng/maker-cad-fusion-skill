# 사용 방법

1. Fusion을 실행하고 빈 Design을 활성화합니다.
2. Timely에 pairing code를 알려줍니다.
3. “ESP32 고정용 80×50×3 mm 플레이트를 만들어줘”처럼 요청합니다.
4. Timely가 묻는 홀 지름·간격·두께 등 핵심 치수에 답합니다.
5. 검증이 끝나면 Timely가 Job을 제출하고 `completed` 또는 `failed` 결과를 알려줍니다.

지원 부품군은 mounting plate, simple bracket, sensor mount, motor mount, PCB mount, adapter plate입니다. 안정 자동화 범위는 construction plane의 rectangle/circle, extrude/new body/join/cut, 명시 좌표 hole, vertical/all fillet, body linear/circular pattern입니다. Chamfer와 복잡한 bracket은 아직 자동 제출하지 않습니다.

기능 치수가 빠지면 Timely가 질문합니다. AI가 홀 간격, 체결 지름, 판 두께 같은 값을 임의로 정하지 않습니다.


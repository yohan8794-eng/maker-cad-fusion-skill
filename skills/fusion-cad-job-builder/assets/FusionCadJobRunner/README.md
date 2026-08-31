# Fusion Local Bridge

Fusion 360에서 Timely CAD Job을 실행하는 Add-in입니다. Python이나 Git 설치는 필요하지 않습니다.

1. 이 폴더를 쓰기 가능한 위치에 압축 해제합니다.
2. Fusion 360의 `Utilities > Scripts and Add-Ins`에서 이 폴더를 추가합니다.
3. `FusionCadJobRunner`를 실행합니다.
4. 최초 실행 때 생성되는 `config.json`에 장치 ID와 토큰이 안전하게 저장됩니다.
5. 화면에 표시된 10자리 pairing code를 Timely 채팅에 입력합니다.

`config.json`은 다른 사람에게 보내지 마세요. Add-in을 다시 설치할 때 기존 연결을 유지하려면 이 파일을 보관하세요.


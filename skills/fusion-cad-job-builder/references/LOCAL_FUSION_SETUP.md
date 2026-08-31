# Fusion Local Bridge 설치

## 처음 한 번만

1. https://github.com/yohan8794-eng/maker-cad-fusion-skill/releases/latest/download/fusion-local-bridge.zip 에서 `fusion-local-bridge.zip`을 받습니다.
2. ZIP을 문서 폴더처럼 계속 보관할 위치에 압축 해제합니다. ZIP 안의 `FusionCadJobRunner` 폴더를 확인합니다.
3. Fusion 360을 실행합니다.
4. `Utilities`(또는 `Tools`) → `Scripts and Add-Ins`를 엽니다.
5. `Add-Ins` 탭의 `+` 버튼을 눌러 압축을 푼 `FusionCadJobRunner` 폴더를 선택합니다.
6. 목록에서 `FusionCadJobRunner`를 선택하고 `Run`을 누릅니다.
7. `Run on Startup`을 켭니다. 등록은 한 번만 하면 되고, 이후 Fusion 시작 시 Bridge가 자동 실행됩니다.
8. 처음 실행하면 같은 폴더에 개인용 `config.json`이 만들어집니다. 연결 정보가 비어 있다는 안내가 나오면 `config.json`의 Supabase URL과 publishable key를 입력한 뒤 Add-in을 다시 실행합니다. 이 파일은 공유하지 마세요.
9. Fusion 화면에 표시된 10자리 pairing code를 Timely 채팅에 입력합니다.
10. Timely가 ONLINE을 확인하면 설치가 끝납니다.

## 평소 사용

Fusion을 먼저 켜고 Timely에서 부품을 요청하는 것이 가장 간단합니다. Timely를 먼저 켜도 되지만 Fusion이 꺼져 있으면 Bridge는 OFFLINE이며 Job이 제출되지 않습니다. Fusion을 켠 뒤 같은 요청을 계속하면 됩니다.

모델은 실행 시 활성화된 Fusion Design의 Root Component에 생성됩니다. 중요한 문서가 열려 있다면 새 Design을 먼저 여세요.

업데이트가 나오면 새 ZIP을 별도 폴더에 풀고 기존 `config.json`을 새 `FusionCadJobRunner` 폴더로 복사한 뒤 Add-in 경로를 새 폴더로 등록합니다.

Timely용 `maker-cad-fusion-skill.zip`은 AI 스킬이고, PC용 `fusion-local-bridge.zip`은 Fusion Add-in입니다. 서로 바꿔 설치할 수 없습니다.

# 문제 해결

## Bridge가 OFFLINE입니다

- Fusion 360이 실행 중인지 확인합니다.
- `Scripts and Add-Ins`에서 `FusionCadJobRunner`가 실행 중인지 확인합니다.
- pairing code를 공백 없이 다시 입력합니다.
- Add-in을 Stop 후 Run하여 heartbeat를 다시 보냅니다.

## config 오류가 표시됩니다

`FusionCadJobRunner/config.json`을 열어 `supabase_url`과 `supabase_publishable_key`가 비어 있지 않은지 확인합니다. `device_id`, `device_token`, `pairing_code`는 삭제하거나 다른 사람과 공유하지 마세요.

## Job이 failed입니다

활성 문서가 Fusion Design인지 확인하고 새 빈 Design에서 다시 시도합니다. Timely가 보여준 실패 operation과 오류를 함께 확인합니다. 일부 geometry는 Chamfer, face sketch, feature pattern처럼 현재 안정 범위 밖일 수 있습니다.

## 모델을 찾을 수 없습니다

Job 실행 당시 활성화되어 있던 Design의 Root Component와 Timeline을 확인합니다.

## 재설치 후 pairing code가 바뀌었습니다

기존 `config.json`을 새 Add-in 폴더로 복사하면 기존 연결이 유지됩니다. 파일을 잃었다면 새 code를 Timely에 입력합니다.


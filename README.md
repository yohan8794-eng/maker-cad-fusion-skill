# MakerCAD Fusion Skill

자연어 메이커 부품 요구사항을 검증된 CAD Job JSON으로 바꾸고, 장치별로 pairing된 Fusion 360 Add-in에서 실행하는 MABC 2026 / Timely 공개배포 MVP입니다.

- Timely Skill: `skills/fusion-cad-job-builder`
- Fusion Bridge 다운로드: https://github.com/yohan8794-eng/maker-cad-fusion-skill/releases/latest/download/fusion-local-bridge.zip
- Supabase schema: `schema.sql`
- 배포 ZIP 생성: `python build_dist.py`

Bridge는 UUID device ID와 고엔트로피 device token을 로컬 `config.json`에 저장합니다. 서버에는 token hash만 저장되며, Job은 target device별 원자적 claim을 사용합니다. `.env`, `config.json`, service-role key는 배포하지 않습니다.

Fusion 360 실제 GUI 통합은 계정 로그인이 가능한 환경에서 별도 확인이 필요합니다.


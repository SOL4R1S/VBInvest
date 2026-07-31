# 기여 가이드

VBInvest에 관심을 가져주셔서 감사합니다! 이 문서는 개발 환경 설정부터 PR 프로세스까지 안내합니다.

## 개발 환경 설정

1. Python 3.14+, Node 22+ 설치
2. 저장소 클론: `git clone https://github.com/SOL4R1S/VBInvest.git && cd VBInvest`
3. 가상환경: `python -m venv .venv && source .venv/bin/activate`
4. 의존성: `pip install -r requirements.txt -r requirements-dev.txt`
5. 프론트엔드: `cd frontend && npm ci`

## 코드 스타일

- **Backend:** `ruff check --fix scripts/ tests/`, `ruff format scripts/ tests/`, `mypy scripts/`
- **Frontend:** `cd frontend && npm run lint && npm run typecheck`
- **커밋 메시지:** `feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `ci:` 프리픽스 사용

## 테스트

```bash
# 백엔드
python -m pytest -q

# 프론트엔드 유닛
cd frontend && npm test -- --run

# 프론트엔드 e2e (Playwright)
cd frontend && npx playwright test e2e/chart.spec.ts --project=chromium
```

## PR 프로세스

1. `main` 브랜치에서 feature 브랜치 생성 (`feature/xxx`)
2. 변경 사항 구현 + 테스트 추가
3. 로컬에서 ruff/mypy/테스트 통과 확인
4. PR 대상: `main`
5. CI 전부 초록 확인
6. 리뷰어 1명 승인 후 squash merge

## 아키텍처 원칙

- **Local-first:** 사용자 데이터는 로컬 SQLite/PostgreSQL에 저장
- **YAGNI:** 추상화는 두 번째 필요가 생길 때 도입
- **DBRepository Protocol:** SQLite/PG 이중 구현 — 새 DB 메서드는 Protocol + 양쪽 mixin에 추가
- **프론트엔드:** React + TypeScript, `apiGet`/`apiPost` 헬퍼 사용, `readonly` 배열 선호

## 데이터 소스 추가

`scripts/lib/data_source.py`의 `PriceDataSource` Protocol을 구현하고 `PriceSourceRegistry`에 등록하세요. 기존 소스(YahooChart, YFinance, Stooq)를 참고하면 됩니다.

## 질문

이슈를 열어주세요. 버그 리포트는 재현 단계를 포함해 주시면 감사합니다.

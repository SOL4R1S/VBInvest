# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- 플러그인 데이터 소스 아키텍처 (PriceSourceRegistry)
- 커뮤니티 템플릿 API (GET/POST/DELETE /api/templates)
- Docker Compose 선택적 서버 모드
- CSV/데이터 내보내기 (포트폴리오, 거래이력, 워치리스트 가격, 리서치)
- 알림 시스템 (DB + API + 프론트엔드 벨/배지/드롭다운)
- 포트폴리오 수익률 추적 (DB + API + 프론트엔드)
- AI 리서치 품질 개선 (섹터별 프롬프트 템플릿, 소스 인용 검증)
- CONTRIBUTING.md, 이슈 템플릿, CHANGELOG.md

### Changed
- WatchlistDashboard 949줄 → 513줄 오케스트레이터 + 13개 컴포넌트 분할
- migration-smoke CI blocking 전환
- TypedDict/type:ignore 18건 정리

### Fixed
- mypy 에러 0 달성 (blocking)
- 프론트엔드 접근성 개선

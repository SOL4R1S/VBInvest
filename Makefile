.PHONY: test backend-test frontend-test e2e-test secret-scan migration-smoke

test: secret-scan backend-test frontend-test e2e-test

backend-test:
	./.venv/bin/python -m pytest -q

frontend-test:
	cd frontend && npm run lint && npm run typecheck && npm test -- --run && npm run build

e2e-test:
	cd frontend && npx playwright test e2e/chart.spec.ts --project=chromium

secret-scan:
	./.venv/bin/python scripts/secret_scan.py

migration-smoke:
	cd postgres && docker compose up -d
	for file in postgres/init/*.sql; do docker exec vbinvest-postgres psql -U vbinvest -d vbinvest -v ON_ERROR_STOP=1 -f "/docker-entrypoint-initdb.d/$$(basename $$file)"; done

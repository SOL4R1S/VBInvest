.PHONY: test backend-test frontend-test e2e-test secret-scan migration-smoke launcher-smoke package-smoke docker-postgres-smoke

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
	@if command -v docker >/dev/null 2>&1; then \
		cd postgres && docker compose up -d && \
		for file in init/*.sql; do \
			basename_file=$$(basename $$file); \
			docker exec vbinvest-postgres psql -U vbinvest -d vbinvest -v ON_ERROR_STOP=1 -f "/docker-entrypoint-initdb.d/$$basename_file"; \
		done && \
		docker compose down -v; \
	else \
		echo "migration-smoke: SKIP (docker unavailable)"; \
	fi

launcher-smoke:
	@for launcher in VBinvest.command VBinvest.bat VBinvest.ps1; do \
		if [ ! -f "$$launcher" ]; then \
			echo "launcher-smoke: FAIL ($$launcher missing)"; \
			exit 1; \
		fi; \
	done
	@echo "launcher-smoke: PASS"

package-smoke:
	@if [ -f postgres/docker-compose.yml ] && [ -f postgres/.env.example ] && [ -f Makefile ]; then \
		echo "package-smoke: PASS"; \
	else \
		echo "package-smoke: FAIL"; \
		exit 1; \
	fi

docker-postgres-smoke:
	@if command -v docker >/dev/null 2>&1; then \
		cd postgres && docker compose config --quiet; \
	else \
		echo "docker-postgres-smoke: SKIP (docker unavailable)"; \
	fi

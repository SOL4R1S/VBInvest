from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INIT_DIR = ROOT / "postgres" / "init"


def _schema_sql() -> str:
    return "\n".join(path.read_text(encoding="utf-8") for path in sorted(INIT_DIR.glob("*.sql")))


def test_productization_migration_exists():
    assert (INIT_DIR / "005_productization.sql").is_file()


def test_productization_schema_contains_required_tables_and_columns():
    sql = _schema_sql().lower()

    for required in [
        "auth_user_id uuid",
        "create table if not exists entitlements",
        "create table if not exists ad_unlocks",
        "create table if not exists research_sources",
        "create table if not exists obsidian_exports",
        "create table if not exists portfolio_holdings",
        "create table if not exists job_locks",
        "create table if not exists ai_research_runs",
        "create table if not exists payment_webhook_events",
        "create table if not exists audit_logs",
    ]:
        assert required in sql


def test_daily_prices_has_extended_provenance_columns():
    sql = _schema_sql().lower()

    for required in [
        "add column if not exists adj_close",
        "add column if not exists currency",
        "add column if not exists provider",
        "add column if not exists fetched_at",
    ]:
        assert required in sql


def test_news_dedupe_rejects_duplicate_hash():
    sql = _schema_sql().lower()

    assert "ux_news_provider_content_hash" in sql
    assert "on news_items(provider, content_hash)" in sql
    assert "where content_hash is not null" in sql
    assert "create unique index if not exists ux_asset_news_content_hash" not in sql


def test_payment_webhook_events_are_provider_scoped():
    sql = _schema_sql().lower()

    assert "primary key (provider, event_id)" in sql
    assert "event_id text primary key" not in sql

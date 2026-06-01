from scripts.lib.db import DatabaseConfig


def test_database_config_defaults_for_hermes_docker():
    config = DatabaseConfig.from_env({})

    assert config.host == "host.docker.internal"
    assert config.port == 5432
    assert config.database == "vbinvest"
    assert config.user == "vbinvest"


def test_database_config_builds_dsn_with_password_when_requested():
    config = DatabaseConfig.from_env(
        {
            "VBINVEST_DB_HOST": "db.example",
            "VBINVEST_DB_PORT": "15432",
            "VBINVEST_DB_NAME": "customdb",
            "VBINVEST_DB_USER": "customuser",
            "VBINVEST_DB_PASSWORD": "pw",
        }
    )

    assert config.dsn() == "postgresql://customuser:***@db.example:15432/customdb"
    assert config.dsn(mask_password=False) == "postgresql://customuser:pw@db.example:15432/customdb"


def test_database_config_safe_summary_masks_password():
    config = DatabaseConfig.from_env({"VBINVEST_DB_PASSWORD": "pw"})

    summary = config.safe_summary()

    assert "pw" not in summary
    assert "password=***" in summary
    assert "database=vbinvest" in summary


def test_database_config_prefers_macos_keychain_password():
    class FakeStore:
        def get(self, account: str) -> str:
            return "keychain-pw" if account == "POSTGRES_PASSWORD" else ""

    config = DatabaseConfig.from_env(
        {"VBINVEST_DB_PASSWORD": "env-pw"},
        system_name="Darwin",
        secret_store=FakeStore(),
    )

    assert config.password == "keychain-pw"

"""Tests for scripts.lib.db_factory — URL parsing and database construction."""

import pytest

from scripts.lib.db_factory import _database_config_from_url


class TestDatabaseConfigFromUrl:
    def test_basic_postgresql_url(self):
        config = _database_config_from_url("postgresql://user:pass@dbhost:5433/mydb")
        assert config.host == "dbhost"
        assert config.port == 5433
        assert config.database == "mydb"
        assert config.user == "user"
        assert config.password == "pass"

    def test_postgres_scheme_alias(self):
        config = _database_config_from_url("postgres://u:p@h:5432/d")
        assert config.host == "h"
        assert config.database == "d"

    def test_defaults_for_missing_parts(self):
        config = _database_config_from_url("postgresql://localhost")
        assert config.host == "localhost"
        assert config.port == 5432
        assert config.database == "vbinvest"
        assert config.user == "vbinvest"
        assert config.password == ""

    def test_url_encoded_credentials(self):
        config = _database_config_from_url("postgresql://us%40er:p%23ss@h:5432/d")
        assert config.user == "us@er"
        assert config.password == "p#ss"

    def test_rejects_non_postgres_scheme(self):
        with pytest.raises(ValueError, match="postgresql://"):
            _database_config_from_url("mysql://user:pass@host/db")

    def test_rejects_http_scheme(self):
        with pytest.raises(ValueError, match="postgresql://"):
            _database_config_from_url("http://example.com")

    def test_empty_path_defaults_to_vbinvest(self):
        config = _database_config_from_url("postgresql://user@host:5432/")
        assert config.database == "vbinvest"

    def test_custom_port(self):
        config = _database_config_from_url("postgresql://u:p@h:15432/d")
        assert config.port == 15432

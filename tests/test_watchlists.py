from scripts.lib.watchlists import SEMICONDUCTOR_CORE, get_watchlist_symbols


def test_semiconductor_core_has_17_assets():
    assert len(SEMICONDUCTOR_CORE) == 17


def test_semiconductor_core_items_have_required_fields():
    for item in SEMICONDUCTOR_CORE:
        assert item["symbol"]
        assert item["display_name_ko"]


def test_nvda_korean_display_name_is_preserved():
    by_symbol = {item["symbol"]: item for item in SEMICONDUCTOR_CORE}

    assert by_symbol["NVDA"]["display_name_ko"] == "엔비디아"


def test_get_watchlist_symbols_returns_ordered_symbols():
    assert get_watchlist_symbols("semiconductor-core")[:3] == ["SNDK", "005930.KS", "000660.KS"]

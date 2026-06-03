from scripts.lib.ticker_catalog import parse_kind_listed_company_html, refresh_ticker_catalog, search_korean_ticker_catalog


def test_parse_kind_listed_company_html_maps_krx_codes_to_yfinance_symbols():
    html = (
        "<table>"
        "<tr><th>회사명</th><th>시장구분</th><th>종목코드</th></tr>"
        "<tr><td>삼성전자</td><td>유가증권</td><td>005930</td></tr>"
        "<tr><td>테스트코스닥</td><td>코스닥</td><td>123450</td></tr>"
        "</table>"
    )

    tickers = parse_kind_listed_company_html(html)

    assert tickers[0].symbol == "005930.KS"
    assert tickers[0].market == "KSC"
    assert tickers[1].symbol == "123450.KQ"
    assert tickers[1].market == "KOE"


def test_search_korean_ticker_catalog_returns_prefix_matches(monkeypatch):
    monkeypatch.setattr(
        "scripts.lib.ticker_catalog.load_korean_ticker_catalog",
        lambda: parse_kind_listed_company_html(
            "<table>"
            "<tr><th>회사명</th><th>시장구분</th><th>종목코드</th></tr>"
            "<tr><td>삼성전자</td><td>유가증권</td><td>005930</td></tr>"
            "<tr><td>삼성전기</td><td>유가증권</td><td>009150</td></tr>"
            "<tr><td>SK하이닉스</td><td>유가증권</td><td>000660</td></tr>"
            "<tr><td>SK텔레콤</td><td>유가증권</td><td>017670</td></tr>"
            "</table>"
        ),
    )

    samsung = search_korean_ticker_catalog("삼")
    sk = search_korean_ticker_catalog("sk")

    assert [item["symbol"] for item in samsung[:2]] == ["005930.KS", "005935.KS"]
    assert [item["name"] for item in sk[:2]] == ["SK하이닉스", "SK텔레콤"]


def test_refresh_ticker_catalog_reloads_kind_company_list(monkeypatch):
    monkeypatch.setattr(
        "scripts.lib.ticker_catalog._download_kind_listed_company_html",
        lambda: (
            "<table>"
            "<tr><th>회사명</th><th>시장구분</th><th>종목코드</th></tr>"
            "<tr><td>신규상장</td><td>코스닥</td><td>123450</td></tr>"
            "</table>"
        ),
    )

    result = refresh_ticker_catalog()

    assert result.status == "ok"
    assert result.source == "kind"
    assert result.count == 1
    assert search_korean_ticker_catalog("신규")[0]["symbol"] == "123450.KQ"

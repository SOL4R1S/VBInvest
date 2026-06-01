from scripts.lib.disclosures import collect_disclosures_for_asset, normalize_dart_list, normalize_sec_submissions


def test_sec_submissions_normalizes_recent_filings():
    payload = {
        "filings": {
            "recent": {
                "accessionNumber": ["0000320193-26-000001"],
                "form": ["10-Q"],
                "filingDate": ["2026-05-01"],
                "primaryDocument": ["aapl-20260328.htm"],
                "primaryDocDescription": ["Quarterly report"],
            }
        }
    }
    asset = {"asset_id": 7, "symbol": "AAPL", "exchange": "NASDAQ", "cik": "320193"}

    rows = normalize_sec_submissions(asset, payload)

    assert len(rows) == 1
    assert rows[0]["asset_id"] == 7
    assert rows[0]["provider"] == "sec-submissions"
    assert rows[0]["provider_disclosure_id"] == "0000320193-26-000001"
    assert rows[0]["title"] == "10-Q Quarterly report"
    assert rows[0]["url"].endswith("/000032019326000001/aapl-20260328.htm")


def test_dart_missing_key_marks_provider_disabled():
    asset = {"asset_id": 8, "symbol": "005930.KS", "exchange": "KRX", "corp_code": "00126380"}

    result = collect_disclosures_for_asset(asset, dart_api_key=None, no_network=False)

    assert result.status == "provider_disabled"
    assert result.provider_disabled == ["dart:missing-api-key"]
    assert result.items == []


def test_dart_list_normalizes_rows():
    payload = {
        "status": "000",
        "message": "정상",
        "list": [
            {
                "rcept_no": "20260501000001",
                "report_nm": "분기보고서",
                "rcept_dt": "20260501",
                "corp_code": "00126380",
                "corp_name": "삼성전자",
            }
        ],
    }
    asset = {"asset_id": 8, "symbol": "005930.KS", "exchange": "KRX", "corp_code": "00126380"}

    rows = normalize_dart_list(asset, payload)

    assert len(rows) == 1
    assert rows[0]["provider"] == "dart"
    assert rows[0]["provider_disclosure_id"] == "20260501000001"
    assert rows[0]["market"] == "KRX"
    assert rows[0]["url"] == "https://dart.fss.or.kr/dsaf001/main.do?rcpNo=20260501000001"

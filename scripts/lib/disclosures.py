from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


SEC_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
DART_LIST_URL = "https://opendart.fss.or.kr/api/list.json"


class DisclosureFetchError(RuntimeError):
    pass


@dataclass(frozen=True)
class DisclosureFetchResult:
    status: str
    items: list[dict[str, Any]]
    provider_disabled: list[str]


@dataclass(frozen=True, slots=True)
class OpenDartProviderStatus:
    status: str
    provider_code: str | None
    message: str | None


def classify_opendart_status(payload: dict[str, Any]) -> OpenDartProviderStatus:
    provider_code = payload.get("status")
    message = payload.get("message")
    code = provider_code if isinstance(provider_code, str) else None
    text = message if isinstance(message, str) else None
    if code == "000":
        return OpenDartProviderStatus(status="enabled", provider_code=code, message=text)
    if code in {"020", "800"} or "제한" in (text or "").lower() or "limit" in (text or "").lower():
        return OpenDartProviderStatus(status="rate_limited", provider_code=code, message=text)
    return OpenDartProviderStatus(status="provider_error", provider_code=code, message=text)


def check_opendart_api_key(api_key: str) -> OpenDartProviderStatus:
    params = urllib.parse.urlencode({"crtfc_key": api_key, "page_count": "1"})
    request = urllib.request.Request(f"{DART_LIST_URL}?{params}", headers={"User-Agent": "VBinvest/0.1"})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return OpenDartProviderStatus(status="provider_error", provider_code=None, message=str(exc))
    if isinstance(payload, dict):
        return classify_opendart_status(payload)
    return OpenDartProviderStatus(status="provider_error", provider_code=None, message="invalid provider response")


def normalize_sec_submissions(asset: dict[str, Any], payload: dict[str, Any], *, limit: int = 20) -> list[dict[str, Any]]:
    recent = ((payload.get("filings") or {}).get("recent") or {})
    accessions = recent.get("accessionNumber") or []
    forms = recent.get("form") or []
    filing_dates = recent.get("filingDate") or []
    documents = recent.get("primaryDocument") or []
    descriptions = recent.get("primaryDocDescription") or []
    cik = str(asset.get("cik") or "").zfill(10)

    rows: list[dict[str, Any]] = []
    for index, accession in enumerate(accessions[:limit]):
        form = _at(forms, index) or "SEC filing"
        description = _at(descriptions, index)
        document = _at(documents, index)
        title = f"{form} {description}".strip() if description else form
        accession_path = str(accession).replace("-", "")
        rows.append(
            {
                "asset_id": asset.get("asset_id"),
                "market": "US",
                "provider": "sec-submissions",
                "provider_disclosure_id": accession,
                "title": title,
                "published_at": parse_yyyymmdd(_at(filing_dates, index), dashed=True),
                "url": sec_filing_url(cik, accession_path, document),
                "raw_json": {
                    "symbol": asset.get("symbol"),
                    "accessionNumber": accession,
                    "form": form,
                    "filingDate": _at(filing_dates, index),
                    "primaryDocument": document,
                },
            }
        )
    return rows


def normalize_dart_list(asset: dict[str, Any], payload: dict[str, Any]) -> list[dict[str, Any]]:
    if payload.get("status") not in (None, "000"):
        raise DisclosureFetchError(f"{asset.get('symbol')}: dart status {payload.get('status')} {payload.get('message')}")

    rows: list[dict[str, Any]] = []
    for item in payload.get("list") or []:
        receipt_no = item.get("rcept_no")
        title = item.get("report_nm")
        if not receipt_no or not title:
            continue
        rows.append(
            {
                "asset_id": asset.get("asset_id"),
                "market": asset.get("exchange") or "KRX",
                "provider": "dart",
                "provider_disclosure_id": receipt_no,
                "title": title,
                "published_at": parse_yyyymmdd(item.get("rcept_dt"), dashed=False),
                "url": f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={urllib.parse.quote(receipt_no)}",
                "raw_json": item,
            }
        )
    return rows


def collect_disclosures_for_asset(
    asset: dict[str, Any],
    *,
    dart_api_key: str | None,
    no_network: bool = False,
    sec_fetcher=None,
    dart_fetcher=None,
) -> DisclosureFetchResult:
    disabled: list[str] = []
    items: list[dict[str, Any]] = []
    if no_network:
        return DisclosureFetchResult(status="provider_disabled", items=[], provider_disabled=["disclosures:no-network"])

    if _is_us_asset(asset):
        cik = asset.get("cik")
        if not cik:
            disabled.append("sec:missing-cik")
        else:
            fetcher = sec_fetcher or fetch_sec_submissions
            items.extend(fetcher(str(cik), asset))
    else:
        corp_code = asset.get("corp_code")
        if not dart_api_key:
            disabled.append("dart:missing-api-key")
        elif not corp_code:
            disabled.append("dart:missing-corp-code")
        else:
            fetcher = dart_fetcher or fetch_dart_disclosures
            items.extend(fetcher(dart_api_key, str(corp_code), asset))

    if items:
        return DisclosureFetchResult(status="ok", items=items, provider_disabled=disabled)
    if disabled:
        return DisclosureFetchResult(status="provider_disabled", items=[], provider_disabled=disabled)
    return DisclosureFetchResult(status="ok", items=[], provider_disabled=[])


def fetch_sec_submissions(cik: str, asset: dict[str, Any]) -> list[dict[str, Any]]:
    url = SEC_SUBMISSIONS_URL.format(cik=str(cik).zfill(10))
    request = urllib.request.Request(url, headers={"User-Agent": "VBinvest/0.1 contact@example.com"})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DisclosureFetchError(f"{asset.get('symbol')}: sec fetch failed: {exc}") from exc
    return normalize_sec_submissions(asset, payload)


def fetch_dart_disclosures(api_key: str, corp_code: str, asset: dict[str, Any]) -> list[dict[str, Any]]:
    params = urllib.parse.urlencode(
        {
            "crtfc_key": api_key,
            "corp_code": corp_code,
            "page_count": "100",
            "sort": "date",
            "sort_mth": "desc",
        }
    )
    request = urllib.request.Request(f"{DART_LIST_URL}?{params}", headers={"User-Agent": "VBinvest/0.1"})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DisclosureFetchError(f"{asset.get('symbol')}: dart fetch failed: {exc}") from exc
    return normalize_dart_list(asset, payload)


def parse_yyyymmdd(value: str | None, *, dashed: bool) -> datetime | None:
    if not value:
        return None
    fmt = "%Y-%m-%d" if dashed else "%Y%m%d"
    return datetime.strptime(value, fmt).replace(tzinfo=timezone.utc)


def sec_filing_url(cik: str, accession_path: str, document: str | None) -> str:
    if not document:
        return f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession_path}/"
    return f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession_path}/{urllib.parse.quote(document)}"


def _is_us_asset(asset: dict[str, Any]) -> bool:
    return (asset.get("exchange") or "").upper() in {"NASDAQ", "NYSE", "AMEX", "ARCA", "BATS", "US"}


def _at(values: list[Any], index: int) -> Any:
    if index >= len(values):
        return None
    return values[index]

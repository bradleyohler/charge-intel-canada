from __future__ import annotations

from unittest.mock import MagicMock, patch

import requests

from ingestion.sources.scrapers.base import PricingRecord
from ingestion.sources.scrapers.chargepoint_ca import ChargePointCAScraper
from ingestion.sources.scrapers.flo import FloScraper

_ALLOWED_PRICING_MODELS = {
    "per_kwh",
    "per_minute",
    "flat_fee",
    "session_plus_kwh",
    "unknown",
}


def _assert_sane_records(
    records: list[PricingRecord], expected_network_name: str
) -> None:
    assert isinstance(records, list)
    assert len(records) > 0
    for record in records:
        assert record.network_name == expected_network_name
        assert record.currency == "CAD"
        assert record.pricing_model in _ALLOWED_PRICING_MODELS
        if record.pricing_model == "session_plus_kwh":
            assert record.session_fee_value is not None
        else:
            assert record.session_fee_value is None


# ---------------------------------------------------------------------------
# FLO scraper tests
# ---------------------------------------------------------------------------

_FLO_HTML_WITH_RATES = (
    "<table><tr><td>DC Fast Charging: $0.45/kWh</td></tr>"
    "<tr><td>Level 2: $0.02/minute</td></tr></table>"
)


def test_flo_scraper_returns_sane_records_on_successful_fetch() -> None:
    mock_response = MagicMock()
    mock_response.text = _FLO_HTML_WITH_RATES
    mock_response.raise_for_status = MagicMock()

    with patch("requests.get", return_value=mock_response):
        scraper = FloScraper()
        records = scraper.scrape()

    _assert_sane_records(records, "FLO")


def test_flo_scraper_falls_back_when_http_request_fails() -> None:
    with patch("requests.get", side_effect=requests.RequestException("boom")):
        scraper = FloScraper()
        records = scraper.scrape()

    _assert_sane_records(records, "FLO")
    # Fallback data should include province-level DCFC rates.
    provinces = {r.province_code for r in records if r.province_code is not None}
    assert "ON" in provinces


def test_flo_scraper_does_not_raise_when_page_structure_is_unparseable() -> None:
    mock_response = MagicMock()
    mock_response.text = "<html><body>No pricing info here</body></html>"
    mock_response.raise_for_status = MagicMock()

    with patch("requests.get", return_value=mock_response):
        scraper = FloScraper()
        records = scraper.scrape()

    _assert_sane_records(records, "FLO")


# ---------------------------------------------------------------------------
# ChargePoint CA scraper tests
# ---------------------------------------------------------------------------

_CHARGEPOINT_HTML_WITH_RATES = (
    "<div>DCFC pricing example: $0.25/kWh plus $0.10/minute</div>"
)


def test_chargepoint_ca_scraper_returns_sane_records_on_successful_fetch() -> None:
    mock_response = MagicMock()
    mock_response.text = _CHARGEPOINT_HTML_WITH_RATES
    mock_response.raise_for_status = MagicMock()

    with patch("requests.get", return_value=mock_response):
        scraper = ChargePointCAScraper()
        records = scraper.scrape()

    _assert_sane_records(records, "ChargePoint CA")


def test_chargepoint_ca_scraper_falls_back_when_http_request_fails() -> None:
    with patch("requests.get", side_effect=requests.RequestException("boom")):
        scraper = ChargePointCAScraper()
        records = scraper.scrape()

    _assert_sane_records(records, "ChargePoint CA")
    sp_records = [r for r in records if r.pricing_model == "session_plus_kwh"]
    assert len(sp_records) > 0
    assert all(r.session_fee_value is not None for r in sp_records)


def test_chargepoint_ca_does_not_raise_when_page_structure_is_unparseable() -> None:
    mock_response = MagicMock()
    mock_response.text = "<html><body>No pricing info here</body></html>"
    mock_response.raise_for_status = MagicMock()

    with patch("requests.get", return_value=mock_response):
        scraper = ChargePointCAScraper()
        records = scraper.scrape()

    _assert_sane_records(records, "ChargePoint CA")

from __future__ import annotations

from unittest.mock import MagicMock, patch

import requests

from ingestion.sources.scrapers.base import PricingRecord

_ALLOWED_PRICING_MODELS = {
    "per_kwh",
    "per_minute",
    "flat_fee",
    "session_plus_kwh",
    "unknown",
}


def _assert_sane_records(records: list[PricingRecord], expected_network: str) -> None:
    assert isinstance(records, list)
    assert len(records) > 0
    for record in records:
        assert isinstance(record, PricingRecord)
        assert record.network_name == expected_network
        assert record.currency == "CAD"
        assert record.pricing_model in _ALLOWED_PRICING_MODELS
        assert record.rate_value is not None
        assert record.rate_value > 0


# ---------------------------------------------------------------------------
# Tesla
# ---------------------------------------------------------------------------

_TESLA_HTML_WITH_RATE = (
    "<html><body><p>Supercharging costs $0.43/kWh in most regions.</p>" "</body></html>"
)


def test_tesla_scraper_returns_sane_records_on_successful_fetch() -> None:
    mock_response = MagicMock()
    mock_response.text = _TESLA_HTML_WITH_RATE
    mock_response.raise_for_status = MagicMock()

    with patch("requests.get", return_value=mock_response):
        from ingestion.sources.scrapers.tesla import TeslaScraper

        records = TeslaScraper().scrape()

    _assert_sane_records(records, "Tesla")
    assert all(r.pricing_model == "per_kwh" for r in records)
    assert all(r.rate_unit == "cad_per_kwh" for r in records)
    tiers = {r.membership_tier for r in records}
    assert "member" in tiers
    assert "non_member" in tiers


def test_tesla_scraper_falls_back_when_http_fails() -> None:
    with patch("requests.get", side_effect=requests.RequestException("boom")):
        from ingestion.sources.scrapers.tesla import TeslaScraper

        records = TeslaScraper().scrape()

    _assert_sane_records(records, "Tesla")


# ---------------------------------------------------------------------------
# Petro-Canada
# ---------------------------------------------------------------------------

_PETRO_CANADA_HTML_WITH_RATE = (
    "<html><body><p>DC fast charging costs $0.50/minute on our network.</p>"
    "</body></html>"
)


def test_petro_canada_scraper_returns_sane_records_on_successful_fetch() -> None:
    mock_response = MagicMock()
    mock_response.text = _PETRO_CANADA_HTML_WITH_RATE
    mock_response.raise_for_status = MagicMock()

    with patch("requests.get", return_value=mock_response):
        from ingestion.sources.scrapers.petro_canada import PetroCanadaScraper

        records = PetroCanadaScraper().scrape()

    _assert_sane_records(records, "Petro-Canada")
    assert all(r.pricing_model == "per_minute" for r in records)
    assert all(r.rate_unit == "cad_per_minute" for r in records)
    assert all(r.membership_tier == "pay_as_you_go" for r in records)


def test_petro_canada_scraper_falls_back_when_http_fails() -> None:
    with patch("requests.get", side_effect=requests.RequestException("boom")):
        from ingestion.sources.scrapers.petro_canada import PetroCanadaScraper

        records = PetroCanadaScraper().scrape()

    _assert_sane_records(records, "Petro-Canada")


# ---------------------------------------------------------------------------
# IVY
# ---------------------------------------------------------------------------

_IVY_HTML_WITH_RATE = (
    "<html><body><p>Charging on the Ivy network costs $0.69/kWh.</p></body></html>"
)


def test_ivy_scraper_returns_sane_records_on_successful_fetch() -> None:
    mock_response = MagicMock()
    mock_response.text = _IVY_HTML_WITH_RATE
    mock_response.raise_for_status = MagicMock()

    with patch("requests.get", return_value=mock_response):
        from ingestion.sources.scrapers.ivy import IVYScraper

        records = IVYScraper().scrape()

    _assert_sane_records(records, "IVY")
    assert all(r.pricing_model == "per_kwh" for r in records)
    assert all(r.rate_unit == "cad_per_kwh" for r in records)
    assert all(r.province_code == "ON" for r in records)


def test_ivy_scraper_falls_back_when_http_fails() -> None:
    with patch("requests.get", side_effect=requests.RequestException("boom")):
        from ingestion.sources.scrapers.ivy import IVYScraper

        records = IVYScraper().scrape()

    _assert_sane_records(records, "IVY")

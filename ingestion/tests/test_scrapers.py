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

# ---------------------------------------------------------------------------
# BC Hydro EV
# ---------------------------------------------------------------------------

_BC_HYDRO_HTML_WITH_RATE = (
    "<table><tr><td>DC Fast Charging</td><td>$0.28/kWh</td></tr></table>"
)
_BC_HYDRO_HTML_NO_RATE = "<p>No pricing data available here.</p>"


def test_bc_hydro_ev_scrape_returns_records_from_live_page() -> None:
    mock_response = MagicMock()
    mock_response.text = _BC_HYDRO_HTML_WITH_RATE
    mock_response.raise_for_status = MagicMock()

    with patch("requests.get", return_value=mock_response):
        from ingestion.sources.scrapers.bc_hydro_ev import BCHydroEVScraper

        records = BCHydroEVScraper().scrape()

    assert isinstance(records, list)
    assert len(records) > 0
    for record in records:
        assert isinstance(record, PricingRecord)
        assert record.network_name == "BC Hydro EV"
        assert record.currency == "CAD"
        assert record.pricing_model in _ALLOWED_PRICING_MODELS
        assert record.rate_value is not None
        assert record.rate_value > 0


def test_bc_hydro_ev_scrape_falls_back_when_page_unparseable() -> None:
    mock_response = MagicMock()
    mock_response.text = _BC_HYDRO_HTML_NO_RATE
    mock_response.raise_for_status = MagicMock()

    with patch("requests.get", return_value=mock_response):
        from ingestion.sources.scrapers.bc_hydro_ev import BCHydroEVScraper

        records = BCHydroEVScraper().scrape()

    assert isinstance(records, list)
    assert len(records) > 0
    assert records[0].rate_value is not None


def test_bc_hydro_ev_scrape_falls_back_on_request_exception() -> None:
    with patch("requests.get", side_effect=requests.RequestException("boom")):
        from ingestion.sources.scrapers.bc_hydro_ev import BCHydroEVScraper

        records = BCHydroEVScraper().scrape()

    assert isinstance(records, list)
    assert len(records) > 0
    for record in records:
        assert record.network_name == "BC Hydro EV"
        assert record.currency == "CAD"
        assert record.pricing_model in _ALLOWED_PRICING_MODELS
        assert record.rate_value is not None


# ---------------------------------------------------------------------------
# Electrify Canada
# ---------------------------------------------------------------------------

_ELECTRIFY_HTML_WITH_RATES = (
    "<div>British Columbia stations: $0.70/kWh</div>"
    "<div>Alberta stations: $0.60/kWh</div>"
)
_ELECTRIFY_HTML_NO_RATE = "<p>No pricing data available here.</p>"


def test_electrify_canada_scrape_returns_records_from_live_page() -> None:
    mock_response = MagicMock()
    mock_response.text = _ELECTRIFY_HTML_WITH_RATES
    mock_response.raise_for_status = MagicMock()

    with patch("requests.get", return_value=mock_response):
        from ingestion.sources.scrapers.electrify_canada import (
            ElectrifyCanadaScraper,
        )

        records = ElectrifyCanadaScraper().scrape()

    assert isinstance(records, list)
    assert len(records) > 0
    for record in records:
        assert isinstance(record, PricingRecord)
        assert record.network_name == "Electrify Canada"
        assert record.currency == "CAD"
        assert record.pricing_model in _ALLOWED_PRICING_MODELS
        assert record.rate_value is not None
        assert record.rate_value > 0

    tiers = {record.membership_tier for record in records}
    assert "guest" in tiers
    assert "pass_plus" in tiers


def test_electrify_canada_scrape_pass_plus_cheaper_than_guest() -> None:
    mock_response = MagicMock()
    mock_response.text = _ELECTRIFY_HTML_WITH_RATES
    mock_response.raise_for_status = MagicMock()

    with patch("requests.get", return_value=mock_response):
        from ingestion.sources.scrapers.electrify_canada import (
            ElectrifyCanadaScraper,
        )

        records = ElectrifyCanadaScraper().scrape()

    by_tier_and_province: dict[tuple[str | None, str], float] = {
        (record.province_code, record.membership_tier): record.rate_value
        for record in records
        if record.rate_value is not None
    }
    provinces = {record.province_code for record in records}
    for province_code in provinces:
        guest_rate = by_tier_and_province.get((province_code, "guest"))
        pass_plus_rate = by_tier_and_province.get((province_code, "pass_plus"))
        assert guest_rate is not None
        assert pass_plus_rate is not None
        assert pass_plus_rate < guest_rate


def test_electrify_canada_scrape_falls_back_when_page_unparseable() -> None:
    mock_response = MagicMock()
    mock_response.text = _ELECTRIFY_HTML_NO_RATE
    mock_response.raise_for_status = MagicMock()

    with patch("requests.get", return_value=mock_response):
        from ingestion.sources.scrapers.electrify_canada import (
            ElectrifyCanadaScraper,
        )

        records = ElectrifyCanadaScraper().scrape()

    assert isinstance(records, list)
    assert len(records) > 0


def test_electrify_canada_scrape_falls_back_on_request_exception() -> None:
    with patch("requests.get", side_effect=requests.RequestException("boom")):
        from ingestion.sources.scrapers.electrify_canada import (
            ElectrifyCanadaScraper,
        )

        records = ElectrifyCanadaScraper().scrape()

    assert isinstance(records, list)
    assert len(records) > 0
    for record in records:
        assert record.network_name == "Electrify Canada"
        assert record.currency == "CAD"
        assert record.pricing_model in _ALLOWED_PRICING_MODELS
        assert record.rate_value is not None

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

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
import requests


def test_load_config_raises_on_missing_env(monkeypatch: pytest.MonkeyPatch) -> None:
    from ingestion.config import load_config

    env_vars = [
        "AFDC_API_KEY",
        "SNOWFLAKE_ACCOUNT",
        "SNOWFLAKE_USER",
        "SNOWFLAKE_PRIVATE_KEY_PATH",
        "SNOWFLAKE_WAREHOUSE",
        "SNOWFLAKE_DATABASE",
        "SNOWFLAKE_ROLE",
    ]
    for var in env_vars:
        monkeypatch.delenv(var, raising=False)

    with pytest.raises(
        EnvironmentError, match="Missing required environment variables"
    ):
        load_config()


def test_fetch_ev_networks_returns_dataframe() -> None:
    mock_response = MagicMock()
    mock_response.json.return_value = [
        {
            "key": "CHARGEPOINT",
            "name": "ChargePoint",
            "name_fr": "ChargePoint",
            "url": "https://www.chargepoint.com",
            "last_import_date": "2026-06-17",
            "date_added": "2013-01-01",
            "date_removed": None,
            "import_type": "API",
        },
        {
            "key": "FLO",
            "name": "FLO",
            "name_fr": "FLO",
            "url": "https://www.flo.com",
            "last_import_date": "2026-06-17",
            "date_added": "2017-07-11",
            "date_removed": None,
            "import_type": "API",
        },
    ]
    mock_response.raise_for_status = MagicMock()

    with patch("requests.get", return_value=mock_response):
        from ingestion.sources.afdc import fetch_ev_networks

        df = fetch_ev_networks("test-api-key")

    assert isinstance(df, pd.DataFrame)
    assert len(df) == 2
    assert "key" in df.columns
    assert "name" in df.columns


def test_fetch_ev_charging_units_drops_rows_missing_lat_lon() -> None:
    csv_content = (
        "fuel_type_code,station_name,city,state,latitude,longitude\n"
        "ELEC,Good Station,Toronto,ON,43.6532,-79.3832\n"
        "ELEC,No Lat Station,Vancouver,BC,,\n"
        "ELEC,Another Good,Calgary,AB,51.0447,-114.0719\n"
    )
    mock_response = MagicMock()
    mock_response.text = csv_content
    mock_response.raise_for_status = MagicMock()

    with patch("requests.get", return_value=mock_response):
        from ingestion.sources.afdc import fetch_ev_charging_units

        df = fetch_ev_charging_units("test-key")

    assert isinstance(df, pd.DataFrame)
    assert len(df) == 2, "Row missing lat/lon should have been dropped"


_CE_CSV_TWO_PORTS = (
    "Nom de la borne de recharge,Nom du parc,Adresse,Rue,Suite,Ville,Province,"
    "Code Postal,Région,Niveau de recharge,Latitude,Longitude,Coût,"
    "Mode de tarification,Type d'emplacement,Puissance (kW)\n"
    "CEA-001,Parc Test,10 Rue Test,10 Rue Test,,Montréal,QC,H2X 1Y6,"
    "Montréal,Niveau 2,45.5017,-73.5673,Free,Flat,Public,7.2\n"
    "CEA-002,Parc Test,10 Rue Test,10 Rue Test,,Montréal,QC,H2X 1Y6,"
    "Montréal,Niveau 2,45.5017,-73.5673,Free,Flat,Public,7.2\n"
)

_CE_EXPECTED_COLUMNS = [
    "station_id",
    "latitude",
    "longitude",
    "station_name",
    "street_address",
    "city",
    "province_code",
    "postal_code",
    "network_name",
    "status_code",
    "l1_port_count",
    "l2_port_count",
    "dcfc_port_count",
]


def test_fetch_circuit_electrique_returns_dataframe() -> None:
    mock_response = MagicMock()
    mock_response.text = _CE_CSV_TWO_PORTS
    mock_response.raise_for_status = MagicMock()

    with patch("requests.get", return_value=mock_response):
        from ingestion.sources.circuit_electrique import fetch_circuit_electrique

        result = fetch_circuit_electrique()

    assert isinstance(result, pd.DataFrame)
    assert (
        len(result) == 1
    ), "Two ports at the same location should aggregate to one station"
    for col in _CE_EXPECTED_COLUMNS:
        assert col in result.columns, f"Expected column '{col}' missing from result"
    assert result["l2_port_count"].iloc[0] == 2
    assert result["l1_port_count"].iloc[0] == 0
    assert result["dcfc_port_count"].iloc[0] == 0


def test_fetch_circuit_electrique_drops_rows_missing_lat_lon() -> None:
    csv_text = (
        "Nom de la borne de recharge,Nom du parc,Adresse,Rue,Suite,Ville,Province,"
        "Code Postal,Région,Niveau de recharge,Latitude,Longitude,Coût,"
        "Mode de tarification,Type d'emplacement,Puissance (kW)\n"
        "CEA-001,Parc A,1 Rue A,1 Rue A,,Québec,QC,G1R 1A1,"
        "Québec,Niveau 2,45.5,-73.5,Free,Flat,Public,7.2\n"
        "CEA-002,Parc A,1 Rue A,1 Rue A,,Québec,QC,G1R 1A1,"
        "Québec,Niveau 2,45.5,-73.5,Free,Flat,Public,7.2\n"
        "CEA-003,Parc B,2 Rue B,2 Rue B,,Laval,QC,H7T 2T8,"
        "Laval,Niveau 1,,,Free,Flat,Public,1.4\n"
    )
    mock_response = MagicMock()
    mock_response.text = csv_text
    mock_response.raise_for_status = MagicMock()

    with patch("requests.get", return_value=mock_response):
        from ingestion.sources.circuit_electrique import fetch_circuit_electrique

        result = fetch_circuit_electrique()

    assert (
        len(result) == 1
    ), "Port with missing lat/lon should be dropped after aggregation"


def test_fetch_circuit_electrique_province_always_qc() -> None:
    mock_response = MagicMock()
    mock_response.text = _CE_CSV_TWO_PORTS
    mock_response.raise_for_status = MagicMock()

    with patch("requests.get", return_value=mock_response):
        from ingestion.sources.circuit_electrique import fetch_circuit_electrique

        result = fetch_circuit_electrique()

    assert (
        result["province_code"] == "QC"
    ).all(), "All CE stations should have province_code == 'QC'"


def test_fetch_circuit_electrique_raises_on_http_error() -> None:
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock(side_effect=requests.HTTPError())

    with patch("requests.get", return_value=mock_response):
        from ingestion import IngestionError
        from ingestion.sources.circuit_electrique import fetch_circuit_electrique

        with pytest.raises(IngestionError):
            fetch_circuit_electrique()


# ---------------------------------------------------------------------------
# CER Rates tests
# ---------------------------------------------------------------------------

_CER_HTML_WITH_RATE = (
    "<p>The residential flat rate is 9.87 ¢/kW.h including all taxes.</p>"
)
_CER_HTML_NO_RATE = "<p>No pricing data available here.</p>"
_CER_HTML_TD_RATE = "<table><tr><td>8.45 ¢/kW.h</td></tr></table>"


def test_fetch_cer_rates_returns_dataframe() -> None:
    mock_response = MagicMock()
    mock_response.text = _CER_HTML_WITH_RATE
    mock_response.raise_for_status = MagicMock()

    with patch("requests.get", return_value=mock_response):
        from ingestion.sources.cer_rates import fetch_cer_rates

        result = fetch_cer_rates()

    assert isinstance(result, pd.DataFrame)
    required_columns = [
        "province_code",
        "rate_type",
        "period",
        "rate_value",
        "rate_unit",
        "effective_date",
    ]
    for col in required_columns:
        assert col in result.columns, f"Expected column '{col}' missing from result"
    assert len(result) > 0


def test_fetch_cer_rates_drops_provinces_with_no_rate_in_html() -> None:
    mock_response = MagicMock()
    mock_response.text = _CER_HTML_NO_RATE
    mock_response.raise_for_status = MagicMock()

    with patch("requests.get", return_value=mock_response):
        from ingestion import IngestionError
        from ingestion.sources.cer_rates import fetch_cer_rates

        with pytest.raises(IngestionError):
            fetch_cer_rates()


def test_fetch_cer_rates_skips_provinces_with_http_error() -> None:
    with patch("requests.get", side_effect=requests.HTTPError()):
        from ingestion import IngestionError
        from ingestion.sources.cer_rates import fetch_cer_rates

        with pytest.raises(IngestionError):
            fetch_cer_rates()


def test_fetch_cer_rates_rate_value_is_float() -> None:
    mock_response = MagicMock()
    mock_response.text = _CER_HTML_TD_RATE
    mock_response.raise_for_status = MagicMock()

    with patch("requests.get", return_value=mock_response):
        from ingestion.sources.cer_rates import fetch_cer_rates

        result = fetch_cer_rates()

    assert pd.api.types.is_float_dtype(
        result["rate_value"]
    ), f"Expected float dtype for rate_value, got {result['rate_value'].dtype}"


def test_fetch_cer_rates_province_codes_are_uppercase_two_letter() -> None:
    mock_response = MagicMock()
    mock_response.text = _CER_HTML_WITH_RATE
    mock_response.raise_for_status = MagicMock()

    with patch("requests.get", return_value=mock_response):
        from ingestion.sources.cer_rates import fetch_cer_rates

        result = fetch_cer_rates()

    import re as _re

    for code in result["province_code"]:
        assert isinstance(code, str), f"province_code {code!r} is not a string"
        assert len(code) == 2, f"province_code {code!r} is not 2 characters"
        assert _re.match(
            r"^[A-Z]{2}$", code
        ), f"province_code {code!r} does not match ^[A-Z]{{2}}$"


# ---------------------------------------------------------------------------
# StatCan Population tests
# ---------------------------------------------------------------------------

_STATCAN_CSV_TWO_FSAS = (
    "GEO_LEVEL,ALT_GEO_CODE,CHARACTERISTIC_NAME,C1_COUNT_TOTAL\n"
    'Forward sortation area,K7G,"Population, 2021",12345\n'
    "Forward sortation area,K7G,Land area in square kilometres,250.5\n"
    'Forward sortation area,H2X,"Population, 2021",67890\n'
    "Forward sortation area,H2X,Land area in square kilometres,8.3\n"
)

_STATCAN_CSV_MULTI_PROVINCE = (
    "GEO_LEVEL,ALT_GEO_CODE,CHARACTERISTIC_NAME,C1_COUNT_TOTAL\n"
    'Forward sortation area,A0A,"Population, 2021",5000\n'
    'Forward sortation area,V6B,"Population, 2021",20000\n'
    'Forward sortation area,T2P,"Population, 2021",15000\n'
    'Forward sortation area,X0A,"Population, 2021",1000\n'
    'Forward sortation area,X1A,"Population, 2021",2000\n'
    'Forward sortation area,H3B,"Population, 2021",30000\n'
    'Forward sortation area,K1A,"Population, 2021",25000\n'
)

_STATCAN_CSV_MISSING_POP = (
    "GEO_LEVEL,ALT_GEO_CODE,CHARACTERISTIC_NAME,C1_COUNT_TOTAL\n"
    "Forward sortation area,M5V,Land area in square kilometres,12.1\n"
    'Forward sortation area,K1A,"Population, 2021",25000\n'
    "Forward sortation area,K1A,Land area in square kilometres,180.0\n"
)

_STATCAN_CSV_NO_MATCHING_CHARS = (
    "GEO_LEVEL,ALT_GEO_CODE,CHARACTERISTIC_NAME,C1_COUNT_TOTAL\n"
    'Forward sortation area,K7G,"Dwellings, 2021",4500\n'
    'Forward sortation area,H2X,"Dwellings, 2021",8100\n'
)


def test_fetch_statcan_population_returns_dataframe() -> None:
    mock_response = MagicMock()
    mock_response.content = _STATCAN_CSV_TWO_FSAS.encode("latin-1")
    mock_response.raise_for_status = MagicMock()

    with patch("requests.get", return_value=mock_response):
        from ingestion.sources.statcan import fetch_statcan_population

        result = fetch_statcan_population()

    assert isinstance(result, pd.DataFrame)
    for col in ["fsa", "province_code", "population", "area_sq_km"]:
        assert col in result.columns, f"Expected column '{col}' missing from result"
    assert len(result) == 2


def test_fetch_statcan_population_derives_province_code_correctly() -> None:
    mock_response = MagicMock()
    mock_response.content = _STATCAN_CSV_MULTI_PROVINCE.encode("latin-1")
    mock_response.raise_for_status = MagicMock()

    with patch("requests.get", return_value=mock_response):
        from ingestion.sources.statcan import fetch_statcan_population

        result = fetch_statcan_population()

    expected = {
        "A0A": "NL",
        "V6B": "BC",
        "T2P": "AB",
        "X0A": "NU",
        "X1A": "NT",
        "H3B": "QC",
        "K1A": "ON",
    }
    fsa_to_province = dict(zip(result["fsa"], result["province_code"]))
    for fsa, expected_province in expected.items():
        assert fsa in fsa_to_province, f"FSA {fsa!r} not found in result"
        assert fsa_to_province[fsa] == expected_province, (
            f"FSA {fsa!r}: expected province {expected_province!r}, "
            f"got {fsa_to_province[fsa]!r}"
        )


def test_fetch_statcan_population_raises_ingestion_error_on_http_error() -> None:
    mock_response = MagicMock()
    mock_response.content = b""
    mock_response.raise_for_status = MagicMock(side_effect=requests.HTTPError())

    with patch("requests.get", return_value=mock_response):
        from ingestion import IngestionError
        from ingestion.sources.statcan import fetch_statcan_population

        with pytest.raises(IngestionError):
            fetch_statcan_population()


def test_fetch_statcan_population_drops_rows_missing_population() -> None:
    mock_response = MagicMock()
    mock_response.content = _STATCAN_CSV_MISSING_POP.encode("latin-1")
    mock_response.raise_for_status = MagicMock()

    with patch("requests.get", return_value=mock_response):
        from ingestion.sources.statcan import fetch_statcan_population

        result = fetch_statcan_population()

    assert (
        len(result) == 1
    ), "FSA with no population row should be dropped; only K1A should remain"
    assert result["fsa"].iloc[0] == "K1A"


def test_fetch_statcan_population_raises_ingestion_error_on_empty_result() -> None:
    mock_response = MagicMock()
    mock_response.content = _STATCAN_CSV_NO_MATCHING_CHARS.encode("latin-1")
    mock_response.raise_for_status = MagicMock()

    with patch("requests.get", return_value=mock_response):
        from ingestion import IngestionError
        from ingestion.sources.statcan import fetch_statcan_population

        with pytest.raises(IngestionError):
            fetch_statcan_population()

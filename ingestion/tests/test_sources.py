from __future__ import annotations

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
import requests


def test_load_config_raises_on_missing_env(monkeypatch: pytest.MonkeyPatch) -> None:
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

    from ingestion.config import load_config

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

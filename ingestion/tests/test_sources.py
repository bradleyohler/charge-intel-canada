from __future__ import annotations

import pytest
import pandas as pd
from unittest.mock import patch, MagicMock


def test_load_config_raises_on_missing_env(monkeypatch: pytest.MonkeyPatch) -> None:
    env_vars = [
        "AFDC_API_KEY",
        "SNOWFLAKE_ACCOUNT",
        "SNOWFLAKE_USER",
        "SNOWFLAKE_PASSWORD",
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


def test_fetch_afdc_returns_dataframe(monkeypatch: pytest.MonkeyPatch) -> None:
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "fuel_stations": [
            {
                "id": "123",
                "station_name": "Test Station",
                "street_address": "123 Main St",
                "city": "Toronto",
                "state": "ON",
                "zip": "M5H 2N2",
                "latitude": 43.65107,
                "longitude": -79.347015,
                "status_code": "E",
                "ev_level1_evse_num": 0,
                "ev_level2_evse_num": 4,
                "ev_dc_fast_num": 2,
                "ev_connector_types": ["J1772", "CCS"],
                "ev_network": "ChargePoint",
                "ev_network_web": "https://chargepoint.com",
                "ev_pricing": None,
                "ev_pricing_fr": None,
                "open_date": "2022-01-15",
                "ev_workplace_charging": False,
                "updated_at": "2024-01-01T00:00:00Z",
            }
        ]
    }
    mock_response.raise_for_status = MagicMock()

    with patch("requests.get", return_value=mock_response):
        from ingestion.sources.afdc import fetch_afdc_stations

        df = fetch_afdc_stations("test-api-key")

    assert isinstance(df, pd.DataFrame)
    assert len(df) == 1
    required_cols = [
        "station_id",
        "latitude",
        "longitude",
        "province_code",
        "station_name",
    ]
    for col in required_cols:
        assert col in df.columns, f"Missing column: {col}"


def test_fetch_afdc_skips_records_missing_critical_fields() -> None:
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "fuel_stations": [
            {
                "id": "1",
                "station_name": "Good",
                "state": "ON",
                "latitude": 43.0,
                "longitude": -79.0,
            },
            {
                "id": "2",
                "station_name": "No lat",
                "state": "ON",
                "latitude": None,
                "longitude": -79.0,
            },
            {
                "id": "3",
                "station_name": "No prov",
                "latitude": 43.0,
                "longitude": -79.0,
                "state": None,
            },
        ]
    }
    mock_response.raise_for_status = MagicMock()

    with patch("requests.get", return_value=mock_response):
        from ingestion.sources.afdc import fetch_afdc_stations

        df = fetch_afdc_stations("test-key")

    assert len(df) == 1

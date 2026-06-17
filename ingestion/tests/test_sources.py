from __future__ import annotations

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest


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

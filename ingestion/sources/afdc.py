from __future__ import annotations

import json
import logging
from io import StringIO
from pathlib import Path

import pandas as pd
import requests

from ingestion import IngestionError
from ingestion.config import load_config
from ingestion.loader import write_to_bronze

logger = logging.getLogger(__name__)

BASE_URL = "https://developer.nlr.gov/api/alt-fuel-stations/v1"
NETWORKS_URL = f"{BASE_URL}/electric-networks"
CHARGING_UNITS_URL = f"{BASE_URL}/ev-charging-units"

_CACHE_DIR = Path(__file__).parent.parent.parent / ".cache"
_HEADERS = {"User-Agent": "curl/7.88"}


def _cache_path(name: str) -> Path:
    _CACHE_DIR.mkdir(exist_ok=True)
    return _CACHE_DIR / name


def fetch_ev_networks(api_key: str, *, use_cache: bool = False) -> pd.DataFrame:
    """Fetch full list of EV charging networks (reference data)."""
    cache_file = _cache_path("afdc_networks.json")

    if use_cache and cache_file.exists():
        logger.info("Loading EV networks from cache: %s", cache_file)
        data = json.loads(cache_file.read_text())
    else:
        try:
            response = requests.get(
                NETWORKS_URL, params={"api_key": api_key}, headers=_HEADERS, timeout=60
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise IngestionError(f"AFDC networks request failed: {exc}") from exc
        data = response.json()
        cache_file.write_text(json.dumps(data))
        logger.info("Cached EV networks response to %s", cache_file)

    if isinstance(data, list):
        networks = data
    else:
        networks = data.get("ev_charging_networks", data.get("networks", [data]))

    df = pd.DataFrame(networks)
    logger.info("Fetched %d EV networks from AFDC", len(df))
    return df


def fetch_ev_charging_units(api_key: str) -> pd.DataFrame:
    """Fetch port-level EV charging unit data for Canada as CSV."""
    params = {
        "api_key": api_key,
        "country": "CA",
        "status": "E,T,P",
    }
    try:
        response = requests.get(
            CHARGING_UNITS_URL, params=params, headers=_HEADERS, timeout=120
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise IngestionError(f"AFDC charging units request failed: {exc}") from exc

    # Endpoint returns CSV
    try:
        df = pd.read_csv(StringIO(response.text))
    except Exception as exc:
        raise IngestionError(f"Failed to parse AFDC charging units CSV: {exc}") from exc

    logger.info("Fetched %d charging unit rows from AFDC", len(df))

    # Normalise column names to snake_case and drop rows missing critical fields
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    # Identify lat/lon/province columns flexibly (names may vary by API version)
    lat_col = next((c for c in df.columns if "latitude" in c or c == "lat"), None)
    lon_col = next((c for c in df.columns if "longitude" in c or c == "lon"), None)
    prov_col = next(
        (c for c in df.columns if c in ("state", "province", "province_code")), None
    )

    before = len(df)
    if lat_col and lon_col:
        df = df.dropna(subset=[lat_col, lon_col])
    if prov_col:
        df = df[df[prov_col].notna()]

    dropped = before - len(df)
    if dropped:
        logger.warning(
            "Dropped %d charging unit rows with missing lat/lon/province", dropped
        )

    logger.info("Returning %d charging unit rows after quality filter", len(df))
    return df


if __name__ == "__main__":
    import sys
    import traceback

    logging.basicConfig(level=logging.INFO, stream=sys.stdout)

    try:
        config = load_config()

        logger.info("Fetching EV charging networks...")
        networks_df = fetch_ev_networks(config.afdc_api_key, use_cache=True)
        logger.info("Networks DataFrame shape: %s", networks_df.shape)
        if not networks_df.empty:
            write_to_bronze(
                networks_df, "AFDC_NETWORKS_RAW", "afdc", config, overwrite=True
            )
        else:
            logger.warning("Networks DataFrame was empty – nothing written")

        logger.info("Fetching EV charging units (port-level)...")
        units_df = fetch_ev_charging_units(config.afdc_api_key)
        logger.info("Charging units DataFrame shape: %s", units_df.shape)
        if not units_df.empty:
            write_to_bronze(
                units_df, "AFDC_CHARGING_UNITS_RAW", "afdc", config, overwrite=True
            )
        else:
            logger.warning("Charging units DataFrame was empty – nothing written")

    except Exception:
        traceback.print_exc(file=sys.stdout)
        sys.exit(1)

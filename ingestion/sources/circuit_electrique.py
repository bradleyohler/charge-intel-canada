from __future__ import annotations

import logging
from io import StringIO

import pandas as pd
import requests

from ingestion import IngestionError

logger = logging.getLogger(__name__)

CE_CSV_URL = "https://data.lecircuitelectrique.com/stations/export_sites_fr.csv"

_HEADERS = {"User-Agent": "curl/7.88"}


def fetch_circuit_electrique() -> pd.DataFrame:
    try:
        response = requests.get(CE_CSV_URL, headers=_HEADERS, timeout=60)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise IngestionError(f"Circuit Électrique download failed: {exc}") from exc

    raw = pd.read_csv(StringIO(response.text))
    logger.info("Fetched %d rows from Circuit Électrique", len(raw))

    # Normalise to the shared schema where possible.
    # Column names vary by export; map best-effort.
    df = pd.DataFrame()
    df["latitude"] = pd.to_numeric(
        raw.get("latitude", raw.get("Latitude")), errors="coerce"
    )
    df["longitude"] = pd.to_numeric(
        raw.get("longitude", raw.get("Longitude")), errors="coerce"
    )
    df["station_name"] = raw.get("nom_site", raw.get("name", ""))
    df["street_address"] = raw.get("adresse", raw.get("address", ""))
    df["city"] = raw.get("ville", raw.get("city", ""))
    df["province_code"] = "QC"  # Circuit Électrique is Quebec-only
    df["postal_code"] = raw.get("code_postal", raw.get("postal_code", ""))
    df["network_name"] = "Circuit Électrique"
    df["status_code"] = "E"

    before = len(df)
    df = df.dropna(subset=["latitude", "longitude"])
    dropped = before - len(df)
    if dropped:
        logger.warning("Dropped %d CE records with missing lat/lon", dropped)

    logger.info("Returning %d Circuit Électrique rows", len(df))
    return df


if __name__ == "__main__":
    import sys
    import traceback

    logging.basicConfig(level=logging.INFO, stream=sys.stdout)

    try:
        from ingestion.config import load_config
        from ingestion.loader import write_to_bronze

        config = load_config()
        df = fetch_circuit_electrique()
        write_to_bronze(
            df, "CIRCUIT_ELECTRIQUE_RAW", "circuit_electrique", config, overwrite=True
        )
    except Exception:
        traceback.print_exc(file=sys.stdout)
        sys.exit(1)

from __future__ import annotations

import hashlib
import logging
from io import StringIO

import pandas as pd
import requests

from ingestion import IngestionError

logger = logging.getLogger(__name__)

CE_CSV_URL = "https://data.lecircuitelectrique.com/stations/export_sites_fr.csv"

_HEADERS = {"User-Agent": "curl/7.88"}

# Output column order
_OUTPUT_COLUMNS = [
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


def _charging_level(level: str) -> str:
    """Classify a charging level string into 'l1', 'l2', or 'dcfc'."""
    normalized = str(level).strip().lower()
    if normalized.startswith("niveau 1"):
        return "l1"
    if normalized.startswith("niveau 2"):
        return "l2"
    return "dcfc"


def _station_id(lat: float, lon: float) -> str:
    """Return the MD5 hex digest of 'lat|lon' as the station identifier."""
    key = f"{lat}|{lon}".encode("utf-8")
    return hashlib.md5(key).hexdigest()


def fetch_circuit_electrique() -> pd.DataFrame:
    """Download the Circuit Électrique CSV and return a station-level DataFrame."""
    try:
        response = requests.get(CE_CSV_URL, headers=_HEADERS, timeout=60)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise IngestionError(f"Circuit Électrique download failed: {exc}") from exc

    raw = pd.read_csv(StringIO(response.text), sep=",")
    logger.info("Fetched %d port rows from Circuit Électrique", len(raw))

    # Work on an explicit copy to avoid chained-assignment warnings
    raw = raw.copy()

    # Coerce coordinates to numeric; rows with bad values become NaN
    raw.loc[:, "Latitude"] = pd.to_numeric(raw["Latitude"], errors="coerce")
    raw.loc[:, "Longitude"] = pd.to_numeric(raw["Longitude"], errors="coerce")

    # Classify each port into l1 / l2 / dcfc
    niveau_col = "Niveau de recharge"
    raw.loc[:, "_level"] = raw[niveau_col].fillna("").apply(_charging_level)

    # Aggregate port rows → station rows grouped by (Latitude, Longitude).
    # include_groups=False excludes the groupby keys from grp so _agg only sees
    # the payload columns; the keys are re-attached via reset_index().
    def _agg(grp: pd.DataFrame) -> pd.Series:
        return pd.Series(
            {
                "station_name": grp["Nom du parc"].iloc[0],
                "street_address": grp["Rue"].iloc[0],
                "city": grp["Ville"].iloc[0],
                "postal_code": grp["Code Postal"].iloc[0],
                "l1_port_count": int((grp["_level"] == "l1").sum()),
                "l2_port_count": int((grp["_level"] == "l2").sum()),
                "dcfc_port_count": int((grp["_level"] == "dcfc").sum()),
            }
        )

    grouped = (
        raw.groupby(["Latitude", "Longitude"], dropna=False)
        .apply(_agg, include_groups=False)
        .reset_index()
    )

    grouped.rename(
        columns={"Latitude": "latitude", "Longitude": "longitude"}, inplace=True
    )

    # Drop stations without valid coordinates
    before = len(grouped)
    grouped = grouped.dropna(subset=["latitude", "longitude"])
    dropped = before - len(grouped)
    if dropped:
        logger.warning("Dropped %d CE stations with missing lat/lon", dropped)

    # Add constant columns
    grouped["province_code"] = "QC"
    grouped["network_name"] = "Circuit Électrique"
    grouped["status_code"] = "E"

    # Derive station_id from coordinates
    grouped["station_id"] = grouped.apply(
        lambda row: _station_id(row["latitude"], row["longitude"]), axis=1
    )

    logger.info("Returning %d Circuit Électrique stations", len(grouped))
    return grouped[_OUTPUT_COLUMNS]


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

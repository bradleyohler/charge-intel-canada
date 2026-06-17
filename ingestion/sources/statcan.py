from __future__ import annotations

import logging
from io import BytesIO

import pandas as pd
import requests

from ingestion import IngestionError

logger = logging.getLogger(__name__)

STATCAN_URL = (
    "https://www12.statcan.gc.ca/census-recensement/2021/dp-pd/prof/details/"
    "download-telecharger/comp/GetFile.cfm?Lang=E&FILETYPE=CSV&GEONO=044"
)


def fetch_statcan_population() -> pd.DataFrame:
    try:
        response = requests.get(STATCAN_URL, timeout=120)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise IngestionError(f"StatCan download failed: {exc}") from exc

    try:
        raw = pd.read_csv(BytesIO(response.content), encoding="latin-1")
    except Exception as exc:
        raise IngestionError(f"StatCan CSV parse failed: {exc}") from exc

    logger.info("StatCan raw shape: %s", raw.shape)
    # Stub: return expected schema with available data
    df = pd.DataFrame(columns=["fsa", "province_code", "population", "area_sq_km"])
    logger.warning(
        "StatCan column mapping not yet implemented – returning empty DataFrame"
        " with correct schema"
    )
    return df

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

_FSA_FIRST_CHAR_MAP: dict[str, str] = {
    "A": "NL",
    "B": "NS",
    "C": "PE",
    "E": "NB",
    "G": "QC",
    "H": "QC",
    "J": "QC",
    "K": "ON",
    "L": "ON",
    "M": "ON",
    "N": "ON",
    "P": "ON",
    "R": "MB",
    "S": "SK",
    "T": "AB",
    "V": "BC",
    "Y": "YT",
}


def _derive_province(fsa: str) -> str | None:
    if not fsa or len(fsa) < 1:
        return None
    first = fsa[0].upper()
    if first == "X":
        if fsa.upper().startswith("X0"):
            return "NU"
        if fsa.upper().startswith("X1"):
            return "NT"
        return None
    return _FSA_FIRST_CHAR_MAP.get(first)


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

    # Filter to FSA-level rows only
    fsa_rows = raw[raw["GEO_LEVEL"] == "Forward sortation area"].copy()
    fsa_rows["ALT_GEO_CODE"] = fsa_rows["ALT_GEO_CODE"].str.strip().str.upper()

    # Extract population rows
    pop_rows = fsa_rows[fsa_rows["CHARACTERISTIC_NAME"] == "Population, 2021"][
        ["ALT_GEO_CODE", "C1_COUNT_TOTAL"]
    ].rename(columns={"ALT_GEO_CODE": "fsa", "C1_COUNT_TOTAL": "population"})

    # Extract area rows
    area_rows = fsa_rows[
        fsa_rows["CHARACTERISTIC_NAME"] == "Land area in square kilometres"
    ][["ALT_GEO_CODE", "C1_COUNT_TOTAL"]].rename(
        columns={"ALT_GEO_CODE": "fsa", "C1_COUNT_TOTAL": "area_sq_km"}
    )

    # Merge into one row per FSA
    merged = pop_rows.merge(area_rows, on="fsa", how="outer").copy()

    # Coerce numeric types
    merged["population"] = pd.to_numeric(merged["population"], errors="coerce")
    merged["area_sq_km"] = pd.to_numeric(merged["area_sq_km"], errors="coerce")

    # Derive province_code
    merged["province_code"] = merged["fsa"].map(_derive_province)

    # Warn and drop rows with unknown province
    unknown_province = merged[merged["province_code"].isna() & merged["fsa"].notna()]
    for _, row in unknown_province.iterrows():
        logger.warning("Dropping FSA %r – could not derive province_code", row["fsa"])

    merged = merged[merged["province_code"].notna()]

    # Warn and drop rows missing fsa or population
    missing_fsa = merged[merged["fsa"].isna()]
    for _, row in missing_fsa.iterrows():
        logger.warning("Dropping row with null fsa: %r", row.to_dict())
    merged = merged[merged["fsa"].notna()]

    missing_pop = merged[merged["population"].isna()]
    for _, row in missing_pop.iterrows():
        logger.warning("Dropping FSA %r – population is null", row["fsa"])
    merged = merged[merged["population"].notna()]

    # Final column order and types
    df = merged[["fsa", "province_code", "population", "area_sq_km"]].copy()
    df["population"] = df["population"].astype(int)

    if df.empty:
        raise IngestionError("StatCan ingestion produced no records")

    logger.info("Returning %d StatCan FSA population rows", len(df))
    return df


if __name__ == "__main__":
    import sys
    import traceback

    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    try:
        from ingestion.config import load_config
        from ingestion.loader import write_to_bronze

        config = load_config()
        df = fetch_statcan_population()
        write_to_bronze(df, "STATCAN_POPULATION_RAW", "statcan", config, overwrite=True)
    except Exception:
        traceback.print_exc(file=sys.stdout)
        sys.exit(1)

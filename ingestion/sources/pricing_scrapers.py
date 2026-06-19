from __future__ import annotations

import logging
from dataclasses import asdict

import pandas as pd

from ingestion import IngestionError
from ingestion.sources.scrapers.base import NetworkPricingScraper
from ingestion.sources.scrapers.bc_hydro_ev import BCHydroEVScraper
from ingestion.sources.scrapers.chargepoint_ca import ChargePointCAScraper
from ingestion.sources.scrapers.electrify_canada import ElectrifyCanadaScraper
from ingestion.sources.scrapers.flo import FloScraper
from ingestion.sources.scrapers.ivy import IVYScraper
from ingestion.sources.scrapers.petro_canada import PetroCanadaScraper
from ingestion.sources.scrapers.tesla import TeslaScraper

logger = logging.getLogger(__name__)

SCRAPER_CLASSES: list[type[NetworkPricingScraper]] = [
    FloScraper,
    ChargePointCAScraper,
    ElectrifyCanadaScraper,
    BCHydroEVScraper,
    TeslaScraper,
    PetroCanadaScraper,
    IVYScraper,
]


def collect_pricing_records() -> pd.DataFrame:
    """Run every network pricing scraper and flatten the results into a DataFrame.

    Each scraper is run in isolation – per Decision Rule 5 in SCOPE.md, one
    network's scraper crashing must never take down the others. Failures are
    logged at ERROR and that network is simply excluded from the result.

    Raises
    ------
    IngestionError
        If zero records were collected across all networks.
    """
    records: list[dict[str, object]] = []

    for scraper_cls in SCRAPER_CLASSES:
        scraper = scraper_cls()
        try:
            network_records = scraper.scrape()
        except Exception:
            logger.exception(
                "%s scraper failed – skipping this network", scraper.network_name
            )
            continue

        if not network_records:
            logger.warning("%s scraper returned no records", scraper.network_name)
            continue

        records.extend(asdict(record) for record in network_records)
        logger.info(
            "%s scraper returned %d records", scraper.network_name, len(network_records)
        )

    if not records:
        raise IngestionError(
            "Pricing scraper ingestion produced no records – all networks failed"
        )

    # Build column-by-column with dtype=object for the DataFrame construction.
    # Letting pandas infer dtypes from a list of dicts containing tz-aware
    # datetime.datetime values can crash under some pandas/Python combinations
    # (observed segfault during datetime64 inference) – constructing columns
    # explicitly as plain Python objects avoids that inference path entirely.
    columns = sorted({key for record in records for key in record})
    data = {
        col: pd.Series([record.get(col) for record in records], dtype=object)
        for col in columns
    }
    df = pd.DataFrame(data)
    logger.info("Returning %d pricing records across all networks", len(df))
    return df


if __name__ == "__main__":
    import sys
    import traceback

    logging.basicConfig(level=logging.INFO, stream=sys.stdout)

    try:
        from ingestion.config import load_config
        from ingestion.loader import write_to_bronze

        config = load_config()
        df = collect_pricing_records()
        write_to_bronze(
            df, "PRICING_SCRAPE_RAW", "pricing_scrapers", config, overwrite=False
        )
    except Exception:
        traceback.print_exc(file=sys.stdout)
        sys.exit(1)

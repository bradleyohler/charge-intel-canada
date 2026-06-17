from __future__ import annotations

import logging

import pandas as pd

logger = logging.getLogger(__name__)


def fetch_cer_rates() -> pd.DataFrame:
    logger.warning(
        "CER rates ingestion is not yet implemented – returning empty DataFrame"
    )
    return pd.DataFrame(
        columns=[
            "province_code",
            "rate_type",
            "period",
            "rate_value",
            "rate_unit",
            "effective_date",
        ]
    )

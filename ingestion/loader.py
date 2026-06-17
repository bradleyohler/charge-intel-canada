from __future__ import annotations

import logging
from datetime import datetime, UTC
from pathlib import Path

import pandas as pd
import snowflake.connector
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    load_pem_private_key,
)

from ingestion.config import Config

logger = logging.getLogger(__name__)

_SNOWFLAKE_TYPE_MAP = {
    "object": "TEXT",
    "float64": "FLOAT",
    "float32": "FLOAT",
    "int64": "NUMBER",
    "int32": "NUMBER",
    "bool": "BOOLEAN",
    "datetime64[ns]": "TIMESTAMP_NTZ",
}


def _sf_type(dtype) -> str:
    return _SNOWFLAKE_TYPE_MAP.get(str(dtype), "TEXT")


def _load_private_key(path: str) -> bytes:
    key_bytes = Path(path).read_bytes()
    private_key = load_pem_private_key(key_bytes, password=None)
    return private_key.private_bytes(
        encoding=Encoding.DER,
        format=PrivateFormat.PKCS8,
        encryption_algorithm=NoEncryption(),
    )


_INSERT_BATCH = 500  # rows per multi-row INSERT statement


def get_snowflake_connection(
    config: Config,
    login_timeout: int = 60,
) -> snowflake.connector.SnowflakeConnection:
    return snowflake.connector.connect(
        account=config.snowflake_account,
        user=config.snowflake_user,
        private_key=_load_private_key(config.snowflake_private_key_path),
        warehouse=config.snowflake_warehouse,
        database=config.snowflake_database,
        role=config.snowflake_role,
        schema="BRONZE",
        login_timeout=login_timeout,
        network_timeout=600,  # 10 min – long enough for large batched inserts
    )


def _clean_val(v):
    """Convert NaN / numpy scalars to plain Python values the Snowflake driver accepts."""
    import math

    if v is None:
        return None
    try:
        if math.isnan(v):
            return None
    except TypeError:
        pass
    # Unwrap numpy scalars to plain Python primitives
    if hasattr(v, "item"):
        return v.item()
    return v


def write_to_bronze(
    df: pd.DataFrame,
    table_name: str,
    source: str,
    config: Config,
    *,
    overwrite: bool = True,
) -> None:
    tbl = table_name.upper()
    ingested_at = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")
    data_cols = list(df.columns)

    # DDL – read dtypes from the original df; never mutate it
    col_defs = ", ".join(
        [f'"{c.upper()}" {_sf_type(df[c].dtype)}' for c in data_cols]
        + ['"_INGESTED_AT" TEXT', '"_SOURCE" TEXT']
    )
    if overwrite:
        ddl = f'CREATE OR REPLACE TABLE BRONZE."{tbl}" ({col_defs})'
    else:
        ddl = f'CREATE TABLE IF NOT EXISTS BRONZE."{tbl}" ({col_defs})'

    placeholders = ", ".join(["%s"] * (len(data_cols) + 2))
    dml = f'INSERT INTO BRONZE."{tbl}" VALUES ({placeholders})'

    # Build row tuples without mutating the DataFrame
    rows = [
        tuple(_clean_val(v) for v in row) + (ingested_at, source)
        for row in df.itertuples(index=False, name=None)
    ]

    logger.info("Rows prepared (%d); connecting to Snowflake…", len(rows))
    conn = get_snowflake_connection(config, login_timeout=30)
    try:
        cur = conn.cursor()
        logger.info("DDL: %s", ddl[:200])
        cur.execute(ddl)

        # Multi-row INSERT batches – far faster than executemany for large sets
        n_cols = len(data_cols) + 2  # +2 for _ingested_at, _source
        row_ph = f"({', '.join(['%s'] * n_cols)})"
        total = len(rows)
        inserted = 0
        for start in range(0, total, _INSERT_BATCH):
            batch = rows[start : start + _INSERT_BATCH]
            values_clause = ", ".join([row_ph] * len(batch))
            flat_params = [v for row in batch for v in row]
            cur.execute(
                f'INSERT INTO BRONZE."{tbl}" VALUES {values_clause}',
                flat_params,
            )
            inserted += len(batch)
            logger.info("  inserted %d / %d rows…", inserted, total)

        conn.commit()
        logger.info("Wrote %d rows to BRONZE.%s", total, tbl)
    finally:
        conn.close()

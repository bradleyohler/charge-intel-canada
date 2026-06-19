from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import snowflake.connector
import streamlit as st
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    load_pem_private_key,
)
from dotenv import load_dotenv

load_dotenv()


def _load_private_key(path: str) -> bytes:
    key_bytes = Path(path).read_bytes()
    private_key = load_pem_private_key(key_bytes, password=None)
    return private_key.private_bytes(
        encoding=Encoding.DER,
        format=PrivateFormat.PKCS8,
        encryption_algorithm=NoEncryption(),
    )


@st.cache_resource
def get_connection() -> snowflake.connector.SnowflakeConnection:
    return snowflake.connector.connect(
        account=os.environ["SNOWFLAKE_ACCOUNT"],
        user=os.environ["SNOWFLAKE_USER"],
        private_key=_load_private_key(os.environ["SNOWFLAKE_PRIVATE_KEY_PATH"]),
        warehouse=os.environ.get("SNOWFLAKE_WAREHOUSE", "CHARGE_INTEL_WH"),
        database=os.environ.get("SNOWFLAKE_DATABASE", "CHARGE_INTEL_CANADA"),
        role=os.environ.get("SNOWFLAKE_ROLE", "CHARGE_INTEL_ROLE"),
    )


@st.cache_data(ttl=3600)
def run_query(sql: str) -> pd.DataFrame:
    conn = get_connection()
    return pd.read_sql(sql, conn)

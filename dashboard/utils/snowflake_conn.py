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


def _get_setting(key: str, default: str | None = None) -> str | None:
    # Streamlit only mirrors secrets.toml into os.environ once st.secrets has
    # been accessed, so check st.secrets explicitly rather than relying on that.
    if key in st.secrets:
        return str(st.secrets[key])
    return os.environ.get(key, default)


def _load_private_key(key_pem: str | None, key_path: str | None) -> bytes:
    if key_pem:
        key_bytes = key_pem.encode("utf-8")
    elif key_path:
        key_bytes = Path(key_path).read_bytes()
    else:
        raise EnvironmentError(
            "Set either SNOWFLAKE_PRIVATE_KEY (PEM contents) or "
            "SNOWFLAKE_PRIVATE_KEY_PATH (path to a .p8 file)."
        )
    private_key = load_pem_private_key(key_bytes, password=None)
    return private_key.private_bytes(
        encoding=Encoding.DER,
        format=PrivateFormat.PKCS8,
        encryption_algorithm=NoEncryption(),
    )


@st.cache_resource
def get_connection() -> snowflake.connector.SnowflakeConnection:
    return snowflake.connector.connect(
        account=_get_setting("SNOWFLAKE_ACCOUNT"),
        user=_get_setting("SNOWFLAKE_USER"),
        private_key=_load_private_key(
            _get_setting("SNOWFLAKE_PRIVATE_KEY"),
            _get_setting("SNOWFLAKE_PRIVATE_KEY_PATH"),
        ),
        warehouse=_get_setting("SNOWFLAKE_WAREHOUSE", "CHARGE_INTEL_WH"),
        database=_get_setting("SNOWFLAKE_DATABASE", "CHARGE_INTEL_CANADA"),
        role=_get_setting("SNOWFLAKE_ROLE", "CHARGE_INTEL_ROLE"),
    )


@st.cache_data(ttl=3600)
def run_query(sql: str) -> pd.DataFrame:
    conn = get_connection()
    return pd.read_sql(sql, conn)

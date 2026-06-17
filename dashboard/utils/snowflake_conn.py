from __future__ import annotations

import os
import pandas as pd
import snowflake.connector
import streamlit as st
from dotenv import load_dotenv

load_dotenv()


@st.cache_resource
def get_connection() -> snowflake.connector.SnowflakeConnection:
    return snowflake.connector.connect(
        account=os.environ["SNOWFLAKE_ACCOUNT"],
        user=os.environ["SNOWFLAKE_USER"],
        password=os.environ["SNOWFLAKE_PASSWORD"],
        warehouse=os.environ.get("SNOWFLAKE_WAREHOUSE", "CHARGE_INTEL_WH"),
        database=os.environ.get("SNOWFLAKE_DATABASE", "CHARGE_INTEL_CANADA"),
        role=os.environ.get("SNOWFLAKE_ROLE", "CHARGE_INTEL_ROLE"),
    )


@st.cache_data(ttl=3600)
def run_query(sql: str) -> pd.DataFrame:
    conn = get_connection()
    return pd.read_sql(sql, conn)

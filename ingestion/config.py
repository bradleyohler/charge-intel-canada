from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Config:
    afdc_api_key: str
    snowflake_account: str
    snowflake_user: str
    snowflake_private_key_path: str
    snowflake_warehouse: str
    snowflake_database: str
    snowflake_role: str


def load_config() -> Config:
    required = [
        "AFDC_API_KEY",
        "SNOWFLAKE_ACCOUNT",
        "SNOWFLAKE_USER",
        "SNOWFLAKE_PRIVATE_KEY_PATH",
        "SNOWFLAKE_WAREHOUSE",
        "SNOWFLAKE_DATABASE",
        "SNOWFLAKE_ROLE",
    ]
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        raise EnvironmentError(f"Missing required environment variables: {missing}")
    return Config(
        afdc_api_key=os.environ["AFDC_API_KEY"],
        snowflake_account=os.environ["SNOWFLAKE_ACCOUNT"],
        snowflake_user=os.environ["SNOWFLAKE_USER"],
        snowflake_private_key_path=os.environ["SNOWFLAKE_PRIVATE_KEY_PATH"],
        snowflake_warehouse=os.environ["SNOWFLAKE_WAREHOUSE"],
        snowflake_database=os.environ["SNOWFLAKE_DATABASE"],
        snowflake_role=os.environ["SNOWFLAKE_ROLE"],
    )

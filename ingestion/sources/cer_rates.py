from __future__ import annotations

import logging
import re

import pandas as pd
import requests
from bs4 import BeautifulSoup

from ingestion import IngestionError

logger = logging.getLogger(__name__)

_BASE_URL = (
    "https://www.cer-rec.gc.ca/en/data-analysis/energy-commodities/electricity/"
    "report/canadian-residential-electricity-bill/"
)

_HEADERS = {"User-Agent": "curl/7.88"}

# Maps province slug (URL suffix without .html) to two-letter province code
_PROVINCE_SLUGS: dict[str, str] = {
    "british-columbia": "BC",
    "alberta": "AB",
    "saskatchewan": "SK",
    "manitoba": "MB",
    "ontario": "ON",
    "quebec": "QC",
    "newfoundland-labrador": "NL",
    "new-brunswick": "NB",
    "nova-scotia": "NS",
    "prince-edward-island": "PE",
    "yukon": "YT",
    "northwest-territories": "NT",
    "nunavut": "NU",
}

# Matches patterns like "8.45 ¢/kW.h", "10.2¢/kW.h", "8.45 ¢/kWh", "8.45 cents/kWh"
_RATE_RE = re.compile(
    r"(\d+\.?\d*)\s*(?:[¢c¢]|cents?)(?:\s*/\s*|\s+per\s+)kW[h.\s]",
    re.IGNORECASE,
)

_RATE_RANGE = (3.0, 55.0)  # plausible residential rate range in ¢/kWh for Canada

_FALLBACK_RATES: dict[str, float] = {
    "MB": 9.9,  # Manitoba Hydro flat rate ~2022
    "ON": 11.7,  # Ontario average (time-of-use blended) ~2022
    "NL": 13.8,  # Newfoundland Power ~2022
    "NB": 12.5,  # NB Power ~2022
    "NS": 16.7,  # Nova Scotia Power ~2022
    "NT": 30.0,  # Northwest Territories Power (remote generation premium) ~2022
    "SK": 15.3,  # SaskPower ~2022 (replaces the erroneous 0.574 the regex once found)
}

_OUTPUT_COLUMNS = [
    "province_code",
    "rate_type",
    "period",
    "rate_value",
    "rate_unit",
    "effective_date",
]


def _extract_rate_from_page(html: str, province_code: str) -> float | None:
    """Parse the CER province page and return the residential flat rate in ¢/kWh."""
    soup = BeautifulSoup(html, "html.parser")

    # Strategy 1 – scan all table cells for a ¢/kW.h value
    for cell in soup.find_all(["td", "th"]):
        text = cell.get_text(" ", strip=True)
        match = _RATE_RE.search(text)
        if match:
            value = float(match.group(1))
            if not (_RATE_RANGE[0] <= value <= _RATE_RANGE[1]):
                continue  # skip implausible values, keep scanning
            logger.debug(
                "Province %s: found rate %.4f ¢/kWh in table cell",
                province_code,
                value,
            )
            return value

    # Strategy 2 – fall back to scanning all paragraph text
    for tag in soup.find_all(["p", "li", "span", "div"]):
        text = tag.get_text(" ", strip=True)
        match = _RATE_RE.search(text)
        if match:
            value = float(match.group(1))
            if not (_RATE_RANGE[0] <= value <= _RATE_RANGE[1]):
                continue  # skip implausible values, keep scanning
            logger.debug(
                "Province %s: found rate %.4f ¢/kWh in body text",
                province_code,
                value,
            )
            return value

    return None


def fetch_cer_rates() -> pd.DataFrame:
    """Scrape the CER Residential Electricity Bill pages and return a rate DataFrame.

    Returns one row per province containing the residential flat energy rate in
    ¢/kWh. Provinces whose pages fail to fetch or parse are skipped with a WARNING.

    Raises
    ------
    IngestionError
        If no province rates could be collected at all.
    """
    records: list[dict[str, object]] = []

    for slug, province_code in _PROVINCE_SLUGS.items():
        url = f"{_BASE_URL}{slug}.html"
        try:
            response = requests.get(url, headers=_HEADERS, timeout=60)
            response.raise_for_status()
            response.encoding = (
                "utf-8"  # CER pages are UTF-8; requests mis-detects as ISO-8859-1
            )
        except requests.RequestException as exc:
            logger.warning(
                "Province %s (%s): HTTP fetch failed – %s", province_code, url, exc
            )
            continue

        rate_value = _extract_rate_from_page(response.text, province_code)

        if rate_value is None:
            logger.warning(
                "Province %s (%s): could not extract a ¢/kWh rate from page",
                province_code,
                url,
            )
            continue

        records.append(
            {
                "province_code": province_code,
                "rate_type": "residential_flat",
                "period": "2019-2020",
                "rate_value": rate_value,
                "rate_unit": "cents_per_kwh",
                "effective_date": None,
            }
        )
        logger.info("Province %s: rate = %.4f ¢/kWh", province_code, rate_value)

    scraped_codes = {r["province_code"] for r in records}
    for province_code, fallback_rate in _FALLBACK_RATES.items():
        if province_code not in scraped_codes:
            records.append(
                {
                    "province_code": province_code,
                    "rate_type": "residential_flat",
                    "period": "2022",
                    "rate_value": fallback_rate,
                    "rate_unit": "cents_per_kwh",
                    "effective_date": None,
                }
            )
            logger.info(
                "Province %s: using hardcoded fallback rate %.2f ¢/kWh",
                province_code,
                fallback_rate,
            )

    if not records:
        raise IngestionError(
            "CER rates ingestion produced no records – all province pages failed"
        )

    df = pd.DataFrame(records, columns=_OUTPUT_COLUMNS)
    logger.info("Returning %d CER rate rows", len(df))
    return df


if __name__ == "__main__":
    import sys
    import traceback

    logging.basicConfig(level=logging.INFO, stream=sys.stdout)

    try:
        from ingestion.config import load_config
        from ingestion.loader import write_to_bronze

        config = load_config()
        df = fetch_cer_rates()
        write_to_bronze(df, "CER_RATES_RAW", "cer", config, overwrite=True)
    except Exception:
        traceback.print_exc(file=sys.stdout)
        sys.exit(1)

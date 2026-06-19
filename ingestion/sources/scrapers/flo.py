from __future__ import annotations

import logging
import re

import requests
from bs4 import BeautifulSoup

from ingestion.sources.scrapers.base import NetworkPricingScraper, PricingRecord

logger = logging.getLogger(__name__)

_PRICING_URL = "https://www.flo.com/drivers/pricing/"

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}

# Matches patterns like "$0.35/kWh", "$0.35 per kWh", "0.35 $/kWh"
_KWH_RATE_RE = re.compile(
    r"\$?\s*(\d+\.\d+)\s*(?:\$)?\s*(?:/|\bper\b)\s*kWh", re.IGNORECASE
)
# Matches patterns like "$1.50/hour", "$0.025/minute", "$1.50 per hour"
_MINUTE_RATE_RE = re.compile(
    r"\$?\s*(\d+\.\d+)\s*(?:/|\bper\b)\s*min(?:ute)?", re.IGNORECASE
)

_RATE_RANGE_KWH = (0.10, 1.00)  # plausible CAD/kWh range for DCFC pricing
_RATE_RANGE_MINUTE = (0.01, 0.20)  # plausible CAD/minute range for L2 pricing

# Hardcoded fallback pricing reflecting FLO's published 2024/2025 rate structure:
# DC fast charging billed per kWh (varies by province due to regulation), Level 2
# billed per minute/hour since FLO has not transitioned all L2 stations to kWh
# billing. Source: FLO public pricing page and aggregator sites (ChargeHub,
# electricautonomy.ca) as of research date.
_FALLBACK_DCFC_RATES: dict[str, float] = {
    "BC": 0.49,
    "AB": 0.45,
    "SK": 0.45,
    "MB": 0.43,
    "ON": 0.50,
    "QC": 0.35,  # Quebec DCFC pricing tends to be lower due to cheap hydro power
    "NB": 0.47,
    "NS": 0.47,
    "PE": 0.47,
    "NL": 0.49,
}
_FALLBACK_L2_RATE_PER_MINUTE = 0.02  # roughly $1.20/hour, in line with published L2

_OUTPUT_RATE_UNIT_KWH = "cad_per_kwh"
_OUTPUT_RATE_UNIT_MINUTE = "cad_per_minute"


def _extract_kwh_rate(text: str) -> float | None:
    match = _KWH_RATE_RE.search(text)
    if not match:
        return None
    value = float(match.group(1))
    if not (_RATE_RANGE_KWH[0] <= value <= _RATE_RANGE_KWH[1]):
        return None
    return value


def _extract_minute_rate(text: str) -> float | None:
    match = _MINUTE_RATE_RE.search(text)
    if not match:
        return None
    value = float(match.group(1))
    if not (_RATE_RANGE_MINUTE[0] <= value <= _RATE_RANGE_MINUTE[1]):
        return None
    return value


class FloScraper(NetworkPricingScraper):
    network_name = "FLO"

    def scrape(self) -> list[PricingRecord]:
        records: list[PricingRecord] = []

        try:
            response = requests.get(_PRICING_URL, headers=_HEADERS, timeout=30)
            response.raise_for_status()
            records = self._parse_pricing_page(response.text)
        except requests.RequestException as exc:
            logger.warning(
                "%s: HTTP fetch failed for %s – %s",
                self.network_name,
                _PRICING_URL,
                exc,
            )
        except Exception as exc:  # noqa: BLE001 - never let scrape() raise
            logger.warning(
                "%s: unexpected error parsing pricing page – %s",
                self.network_name,
                exc,
            )

        if not records:
            logger.info(
                "%s: live scrape produced no records, using fallback pricing",
                self.network_name,
            )
            records = self._fallback_records()

        return records

    def _parse_pricing_page(self, html: str) -> list[PricingRecord]:
        soup = BeautifulSoup(html, "html.parser")
        records: list[PricingRecord] = []

        for row in soup.find_all(["tr", "li", "p", "div"]):
            text = row.get_text(" ", strip=True)
            if not text:
                continue

            kwh_rate = _extract_kwh_rate(text)
            if kwh_rate is not None:
                records.append(
                    PricingRecord(
                        network_name=self.network_name,
                        province_code=None,
                        membership_tier="pay_as_you_go",
                        pricing_model="per_kwh",
                        rate_value=kwh_rate,
                        rate_unit=_OUTPUT_RATE_UNIT_KWH,
                        currency="CAD",
                    )
                )
                continue

            minute_rate = _extract_minute_rate(text)
            if minute_rate is not None:
                records.append(
                    PricingRecord(
                        network_name=self.network_name,
                        province_code=None,
                        membership_tier="pay_as_you_go",
                        pricing_model="per_minute",
                        rate_value=minute_rate,
                        rate_unit=_OUTPUT_RATE_UNIT_MINUTE,
                        currency="CAD",
                    )
                )

        return records

    def _fallback_records(self) -> list[PricingRecord]:
        records: list[PricingRecord] = []

        for province_code, rate in _FALLBACK_DCFC_RATES.items():
            records.append(
                PricingRecord(
                    network_name=self.network_name,
                    province_code=province_code,
                    membership_tier="pay_as_you_go",
                    pricing_model="per_kwh",
                    rate_value=rate,
                    rate_unit=_OUTPUT_RATE_UNIT_KWH,
                    currency="CAD",
                )
            )
            logger.info(
                "%s: using hardcoded fallback DCFC rate %.2f CAD/kWh for %s",
                self.network_name,
                rate,
                province_code,
            )

        # FLO Level 2 stations are still largely billed per-minute, nationally.
        records.append(
            PricingRecord(
                network_name=self.network_name,
                province_code=None,
                membership_tier="pay_as_you_go",
                pricing_model="per_minute",
                rate_value=_FALLBACK_L2_RATE_PER_MINUTE,
                rate_unit=_OUTPUT_RATE_UNIT_MINUTE,
                currency="CAD",
            )
        )
        logger.info(
            "%s: using hardcoded fallback L2 rate %.3f CAD/minute (national)",
            self.network_name,
            _FALLBACK_L2_RATE_PER_MINUTE,
        )

        return records


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    scraper = FloScraper()
    results = scraper.scrape()
    for rec in results:
        logger.info(rec)

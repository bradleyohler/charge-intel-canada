from __future__ import annotations

import logging
import re

import requests
from bs4 import BeautifulSoup

from ingestion.sources.scrapers.base import NetworkPricingScraper, PricingRecord

logger = logging.getLogger(__name__)

_PRICING_URL = "https://www.petro-canada.ca/en/personal/fuel/canadas-electric-highway"

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
}

# Matches patterns like "$0.50/min", "$0.50 / minute", "$0.50 per minute"
_RATE_RE = re.compile(r"\$\s*(\d+\.\d+)\s*(?:/|per)\s*min(?:ute)?", re.IGNORECASE)

_RATE_RANGE = (0.10, 1.00)  # plausible CAD/minute range for DCFC in Canada

# Hardcoded fallback rate – Petro-Canada's Electric Highway bills a flat
# CAD/minute rate for DC fast charging regardless of province, with no
# separate connection or idling fee (researched from public reporting on
# Petro-Canada's published per-minute pricing, 2025/2026).
_FALLBACK_RATE_PER_MINUTE = 0.50

_PROVINCE_CODES = [
    "BC",
    "AB",
    "SK",
    "MB",
    "ON",
    "QC",
    "NB",
    "NS",
    "PE",
    "NL",
]


class PetroCanadaScraper(NetworkPricingScraper):
    network_name = "Petro-Canada"

    def scrape(self) -> list[PricingRecord]:
        """Scrape Petro-Canada's Electric Highway DC fast charging pricing.

        Petro-Canada bills per-minute, nationally, with no provincial tiering
        and no membership tiers (pay-as-you-go). Attempts a live fetch first;
        falls back to a hardcoded but realistic flat per-minute rate.
        """
        scraped_rate = self._fetch_live_rate()
        rate_value = (
            scraped_rate if scraped_rate is not None else _FALLBACK_RATE_PER_MINUTE
        )

        records = [
            PricingRecord(
                network_name=self.network_name,
                province_code=province_code,
                membership_tier="pay_as_you_go",
                pricing_model="per_minute",
                rate_value=rate_value,
                rate_unit="cad_per_minute",
                currency="CAD",
            )
            for province_code in _PROVINCE_CODES
        ]

        logger.info(
            "%s scraper returning %d pricing records (%s)",
            self.network_name,
            len(records),
            "live" if scraped_rate is not None else "fallback",
        )
        return records

    def _fetch_live_rate(self) -> float | None:
        """Attempt to fetch and parse the per-minute CAD rate from Petro-Canada's
        public Electric Highway page. Returns None on any failure."""
        try:
            response = requests.get(_PRICING_URL, headers=_HEADERS, timeout=15)
            response.raise_for_status()
        except requests.RequestException as exc:
            logger.warning(
                "%s: HTTP fetch failed for %s – %s",
                self.network_name,
                _PRICING_URL,
                exc,
            )
            return None

        try:
            soup = BeautifulSoup(response.text, "html.parser")
            text = soup.get_text(" ", strip=True)
            match = _RATE_RE.search(text)
            if match is None:
                logger.warning(
                    "%s: could not parse a CAD/minute rate from page structure",
                    self.network_name,
                )
                return None
            value = float(match.group(1))
            if not (_RATE_RANGE[0] <= value <= _RATE_RANGE[1]):
                logger.warning(
                    "%s: parsed rate %.4f outside plausible range, discarding",
                    self.network_name,
                    value,
                )
                return None
            logger.info(
                "%s: parsed live rate %.4f CAD/minute", self.network_name, value
            )
            return value
        except Exception as exc:  # noqa: BLE001 - never let parsing crash scrape()
            logger.warning("%s: failed to parse page – %s", self.network_name, exc)
            return None

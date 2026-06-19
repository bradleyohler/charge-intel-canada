from __future__ import annotations

import logging
import re

import requests
from bs4 import BeautifulSoup

from ingestion.sources.scrapers.base import NetworkPricingScraper, PricingRecord

logger = logging.getLogger(__name__)

_PRICING_URL = "https://ivycharge.com/support/what-is-ivys-pricing-structure/"

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
}

# Matches patterns like "$0.69/kWh", "$0.69 / kWh", "$0.69 per kWh"
_RATE_RE = re.compile(r"\$\s*(\d+\.\d+)\s*(?:/|per)\s*kWh", re.IGNORECASE)

_RATE_RANGE = (0.10, 1.50)  # plausible CAD/kWh range for DCFC in Canada

# Hardcoded fallback rate – IVY Charging Network (Ontario) moved from
# per-minute to per-kWh DC fast charging pricing in its kWh-pricing rollout
# (researched from ivycharge.com support pages and driveteslacanada.ca
# reporting, mid-2025/2026). IVY operates exclusively in Ontario and offers
# pay-as-you-go pricing with no membership tiers for DCFC.
_FALLBACK_RATE_PER_KWH = 0.69

_PROVINCE_CODE = "ON"


class IVYScraper(NetworkPricingScraper):
    network_name = "IVY"

    def scrape(self) -> list[PricingRecord]:
        """Scrape IVY Charging Network's DC fast charging pricing.

        IVY operates only in Ontario and bills DCFC per-kWh, pay-as-you-go.
        Attempts a live fetch first; falls back to a hardcoded but realistic
        per-kWh rate if the live fetch fails or the page can't be parsed.
        """
        scraped_rate = self._fetch_live_rate()
        rate_value = (
            scraped_rate if scraped_rate is not None else _FALLBACK_RATE_PER_KWH
        )

        records = [
            PricingRecord(
                network_name=self.network_name,
                province_code=_PROVINCE_CODE,
                membership_tier="pay_as_you_go",
                pricing_model="per_kwh",
                rate_value=rate_value,
                rate_unit="cad_per_kwh",
                currency="CAD",
            )
        ]

        logger.info(
            "%s scraper returning %d pricing records (%s)",
            self.network_name,
            len(records),
            "live" if scraped_rate is not None else "fallback",
        )
        return records

    def _fetch_live_rate(self) -> float | None:
        """Attempt to fetch and parse the CAD/kWh rate from IVY's public
        pricing support page. Returns None on any failure."""
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
                    "%s: could not parse a CAD/kWh rate from page structure",
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
            logger.info("%s: parsed live rate %.4f CAD/kWh", self.network_name, value)
            return value
        except Exception as exc:  # noqa: BLE001 - never let parsing crash scrape()
            logger.warning("%s: failed to parse page – %s", self.network_name, exc)
            return None

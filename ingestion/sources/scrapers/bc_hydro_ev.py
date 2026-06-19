from __future__ import annotations

import logging
import re

import requests
from bs4 import BeautifulSoup

from ingestion.sources.scrapers.base import NetworkPricingScraper, PricingRecord

logger = logging.getLogger(__name__)

_RATES_URL = (
    "https://www.bchydro.com/powersmart/electric-vehicles/public-charging/"
    "charging-rates-roaming.html"
)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
}

_TIMEOUT_SECONDS = 15

# Matches patterns like "$0.28/kWh", "$0.28 per kWh", "28¢/kWh"
_DOLLAR_RATE_RE = re.compile(r"\$\s*(\d+\.\d+)\s*(?:/|per\s+)\s*kWh", re.IGNORECASE)
_CENTS_RATE_RE = re.compile(r"(\d+\.?\d*)\s*[¢c]\s*/\s*kWh", re.IGNORECASE)

_RATE_RANGE = (0.10, 1.00)  # plausible CAD/kWh range for DCFC pricing

# BC Hydro EV publishes a single flat DC fast-charging rate (no membership tiers).
# As of the 2025/2026 rate schedule the published rate is $0.28 CAD/kWh, with a
# BCUC-approved 5% increase scheduled for April 1, 2026.
_FALLBACK_RATE_CAD_PER_KWH = 0.28


def _extract_rate_from_page(html: str) -> float | None:
    """Parse the BC Hydro public charging rates page for the DCFC $/kWh rate."""
    soup = BeautifulSoup(html, "html.parser")

    # Strategy 1 - scan table cells for a dollar-denominated per-kWh rate
    for cell in soup.find_all(["td", "th"]):
        text = cell.get_text(" ", strip=True)
        match = _DOLLAR_RATE_RE.search(text)
        if match:
            value = float(match.group(1))
            if _RATE_RANGE[0] <= value <= _RATE_RANGE[1]:
                logger.debug("Found BC Hydro rate %.4f CAD/kWh in table cell", value)
                return value

    # Strategy 2 - scan general body text for dollar or cents rates
    for tag in soup.find_all(["p", "li", "span", "div"]):
        text = tag.get_text(" ", strip=True)
        match = _DOLLAR_RATE_RE.search(text)
        if match:
            value = float(match.group(1))
            if _RATE_RANGE[0] <= value <= _RATE_RANGE[1]:
                logger.debug("Found BC Hydro rate %.4f CAD/kWh in body text", value)
                return value
        match = _CENTS_RATE_RE.search(text)
        if match:
            value = float(match.group(1)) / 100.0
            if _RATE_RANGE[0] <= value <= _RATE_RANGE[1]:
                logger.debug(
                    "Found BC Hydro rate %.4f CAD/kWh (converted from cents)", value
                )
                return value

    return None


class BCHydroEVScraper(NetworkPricingScraper):
    network_name = "BC Hydro EV"

    def scrape(self) -> list[PricingRecord]:
        """Scrape the BC Hydro EV public DC fast-charging rate.

        BC Hydro EV publishes a single flat per-kWh rate for its public DC
        fast-charging network (no membership tiers). If the live page cannot
        be fetched or parsed, falls back to the most recently published
        rate. Never raises - on any failure, logs a warning and returns the
        fallback record.
        """
        rate_value: float | None = None

        try:
            response = requests.get(
                _RATES_URL, headers=_HEADERS, timeout=_TIMEOUT_SECONDS
            )
            response.raise_for_status()
            rate_value = _extract_rate_from_page(response.text)
            if rate_value is None:
                logger.warning(
                    "%s: could not extract a CAD/kWh rate from page %s",
                    self.network_name,
                    _RATES_URL,
                )
        except requests.RequestException as exc:
            logger.warning(
                "%s: HTTP fetch failed for %s - %s",
                self.network_name,
                _RATES_URL,
                exc,
            )

        if rate_value is None:
            rate_value = _FALLBACK_RATE_CAD_PER_KWH
            logger.info(
                "%s: using hardcoded fallback rate %.2f CAD/kWh",
                self.network_name,
                rate_value,
            )
        else:
            logger.info("%s: scraped rate %.2f CAD/kWh", self.network_name, rate_value)

        return [
            PricingRecord(
                network_name=self.network_name,
                province_code="BC",
                membership_tier="pay_as_you_go",
                pricing_model="per_kwh",
                rate_value=rate_value,
                rate_unit="cad_per_kwh",
                currency="CAD",
            )
        ]


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    for record in BCHydroEVScraper().scrape():
        logger.info(record)

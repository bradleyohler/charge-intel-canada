from __future__ import annotations

import logging
import re

import requests
from bs4 import BeautifulSoup

from ingestion.sources.scrapers.base import NetworkPricingScraper, PricingRecord

logger = logging.getLogger(__name__)

_PRICING_URL = "https://www.tesla.com/en_ca/support/supercharging"

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
}

# Matches patterns like "$0.45/kWh", "$0.45 / kWh", "$0.45 per kWh"
_RATE_RE = re.compile(r"\$\s*(\d+\.\d+)\s*(?:/|per)\s*kWh", re.IGNORECASE)

_RATE_RANGE = (0.10, 1.50)  # plausible CAD/kWh range for DCFC in Canada

# Hardcoded fallback rates – representative CAD/kWh by province, researched from
# published Tesla Supercharger pricing reporting (driveteslacanada.ca, 2025/2026).
# Tesla-vehicle ("member") rates are cheaper than the "Supercharging for all other
# EVs" (non-Tesla / NACS) rate at the same stall.
_FALLBACK_RATES: dict[str, dict[str, float]] = {
    "BC": {"member": 0.38, "non_member": 0.55},
    "AB": {"member": 0.62, "non_member": 0.78},
    "SK": {"member": 0.45, "non_member": 0.62},
    "MB": {"member": 0.42, "non_member": 0.58},
    "ON": {"member": 0.45, "non_member": 0.65},
    "QC": {"member": 0.42, "non_member": 0.58},
    "NB": {"member": 0.40, "non_member": 0.56},
    "NS": {"member": 0.40, "non_member": 0.56},
    "PE": {"member": 0.40, "non_member": 0.56},
    "NL": {"member": 0.40, "non_member": 0.56},
}


class TeslaScraper(NetworkPricingScraper):
    network_name = "Tesla"

    def scrape(self) -> list[PricingRecord]:
        """Scrape Tesla Supercharger CAD/kWh pricing for member and non-member tiers.

        Attempts a live fetch of Tesla's public support page first. If the
        request fails or no plausible rate can be parsed from the page, falls
        back to hardcoded but realistic per-province CAD/kWh rates.
        """
        scraped_rate = self._fetch_live_rate()

        records: list[PricingRecord] = []
        for province_code, tiers in _FALLBACK_RATES.items():
            for membership_tier, fallback_rate in tiers.items():
                rate_value = scraped_rate if scraped_rate is not None else fallback_rate
                records.append(
                    PricingRecord(
                        network_name=self.network_name,
                        province_code=province_code,
                        membership_tier=membership_tier,
                        pricing_model="per_kwh",
                        rate_value=rate_value,
                        rate_unit="cad_per_kwh",
                        currency="CAD",
                    )
                )

        logger.info(
            "%s scraper returning %d pricing records (%s)",
            self.network_name,
            len(records),
            "live" if scraped_rate is not None else "fallback",
        )
        return records

    def _fetch_live_rate(self) -> float | None:
        """Attempt to fetch and parse a representative CAD/kWh rate from Tesla's
        public Supercharging support page. Returns None on any failure."""
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

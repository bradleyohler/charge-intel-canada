from __future__ import annotations

import logging
import re

import requests
from bs4 import BeautifulSoup

from ingestion.sources.scrapers.base import NetworkPricingScraper, PricingRecord

logger = logging.getLogger(__name__)

_PRICING_URL = "https://www.electrify-canada.ca/pricing"

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
}

_TIMEOUT_SECONDS = 15

# Matches patterns like "$0.65/kWh", "$0.65 per kWh"
_RATE_RE = re.compile(r"\$\s*(\d+\.\d+)\s*(?:/|per\s+)\s*kWh", re.IGNORECASE)

_RATE_RANGE = (0.20, 1.20)  # plausible CAD/kWh range for DCFC pay-as-you-go pricing

# Electrify Canada switched from per-minute to per-kWh billing in Jan 2024.
# Guest (pay-as-you-go) rates vary by province; Pass+ membership ($4/month)
# gives an approx. 20% discount off the Guest rate. Used as fallback when the
# live pricing page can't be fetched or parsed.
_FALLBACK_GUEST_RATES_CAD_PER_KWH: dict[str, float] = {
    "BC": 0.70,
    "AB": 0.60,
    "SK": 0.60,
    "ON": 0.65,
    "QC": 0.65,
}

_PASS_PLUS_DISCOUNT = 0.20  # Pass+ members pay ~20% less than Guest rate


def _extract_rates_from_page(html: str) -> dict[str, float]:
    """Parse the Electrify Canada pricing page for per-province Guest rates.

    Returns a mapping of province_code -> CAD/kWh Guest rate for any
    provinces whose rate could be confidently located near a province
    name/code in the page text.
    """
    soup = BeautifulSoup(html, "html.parser")
    found: dict[str, float] = {}

    province_names = {
        "BC": ("british columbia", "bc"),
        "AB": ("alberta", "ab"),
        "SK": ("saskatchewan", "sk"),
        "ON": ("ontario", "on"),
        "QC": ("quebec", "québec", "qc"),
    }

    for tag in soup.find_all(["p", "li", "span", "div", "td", "th"]):
        text = tag.get_text(" ", strip=True)
        match = _RATE_RE.search(text)
        if not match:
            continue
        value = float(match.group(1))
        if not (_RATE_RANGE[0] <= value <= _RATE_RANGE[1]):
            continue
        lowered = text.lower()
        for province_code, names in province_names.items():
            if province_code in found:
                continue
            if any(name in lowered for name in names):
                found[province_code] = value
                logger.debug(
                    "Found Electrify Canada rate %.2f CAD/kWh for %s",
                    value,
                    province_code,
                )

    return found


class ElectrifyCanadaScraper(NetworkPricingScraper):
    network_name = "Electrify Canada"

    def scrape(self) -> list[PricingRecord]:
        """Scrape Electrify Canada per-province Guest and Pass+ kWh rates.

        Electrify Canada bills per kWh (since Jan 2024) with rates that vary
        by province, and offers a Pass+ membership ($4/month) at a discount
        off the Guest rate. If the live page cannot be fetched or parsed,
        falls back to the most recently published province rates. Never
        raises - on any failure, logs a warning and uses fallback data.
        """
        guest_rates: dict[str, float] = {}

        try:
            response = requests.get(
                _PRICING_URL, headers=_HEADERS, timeout=_TIMEOUT_SECONDS
            )
            response.raise_for_status()
            guest_rates = _extract_rates_from_page(response.text)
            if not guest_rates:
                logger.warning(
                    "%s: could not extract any province rates from page %s",
                    self.network_name,
                    _PRICING_URL,
                )
        except requests.RequestException as exc:
            logger.warning(
                "%s: HTTP fetch failed for %s - %s",
                self.network_name,
                _PRICING_URL,
                exc,
            )

        for province_code, fallback_rate in _FALLBACK_GUEST_RATES_CAD_PER_KWH.items():
            if province_code not in guest_rates:
                guest_rates[province_code] = fallback_rate
                logger.info(
                    "%s: using hardcoded fallback rate %.2f CAD/kWh for %s",
                    self.network_name,
                    fallback_rate,
                    province_code,
                )

        records: list[PricingRecord] = []
        for province_code, guest_rate in guest_rates.items():
            pass_plus_rate = round(guest_rate * (1 - _PASS_PLUS_DISCOUNT), 4)

            records.append(
                PricingRecord(
                    network_name=self.network_name,
                    province_code=province_code,
                    membership_tier="guest",
                    pricing_model="per_kwh",
                    rate_value=guest_rate,
                    rate_unit="cad_per_kwh",
                    currency="CAD",
                )
            )
            records.append(
                PricingRecord(
                    network_name=self.network_name,
                    province_code=province_code,
                    membership_tier="pass_plus",
                    pricing_model="per_kwh",
                    rate_value=pass_plus_rate,
                    rate_unit="cad_per_kwh",
                    currency="CAD",
                )
            )
            logger.info(
                "%s (%s): guest=%.2f CAD/kWh, pass_plus=%.2f CAD/kWh",
                self.network_name,
                province_code,
                guest_rate,
                pass_plus_rate,
            )

        return records


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    for record in ElectrifyCanadaScraper().scrape():
        logger.info(record)

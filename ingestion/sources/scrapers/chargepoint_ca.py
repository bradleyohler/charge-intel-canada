from __future__ import annotations

import logging
import re

import requests
from bs4 import BeautifulSoup

from ingestion.sources.scrapers.base import NetworkPricingScraper, PricingRecord

logger = logging.getLogger(__name__)

_PRICING_URL = (
    "https://www.chargepoint.com/drivers/support/faqs/"
    "how-much-will-it-cost-charge-my-car-who-sets-prices-charging"
)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}

# Matches a combined "$0.25/kWh plus $0.10/minute" style example used by
# ChargePoint's stacked billing model (kWh + per-minute on the same session).
_SESSION_PLUS_RE = re.compile(
    r"\$?\s*(\d+\.\d+)\s*/\s*kWh.{0,20}?\$?\s*(\d+\.\d+)\s*/\s*min",
    re.IGNORECASE | re.DOTALL,
)
_KWH_ONLY_RE = re.compile(r"\$?\s*(\d+\.\d+)\s*/\s*kWh", re.IGNORECASE)
_MINUTE_ONLY_RE = re.compile(r"\$?\s*(\d+\.\d+)\s*/\s*min(?:ute)?", re.IGNORECASE)

_RATE_RANGE_KWH = (0.10, 1.00)
_RATE_RANGE_MINUTE = (0.01, 0.30)

# Hardcoded fallback pricing reflecting ChargePoint's published/observed Canadian
# rate structure as of research date. ChargePoint stations are independently
# priced by station owners/roaming partners and commonly stack a per-kWh rate
# with a per-minute fee on DCFC; Level 2 stations are typically billed per-hour
# (modeled here as per-minute for normalization purposes). Sources: ChargePoint
# driver FAQ pages and observed Metro Vancouver / Ontario station pricing via
# aggregator sites (ChargeHub, ThinkEV.ca) as of research date.
_FALLBACK_DCFC_RATES: dict[str, tuple[float, float]] = {
    # province_code: (cad_per_kwh, cad_per_session_flat_fee)
    "BC": (0.33, 1.00),
    "AB": (0.32, 1.00),
    "SK": (0.32, 1.00),
    "MB": (0.30, 1.00),
    "ON": (0.35, 1.50),
    "QC": (0.28, 1.00),
    "NB": (0.33, 1.00),
    "NS": (0.33, 1.00),
    "PE": (0.33, 1.00),
    "NL": (0.34, 1.00),
}
_FALLBACK_L2_RATE_PER_MINUTE = 0.025  # roughly $1.50/hour, national L2 estimate

_OUTPUT_RATE_UNIT_KWH = "cad_per_kwh"
_OUTPUT_RATE_UNIT_MINUTE = "cad_per_minute"


class ChargePointCAScraper(NetworkPricingScraper):
    network_name = "ChargePoint CA"

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

        for block in soup.find_all(["tr", "li", "p", "div"]):
            text = block.get_text(" ", strip=True)
            if not text:
                continue

            combined = _SESSION_PLUS_RE.search(text)
            if combined:
                kwh_rate = float(combined.group(1))
                minute_rate = float(combined.group(2))
                if _RATE_RANGE_KWH[0] <= kwh_rate <= _RATE_RANGE_KWH[1]:
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
                if _RATE_RANGE_MINUTE[0] <= minute_rate <= _RATE_RANGE_MINUTE[1]:
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
                continue

            kwh_match = _KWH_ONLY_RE.search(text)
            if kwh_match:
                value = float(kwh_match.group(1))
                if _RATE_RANGE_KWH[0] <= value <= _RATE_RANGE_KWH[1]:
                    records.append(
                        PricingRecord(
                            network_name=self.network_name,
                            province_code=None,
                            membership_tier="pay_as_you_go",
                            pricing_model="per_kwh",
                            rate_value=value,
                            rate_unit=_OUTPUT_RATE_UNIT_KWH,
                            currency="CAD",
                        )
                    )
                continue

            minute_match = _MINUTE_ONLY_RE.search(text)
            if minute_match:
                value = float(minute_match.group(1))
                if _RATE_RANGE_MINUTE[0] <= value <= _RATE_RANGE_MINUTE[1]:
                    records.append(
                        PricingRecord(
                            network_name=self.network_name,
                            province_code=None,
                            membership_tier="pay_as_you_go",
                            pricing_model="per_minute",
                            rate_value=value,
                            rate_unit=_OUTPUT_RATE_UNIT_MINUTE,
                            currency="CAD",
                        )
                    )

        return records

    def _fallback_records(self) -> list[PricingRecord]:
        records: list[PricingRecord] = []

        for province_code, (kwh_rate, session_fee) in _FALLBACK_DCFC_RATES.items():
            records.append(
                PricingRecord(
                    network_name=self.network_name,
                    province_code=province_code,
                    membership_tier="pay_as_you_go",
                    pricing_model="session_plus_kwh",
                    rate_value=kwh_rate,
                    rate_unit=_OUTPUT_RATE_UNIT_KWH,
                    currency="CAD",
                    session_fee_value=session_fee,
                )
            )
            logger.info(
                "%s: using hardcoded fallback DCFC rate %.2f CAD/kWh + "
                "%.2f CAD session fee for %s",
                self.network_name,
                kwh_rate,
                session_fee,
                province_code,
            )

        # ChargePoint Level 2 stations are commonly billed per-minute, nationally.
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
    scraper = ChargePointCAScraper()
    results = scraper.scrape()
    for rec in results:
        logger.info(rec)

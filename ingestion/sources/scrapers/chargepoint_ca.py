from __future__ import annotations

import logging

from ingestion.sources.scrapers.base import NetworkPricingScraper, PricingRecord

logger = logging.getLogger(__name__)


class ChargePointCAScraper(NetworkPricingScraper):
    network_name = "ChargePoint CA"

    def scrape(self) -> list[PricingRecord]:
        # TODO: implement scraping from ChargePoint CA pricing page
        logger.warning("%s scraper not yet implemented", self.network_name)
        return []

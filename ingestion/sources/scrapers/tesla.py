from __future__ import annotations

import logging

from ingestion.sources.scrapers.base import NetworkPricingScraper, PricingRecord

logger = logging.getLogger(__name__)


class TeslaScraper(NetworkPricingScraper):
    network_name = "Tesla"

    def scrape(self) -> list[PricingRecord]:
        # TODO: implement scraping from Tesla Supercharger pricing page
        logger.warning("%s scraper not yet implemented", self.network_name)
        return []

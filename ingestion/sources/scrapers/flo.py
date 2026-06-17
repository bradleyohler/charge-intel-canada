from __future__ import annotations

import logging

from ingestion.sources.scrapers.base import NetworkPricingScraper, PricingRecord

logger = logging.getLogger(__name__)


class FloScraper(NetworkPricingScraper):
    network_name = "FLO"

    def scrape(self) -> list[PricingRecord]:
        # TODO: implement scraping from https://www.flo.com/drivers/pricing/
        logger.warning("%s scraper not yet implemented", self.network_name)
        return []

from __future__ import annotations

import logging

from ingestion.sources.scrapers.base import NetworkPricingScraper, PricingRecord

logger = logging.getLogger(__name__)


class PetroCanadaScraper(NetworkPricingScraper):
    network_name = "Petro-Canada"

    def scrape(self) -> list[PricingRecord]:
        # TODO: implement scraping from Petro-Canada EV charging pricing page
        logger.warning("%s scraper not yet implemented", self.network_name)
        return []

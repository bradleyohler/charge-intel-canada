from __future__ import annotations

import logging

from ingestion.sources.scrapers.base import NetworkPricingScraper, PricingRecord

logger = logging.getLogger(__name__)


class ElectrifyCanadaScraper(NetworkPricingScraper):
    network_name = "Electrify Canada"

    def scrape(self) -> list[PricingRecord]:
        # TODO: implement scraping from Electrify Canada pricing page
        logger.warning("%s scraper not yet implemented", self.network_name)
        return []

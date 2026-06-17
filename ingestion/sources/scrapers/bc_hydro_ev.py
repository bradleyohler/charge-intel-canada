from __future__ import annotations

import logging

from ingestion.sources.scrapers.base import NetworkPricingScraper, PricingRecord

logger = logging.getLogger(__name__)


class BCHydroEVScraper(NetworkPricingScraper):
    network_name = "BC Hydro EV"

    def scrape(self) -> list[PricingRecord]:
        # TODO: implement scraping from BC Hydro EV pricing page
        logger.warning("%s scraper not yet implemented", self.network_name)
        return []

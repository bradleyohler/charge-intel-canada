from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal

PricingModel = Literal[
    "per_kwh", "per_minute", "flat_fee", "session_plus_kwh", "unknown"
]


@dataclass
class PricingRecord:
    network_name: str
    province_code: str | None
    membership_tier: str
    pricing_model: PricingModel
    rate_value: float | None
    rate_unit: str
    currency: str
    scraped_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class NetworkPricingScraper(ABC):
    network_name: str

    @abstractmethod
    def scrape(self) -> list[PricingRecord]:
        ...

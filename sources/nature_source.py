from __future__ import annotations

from datetime import date
import logging

from sources.base import Source
from utils.models import Paper

LOGGER = logging.getLogger(__name__)


class NatureSource(Source):
    """Placeholder for Nature and Nature sub-journal integrations.

    Many Nature feeds and APIs have product-specific access rules. This module
    keeps the source interface ready without hard-coding brittle scraping logic.
    """

    name = "nature"

    def fetch(self, target_date: date, topics: list[str], timezone: str) -> list[Paper]:
        LOGGER.info(
            "Nature source is a placeholder. See README.md for integration notes."
        )
        return []

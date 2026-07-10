from __future__ import annotations

from datetime import date
import logging

from sources.base import Source
from utils.models import Paper

LOGGER = logging.getLogger(__name__)


class ScienceSource(Source):
    """Placeholder for Science / AAAS integrations."""

    name = "science"

    def fetch(self, target_date: date, topics: list[str]) -> list[Paper]:
        LOGGER.info(
            "Science source is a placeholder. See README.md for integration notes."
        )
        return []


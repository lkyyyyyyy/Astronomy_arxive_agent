from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date

from config.loader import SourceConfig
from utils.models import Paper


class Source(ABC):
    name: str

    def __init__(self, config: SourceConfig) -> None:
        self.config = config

    @abstractmethod
    def fetch(self, target_date: date, topics: list[str]) -> list[Paper]:
        """Fetch items published on target_date."""


from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

from utils.models import RankedPaper


@dataclass(slots=True)
class DeliveryContext:
    markdown: str
    markdown_path: Path | None
    html_path: Path | None
    total_fetched: int
    selected_papers: list[RankedPaper]
    public_url: str = ""


class DeliveryChannel(ABC):
    @abstractmethod
    def send(self, title: str, context: DeliveryContext) -> None:
        """Send a briefing through a delivery channel."""

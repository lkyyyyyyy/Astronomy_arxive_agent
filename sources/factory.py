from __future__ import annotations

from config.loader import SourceConfig
from sources.arxiv_source import ArxivSource
from sources.base import Source
from sources.nature_source import NatureSource
from sources.science_source import ScienceSource


SOURCE_CLASSES: dict[str, type[Source]] = {
    "arxiv": ArxivSource,
    "nature": NatureSource,
    "science": ScienceSource,
}


def build_sources(configs: dict[str, SourceConfig]) -> list[Source]:
    sources: list[Source] = []
    for name, config in configs.items():
        if not config.enabled:
            continue
        source_cls = SOURCE_CLASSES.get(name)
        if not source_cls:
            raise ValueError(f"Unknown source configured: {name}")
        sources.append(source_cls(config))
    return sources


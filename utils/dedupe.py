from __future__ import annotations

import re

from utils.models import Paper


def _normalize_title(title: str) -> str:
    title = title.casefold()
    title = re.sub(r"[^a-z0-9]+", " ", title)
    return " ".join(title.split())


def dedupe_papers(papers: list[Paper]) -> list[Paper]:
    seen_titles: set[str] = set()
    seen_urls: set[str] = set()
    unique: list[Paper] = []

    for paper in papers:
        title_key = _normalize_title(paper.title)
        url_key = paper.url.strip().lower()
        if title_key in seen_titles or url_key in seen_urls:
            continue
        seen_titles.add(title_key)
        seen_urls.add(url_key)
        unique.append(paper)

    return unique


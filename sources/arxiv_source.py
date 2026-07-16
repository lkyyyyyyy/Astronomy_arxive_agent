from __future__ import annotations

from datetime import date, datetime, timezone as datetime_timezone
from email.utils import parsedate_to_datetime
import logging
import time
from urllib.parse import urlencode
import xml.etree.ElementTree as ET

import requests

from sources.base import Source
from utils.dates import report_window
from utils.models import Paper

LOGGER = logging.getLogger(__name__)


class ArxivSource(Source):
    name = "arxiv"
    api_url = "https://export.arxiv.org/api/query"

    def fetch(self, target_date: date, topics: list[str], timezone: str) -> list[Paper]:
        window_start, window_end = report_window(target_date, timezone)
        query = self._build_query(window_start, window_end)
        response_text = self._request_feed(query, window_start, window_end)
        if response_text is None:
            return []

        return self._parse_feed(response_text, window_start, window_end)

    def _request_feed(
        self,
        query: str,
        window_start: datetime,
        window_end: datetime,
    ) -> str | None:
        params = {
            "search_query": query,
            "start": 0,
            "max_results": self.config.max_results,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        }
        url = f"{self.api_url}?{urlencode(params)}"
        LOGGER.info("Fetching arXiv papers for %s to %s", window_start, window_end)

        timeout = max(10, int(getattr(self.config, "timeout_seconds", 90)))
        retries = max(1, int(getattr(self.config, "retries", 3)))
        for attempt in range(1, retries + 1):
            try:
                response = requests.get(url, timeout=timeout)
                response.raise_for_status()
                return response.text
            except requests.RequestException as exc:
                if attempt >= retries:
                    LOGGER.error("arXiv fetch failed after %d attempt(s): %s", attempt, exc)
                    return None
                sleep_seconds = min(20, attempt * 3)
                LOGGER.warning(
                    "arXiv fetch attempt %d/%d failed: %s; retrying in %ds.",
                    attempt,
                    retries,
                    exc,
                    sleep_seconds,
                )
                time.sleep(sleep_seconds)

        return None

    def _parse_feed(
        self,
        response_text: str,
        window_start: datetime,
        window_end: datetime,
    ) -> list[Paper]:
        papers: list[Paper] = []
        try:
            root = ET.fromstring(response_text)
        except ET.ParseError as exc:
            LOGGER.error("Could not parse arXiv response: %s", exc)
            return []

        namespace = {"atom": "http://www.w3.org/2005/Atom"}
        for entry in root.findall("atom:entry", namespace):
            published_dt = _entry_datetime(entry)
            if not published_dt:
                continue
            published_local = published_dt.astimezone(window_start.tzinfo)
            if not (window_start <= published_local < window_end):
                continue
            papers.append(
                Paper(
                    title=_clean_text(_text(entry, "atom:title", namespace)),
                    authors=_authors(entry, namespace),
                    abstract=_clean_text(_text(entry, "atom:summary", namespace)),
                    published_date=published_local.date(),
                    source=self.name,
                    journal="arXiv",
                    url=_entry_url(entry, namespace),
                    pdf_url=_pdf_url(entry),
                    raw_id=_text(entry, "atom:id", namespace),
                    published_datetime=published_local,
                )
            )

        LOGGER.info(
            "Fetched %d arXiv papers for %s to %s",
            len(papers),
            window_start,
            window_end,
        )
        return papers

    def _build_query(self, window_start: datetime, window_end: datetime) -> str:
        start_utc = window_start.astimezone(datetime_timezone.utc)
        end_utc = window_end.astimezone(datetime_timezone.utc)
        date_query = (
            f"submittedDate:[{start_utc:%Y%m%d%H%M} TO {end_utc:%Y%m%d%H%M}]"
        )

        if self.config.categories:
            cats = " OR ".join(f"cat:{category}" for category in self.config.categories)
            return f"({cats}) AND {date_query}"

        LOGGER.warning("No arXiv categories configured; query may be very broad.")
        return f"all:* AND {date_query}"


def _entry_datetime(entry: ET.Element) -> datetime | None:
    namespace = {"atom": "http://www.w3.org/2005/Atom"}
    raw = _text(entry, "atom:published", namespace) or _text(
        entry, "atom:updated", namespace
    )
    if not raw:
        return None
    try:
        parsed = parsedate_to_datetime(raw)
    except (TypeError, ValueError):
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=datetime_timezone.utc)
    return parsed


def _pdf_url(entry: ET.Element) -> str | None:
    namespace = {"atom": "http://www.w3.org/2005/Atom"}
    for link in entry.findall("atom:link", namespace):
        if link.attrib.get("type") == "application/pdf":
            return link.attrib.get("href")
    raw_id = _text(entry, "atom:id", namespace)
    if raw_id:
        return raw_id.replace("/abs/", "/pdf/")
    return None


def _entry_url(entry: ET.Element, namespace: dict[str, str]) -> str:
    for link in entry.findall("atom:link", namespace):
        if link.attrib.get("rel") == "alternate":
            return link.attrib.get("href", "")
    raw_id = _text(entry, "atom:id", namespace)
    return raw_id


def _authors(entry: ET.Element, namespace: dict[str, str]) -> list[str]:
    authors = []
    for author in entry.findall("atom:author", namespace):
        name = author.find("atom:name", namespace)
        if name is not None and name.text:
            authors.append(_clean_text(name.text))
    return authors


def _text(entry: ET.Element, path: str, namespace: dict[str, str]) -> str:
    node = entry.find(path, namespace)
    return node.text if node is not None and node.text else ""


def _clean_text(value: str) -> str:
    return " ".join(value.replace("\n", " ").split())

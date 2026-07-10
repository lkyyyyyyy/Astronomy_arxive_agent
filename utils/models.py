from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass(slots=True)
class Paper:
    title: str
    authors: list[str]
    abstract: str
    published_date: date
    source: str
    url: str
    pdf_url: str | None = None
    journal: str | None = None
    raw_id: str | None = None


@dataclass(slots=True)
class RankedPaper:
    paper: Paper
    interest_score: int
    novelty: str
    potential_impact: str
    relevance: str
    reason: str


@dataclass(slots=True)
class PaperSummary:
    one_sentence: str
    detailed_summary: str
    key_contribution: str
    why_read: str
    methods: str
    limitations: str
    future_work: str
    abstract_translation: str


@dataclass(slots=True)
class Briefing:
    target_date: date
    highlights: list[str] = field(default_factory=list)
    must_read: list[tuple[RankedPaper, PaperSummary]] = field(default_factory=list)
    recommended: list[tuple[RankedPaper, PaperSummary]] = field(default_factory=list)
    research_trends: list[str] = field(default_factory=list)
    open_questions: list[str] = field(default_factory=list)

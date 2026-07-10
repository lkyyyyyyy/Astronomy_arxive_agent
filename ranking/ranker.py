from __future__ import annotations

import logging
from textwrap import shorten

from llm.base import LLMClient
from utils.json_tools import extract_json
from utils.models import Paper, RankedPaper

LOGGER = logging.getLogger(__name__)


class PaperRanker:
    def __init__(self, llm: LLMClient, language: str, system_prompt: str) -> None:
        self.llm = llm
        self.language = language
        self.system_prompt = system_prompt

    def rank(self, papers: list[Paper], topics: list[str]) -> list[RankedPaper]:
        if not papers:
            return []

        try:
            return self._rank_with_llm(papers, topics)
        except Exception as exc:
            LOGGER.warning("LLM ranking failed; using heuristic ranking: %s", exc)
            return self._rank_heuristically(papers, topics)

    def _rank_with_llm(self, papers: list[Paper], topics: list[str]) -> list[RankedPaper]:
        user_prompt = self._ranking_prompt(papers, topics)
        raw = self.llm.complete(self.system_prompt, user_prompt)
        data = extract_json(raw)
        if not isinstance(data, list):
            raise ValueError("Ranking response must be a JSON list")

        by_index = {item.get("index"): item for item in data if isinstance(item, dict)}
        ranked: list[RankedPaper] = []
        for idx, paper in enumerate(papers, start=1):
            item = by_index.get(idx)
            if not item:
                continue
            ranked.append(
                RankedPaper(
                    paper=paper,
                    interest_score=_bounded_score(item.get("interest_score", 0)),
                    novelty=str(item.get("novelty", "")).strip(),
                    potential_impact=str(item.get("potential_impact", "")).strip(),
                    relevance=str(item.get("relevance", "")).strip(),
                    reason=str(item.get("reason", "")).strip(),
                )
            )

        if not ranked:
            raise ValueError("No ranked papers returned")
        return sorted(ranked, key=lambda item: item.interest_score, reverse=True)

    def _ranking_prompt(self, papers: list[Paper], topics: list[str]) -> str:
        paper_blocks = []
        for idx, paper in enumerate(papers, start=1):
            paper_blocks.append(
                "\n".join(
                    [
                        f"Index: {idx}",
                        f"Title: {paper.title}",
                        f"Authors: {', '.join(paper.authors[:8])}",
                        f"Source: {paper.journal or paper.source}",
                        f"Date: {paper.published_date.isoformat()}",
                        f"Abstract: {shorten(paper.abstract, width=1600, placeholder='...')}",
                    ]
                )
            )

        return f"""
Output language for all text fields: Chinese.
User interests: {", ".join(topics)}

Rank every paper below. Score 0-100 using novelty, potential impact, and relevance
to the interests. Return exactly one valid JSON array using double quotes and no
trailing commas. Each item must use this schema:
[
  {{
    "index": 1,
    "interest_score": 85,
    "novelty": "中文说明。",
    "potential_impact": "中文说明。",
    "relevance": "中文说明。",
    "reason": "中文推荐理由。"
  }}
]

Style requirements:
- All explanation fields must be Chinese.
- Keep paper titles in their original language when mentioning them.
- For technical terms, use Chinese first and put English in parentheses when useful.
- Examples: 中等质量黑洞（intermediate-mass black hole）, 活动星系核（AGN）, 引力透镜（gravitational lensing）.
- Return strict valid JSON only. No Markdown. No code fences. No commentary.

Papers:
{chr(10).join(paper_blocks)}
""".strip()

    def _rank_heuristically(self, papers: list[Paper], topics: list[str]) -> list[RankedPaper]:
        ranked = []
        for paper in papers:
            haystack = f"{paper.title} {paper.abstract}".casefold()
            matches = [topic for topic in topics if topic.casefold() in haystack]
            source_bonus = 15 if (paper.journal or "").lower() in {"nature", "science"} else 0
            score = min(100, 45 + len(matches) * 10 + source_bonus)
            reason = (
                f"与已配置兴趣相关：{', '.join(matches)}。"
                if matches
                else "这是当天抓取到的论文，但暂未发现与配置兴趣的精确关键词匹配。"
            )
            ranked.append(
                RankedPaper(
                    paper=paper,
                    interest_score=score,
                    novelty="暂未提取",
                    potential_impact="基于来源和关键词相关性的初步判断。",
                    relevance=reason,
                    reason=reason,
                )
            )
        return sorted(ranked, key=lambda item: item.interest_score, reverse=True)


def _bounded_score(value: object) -> int:
    try:
        score = int(value)
    except (TypeError, ValueError):
        return 0
    return max(0, min(100, score))

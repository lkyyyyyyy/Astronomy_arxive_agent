from __future__ import annotations

import logging
from textwrap import shorten

from llm.base import LLMClient
from utils.json_tools import extract_json
from utils.models import Paper, RankedPaper

LOGGER = logging.getLogger(__name__)
MAX_LLM_RANKING_CANDIDATES = 80
LLM_RANKING_BATCH_SIZE = 12


class PaperRanker:
    def __init__(self, llm: LLMClient, language: str, system_prompt: str) -> None:
        self.llm = llm
        self.language = language
        self.system_prompt = system_prompt

    def rank(self, papers: list[Paper], topics: list[str]) -> list[RankedPaper]:
        if not papers:
            return []

        heuristic = self._rank_heuristically(papers, topics)
        candidates = [item.paper for item in heuristic[:MAX_LLM_RANKING_CANDIDATES]]
        try:
            llm_ranked = self._rank_with_llm(candidates, topics)
            ranked_by_url = {item.paper.url: item for item in llm_ranked}
            merged = list(llm_ranked)
            merged.extend(
                item for item in heuristic if item.paper.url not in ranked_by_url
            )
            return sorted(merged, key=lambda item: item.interest_score, reverse=True)
        except Exception as exc:
            LOGGER.warning("LLM ranking failed; using heuristic ranking: %s", exc)
            return heuristic

    def _rank_with_llm(self, papers: list[Paper], topics: list[str]) -> list[RankedPaper]:
        ranked: list[RankedPaper] = []
        for start in range(0, len(papers), LLM_RANKING_BATCH_SIZE):
            batch = papers[start : start + LLM_RANKING_BATCH_SIZE]
            try:
                ranked.extend(self._rank_batch_with_llm(batch, topics))
            except Exception as exc:
                LOGGER.warning(
                    "LLM ranking batch failed; using heuristic ranking for that batch: %s",
                    exc,
                )
                ranked.extend(self._rank_heuristically(batch, topics))

        if not ranked:
            raise ValueError("No ranked papers returned")
        return sorted(ranked, key=lambda item: item.interest_score, reverse=True)

    def _rank_batch_with_llm(self, papers: list[Paper], topics: list[str]) -> list[RankedPaper]:
        user_prompt = self._ranking_prompt(papers, topics)
        raw = self.llm.complete(self.system_prompt, user_prompt)
        data = extract_json(raw)
        if isinstance(data, dict):
            rows = data.get("rankings") or data.get("items") or data.get("papers")
        else:
            rows = data
        if not isinstance(rows, list):
            raise ValueError("Ranking response must contain a JSON list under rankings")

        by_index = {item.get("index"): item for item in rows if isinstance(item, dict)}
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
                        f"Abstract: {shorten(paper.abstract, width=900, placeholder='...')}",
                    ]
                )
            )

        return f"""
Output language for all text fields: Chinese.
User interests, used as preference signals but not hard filters: {", ".join(topics)}

Rank every paper below. Score 0-100 using broad scientific value, novelty,
methodological strength, potential impact, timeliness, source prestige when
available, and relevance to the user interests. Papers can be highly recommended
even when they are outside the configured interests if they are unusually novel,
important, methodologically useful, published in Nature/Science, or simply
scientifically interesting.

Return exactly one valid JSON object using double quotes and no trailing commas.
Use this schema:
{{
  "rankings": [
    {{
      "index": 1,
      "interest_score": 85,
      "novelty": "中文短句。",
      "potential_impact": "中文短句。",
      "relevance": "中文短句。",
      "reason": "中文推荐理由，控制在60个汉字以内。"
    }}
  ]
}}

Style requirements:
- All explanation fields must be Chinese.
- Keep paper titles in their original language when mentioning them.
- For technical terms, use Chinese first and put English in parentheses when useful.
- Examples: 中等质量黑洞（intermediate-mass black hole）, 活动星系核（AGN）, 引力透镜（gravitational lensing）.
- Do not over-rank a paper merely because it contains an interest keyword.
- Prefer papers with clear new data, new methods, broad implications, strong surveys, notable instruments, or surprising results.
- Scores below 60 mean the paper should usually not appear in the final briefing.
- Return strict valid JSON object only. No Markdown. No code fences. No commentary.

Papers:
{chr(10).join(paper_blocks)}
""".strip()

    def _rank_heuristically(self, papers: list[Paper], topics: list[str]) -> list[RankedPaper]:
        ranked = []
        for paper in papers:
            haystack = f"{paper.title} {paper.abstract}".casefold()
            matches = _interest_matches(topics, haystack)
            score = 48
            score += min(18, len(matches) * 5)
            score += _keyword_bonus(haystack, _NOVELTY_TERMS, 12)
            score += _keyword_bonus(haystack, _METHOD_TERMS, 10)
            score += _keyword_bonus(haystack, _IMPACT_TERMS, 10)
            if _is_prestige_source(paper):
                score += 18
            if len(paper.abstract) > 900:
                score += 4
            score = min(100, score)
            reason_parts = []
            if matches:
                reason_parts.append(f"与用户兴趣相关：{', '.join(matches[:4])}")
            if _contains_any(haystack, _NOVELTY_TERMS):
                reason_parts.append("摘要显示有新样本、新发现或新方法")
            if _contains_any(haystack, _METHOD_TERMS):
                reason_parts.append("方法或数据集具有复用价值")
            if _contains_any(haystack, _IMPACT_TERMS):
                reason_parts.append("可能对相关领域有较宽影响")
            if _is_prestige_source(paper):
                reason_parts.append("来源优先级较高")
            reason = "；".join(reason_parts) + "。" if reason_parts else "基于标题、摘要和来源的通用科研价值进行初步推荐。"
            ranked.append(
                RankedPaper(
                    paper=paper,
                    interest_score=score,
                    novelty="基于摘要关键词的初步判断。",
                    potential_impact="基于来源、方法和摘要信号的初步判断。",
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


_NOVELTY_TERMS = [
    "new",
    "novel",
    "first",
    "discover",
    "discovery",
    "unprecedented",
    "previously unknown",
    "candidate",
    "constraints",
]
_METHOD_TERMS = [
    "jwst",
    "muse",
    "alma",
    "euclid",
    "roman",
    "rubin",
    "lsst",
    "simulation",
    "machine learning",
    "deep learning",
    "spectroscopy",
    "survey",
    "catalog",
    "catalogue",
]
_IMPACT_TERMS = [
    "implications",
    "challenge",
    "constraints",
    "population",
    "formation",
    "evolution",
    "cosmology",
    "dark matter",
]


def _interest_matches(topics: list[str], haystack: str) -> list[str]:
    aliases = {
        "agn": ["agn", "active galactic nucleus", "active galactic nuclei", "quasar", "quasars"],
        "black holes": ["black hole", "black holes"],
        "intermediate-mass black holes": ["intermediate-mass black hole", "intermediate mass black hole", "imbh"],
        "dwarf galaxies": ["dwarf galaxy", "dwarf galaxies"],
        "galaxy evolution": ["galaxy evolution"],
        "jwst": ["jwst", "james webb"],
        "muse": ["muse"],
        "lensing": ["lensing", "gravitational lens"],
    }
    matches = []
    for topic in topics:
        keys = aliases.get(topic.casefold(), [topic.casefold()])
        if any(key in haystack for key in keys):
            matches.append(topic)
    return matches


def _keyword_bonus(haystack: str, terms: list[str], maximum: int) -> int:
    matches = sum(1 for term in terms if term in haystack)
    return min(maximum, matches * 3)


def _contains_any(haystack: str, terms: list[str]) -> bool:
    return any(term in haystack for term in terms)


def _is_prestige_source(paper: Paper) -> bool:
    text = f"{paper.source} {paper.journal or ''}".casefold()
    return any(name in text for name in ["nature", "science"])

from __future__ import annotations

import logging
from textwrap import shorten

from llm.base import LLMClient
from utils.json_tools import extract_json
from utils.models import PaperSummary, RankedPaper

LOGGER = logging.getLogger(__name__)


class PaperSummarizer:
    def __init__(self, llm: LLMClient, language: str, system_prompt: str) -> None:
        self.llm = llm
        self.language = language
        self.system_prompt = system_prompt

    def summarize(self, ranked_papers: list[RankedPaper]) -> dict[str, PaperSummary]:
        summaries: dict[str, PaperSummary] = {}
        for ranked in ranked_papers:
            key = ranked.paper.url
            try:
                summaries[key] = self._summarize_with_llm(ranked)
            except Exception as exc:
                LOGGER.warning(
                    "LLM summary failed for %s; using extractive fallback: %s",
                    ranked.paper.title,
                    exc,
                )
                summaries[key] = self._fallback_summary(ranked)
        return summaries

    def _summarize_with_llm(self, ranked: RankedPaper) -> PaperSummary:
        paper = ranked.paper
        user_prompt = f"""
Output language: Chinese, except keep the original paper title unchanged.

Paper:
Title: {paper.title}
Authors: {", ".join(paper.authors)}
Source: {paper.journal or paper.source}
Abstract: {paper.abstract}
Ranking reason: {ranked.reason}

Return exactly one valid JSON object using double quotes and no trailing commas.
Use exactly these keys:
{{
  "one_sentence_summary_zh": "一句清晰的中文总结，不超过80个汉字。",
  "key_contribution_zh": "中文主要贡献。",
  "why_read_zh": "自然的中文段落，说明这篇论文为什么有用、有趣、及时或相关。",
  "methods_zh": "中文方法说明。",
  "limitations_zh": "中文局限性；如果无法从摘要推断，返回空字符串。",
  "future_work_zh": "中文后续方向；如果无法从摘要推断，返回空字符串。",
  "abstract_translation_zh": "忠实、流畅的中文摘要翻译。"
}}

Style requirements:
- The report should be mainly Chinese.
- For technical terms, use Chinese first and put English in parentheses when useful.
- Examples: 中等质量黑洞（intermediate-mass black hole）, 活动星系核（AGN）, 引力透镜（gravitational lensing）.
- Avoid hype and avoid random Chinese-English mixing.
- If a field cannot be inferred from the title and abstract, return an empty string.
- Return strict valid JSON only. No Markdown. No code fences. No commentary.
""".strip()
        raw = self.llm.complete(self.system_prompt, user_prompt)
        data = extract_json(raw)
        if not isinstance(data, dict):
            raise ValueError("Summary response must be a JSON object")
        summary = PaperSummary(
            one_sentence=str(data.get("one_sentence_summary_zh", "")).strip(),
            detailed_summary=str(data.get("abstract_translation_zh", "")).strip(),
            key_contribution=str(data.get("key_contribution_zh", "")).strip(),
            why_read=str(data.get("why_read_zh", "")).strip(),
            methods=str(data.get("methods_zh", "")).strip(),
            limitations=str(data.get("limitations_zh", "")).strip(),
            future_work=str(data.get("future_work_zh", "")).strip(),
            abstract_translation=str(data.get("abstract_translation_zh", "")).strip(),
        )
        fallback = self._fallback_summary(ranked)
        return PaperSummary(
            one_sentence=summary.one_sentence or fallback.one_sentence,
            detailed_summary=summary.detailed_summary or fallback.detailed_summary,
            key_contribution=summary.key_contribution or fallback.key_contribution,
            why_read=summary.why_read or fallback.why_read,
            methods=summary.methods or fallback.methods,
            limitations=summary.limitations,
            future_work=summary.future_work,
            abstract_translation=summary.abstract_translation or fallback.abstract_translation,
        )

    def _fallback_summary(self, ranked: RankedPaper) -> PaperSummary:
        paper = ranked.paper
        abstract = paper.abstract.strip()
        title = paper.title.strip()
        short_abstract = shorten(abstract, width=260, placeholder="...") if abstract else ""
        topic_hint = _topic_hint(title, abstract)
        one_sentence = (
            f"本文围绕{topic_hint}展开研究，并提供了可进一步阅读的观测或理论线索。"
            if topic_hint
            else f"本文研究“{title}”所描述的问题，并提供了新的分析结果。"
        )
        key_contribution = (
            f"根据摘要，这篇论文的主要贡献是围绕{topic_hint}给出新的数据、分析或解释框架。"
            if topic_hint
            else "根据标题和摘要，这篇论文提供了新的研究结果，值得结合原文进一步判断其贡献。"
        )
        why_read = (
            f"这篇论文值得阅读，因为它与{topic_hint}相关，并且摘要显示作者试图回答一个具体的科学问题。"
            if topic_hint
            else "这篇论文值得快速浏览，因为它是目标日期内抓取到的相关研究，可能包含新的样本、方法或解释。"
        )
        methods = _rough_methods_zh(abstract)
        abstract_translation = (
            f"基于原文摘要的中文概述：{short_abstract}"
            if short_abstract
            else "摘要原文为空，无法生成中文概述。"
        )
        return PaperSummary(
            one_sentence=one_sentence,
            detailed_summary=abstract_translation,
            key_contribution=key_contribution,
            why_read=why_read,
            methods=methods,
            limitations="",
            future_work="",
            abstract_translation=abstract_translation,
        )


def _topic_hint(title: str, abstract: str) -> str:
    text = f"{title} {abstract}".casefold()
    topics = [
        ("活动星系核（AGN）", ["agn", "active galactic nucleus", "active galactic nuclei"]),
        ("中等质量黑洞（intermediate-mass black hole）", ["intermediate-mass black hole", "imbh"]),
        ("黑洞（black holes）", ["black hole", "black holes"]),
        ("矮星系（dwarf galaxies）", ["dwarf galaxy", "dwarf galaxies"]),
        ("星系演化（galaxy evolution）", ["galaxy evolution"]),
        ("JWST 观测", ["jwst", "james webb"]),
        ("MUSE 积分场观测", ["muse"]),
        ("引力透镜（gravitational lensing）", ["lensing", "gravitational lens"]),
    ]
    matches = [label for label, keys in topics if any(key in text for key in keys)]
    return "、".join(matches[:3])


def _rough_methods_zh(abstract: str) -> str:
    text = abstract.casefold()
    methods = []
    if any(word in text for word in ["spectra", "spectroscopy", "spectroscopic"]):
        methods.append("光谱分析")
    if any(word in text for word in ["imaging", "photometry", "photometric"]):
        methods.append("成像或测光分析")
    if any(word in text for word in ["simulation", "simulations"]):
        methods.append("数值模拟")
    if any(word in text for word in ["model", "modeling", "modelling"]):
        methods.append("模型拟合或理论建模")
    if any(word in text for word in ["survey", "sample", "catalog"]):
        methods.append("样本或巡天数据分析")
    if methods:
        return "根据摘要，论文可能使用了" + "、".join(methods) + "。"
    return "根据摘要，论文主要基于原文所述的数据和分析流程展开研究。"

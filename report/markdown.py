from __future__ import annotations

from pathlib import Path

from utils.models import Briefing, PaperSummary, RankedPaper


class MarkdownReportBuilder:
    def build(self, briefing: Briefing) -> str:
        lines: list[str] = [f"# 天文论文日报（文章日期：{briefing.target_date.isoformat()}）"]

        self._append_section(lines, "## 该日最值得读")
        must_read = briefing.must_read[:3]
        lines.extend(self._paper_sections(must_read, start_index=1))

        self._append_section(lines, "## 推荐阅读")
        lines.extend(self._paper_sections(briefing.recommended, start_index=len(must_read) + 1))

        self._append_section(lines, "## 该日趋势")
        lines.extend(self._bullet_list(briefing.research_trends, "该日论文数量不足，暂时无法判断稳定趋势。"))

        self._append_section(lines, "## 可以关注的问题")
        lines.extend(self._bullet_list(briefing.open_questions, "本期暂无可进一步追踪的问题。"))

        return _clean_blank_lines(lines)

    def save(self, markdown: str, output_dir: str | Path, filename: str) -> Path:
        path = Path(output_dir)
        path.mkdir(parents=True, exist_ok=True)
        output_path = path / filename
        output_path.write_text(markdown, encoding="utf-8")
        return output_path

    def _paper_sections(
        self,
        items: list[tuple[RankedPaper, PaperSummary]],
        start_index: int,
    ) -> list[str]:
        if not items:
            return ["_暂无。_"]

        lines: list[str] = []
        for offset, (ranked, summary) in enumerate(items):
            paper = ranked.paper
            stars = _score_to_stars(ranked.interest_score)
            number = f"{start_index + offset:02d}"
            why_read = summary.why_read or ranked.reason
            lines.extend(["", f"### {number}. {stars} 一句话总结", _clean_text(summary.one_sentence)])
            lines.extend(["", "## English Title", paper.title])
            lines.extend(_optional_section("### 主要贡献", summary.key_contribution))
            lines.extend(_optional_section("### 为什么值得读", why_read))
            lines.extend(_optional_section("### 方法", summary.methods))
            lines.extend(_optional_section("### 局限性", summary.limitations))
            lines.extend(_optional_section("### 后续方向", summary.future_work))
            lines.extend(_optional_section("### 摘要原文", paper.abstract))
            lines.extend(_optional_section("### 摘要中文翻译", summary.abstract_translation))
            lines.extend(
                [
                    "",
                    "### 文章信息",
                    f"- Authors: {', '.join(paper.authors) or 'Unknown'}",
                    f"- Source: {paper.journal or paper.source}",
                    f"- URL: {paper.url}",
                    f"- PDF: {paper.pdf_url or 'N/A'}",
                ]
            )
        return lines

    def _append_section(self, lines: list[str], heading: str) -> None:
        lines.append("")
        lines.append(heading)

    def _bullet_list(self, items: list[str], empty_text: str) -> list[str]:
        if not items:
            return [f"- {empty_text}"]
        return [f"- {item}" for item in items]


def _score_to_stars(score: int) -> str:
    if score >= 90:
        return "⭐⭐⭐⭐⭐"
    if score >= 75:
        return "⭐⭐⭐⭐"
    if score >= 60:
        return "⭐⭐⭐"
    if score >= 40:
        return "⭐⭐"
    return "⭐"


def _optional_section(heading: str, value: str) -> list[str]:
    value = _clean_text(value)
    if not value:
        return []
    return ["", heading, value]


def _clean_text(value: str) -> str:
    return " ".join(value.split())


def _clean_blank_lines(lines: list[str]) -> str:
    # Keep one blank line between Markdown blocks while avoiding accidental gaps.
    cleaned: list[str] = []
    previous_blank = False
    for line in lines:
        blank = not line.strip()
        if blank and previous_blank:
            continue
        cleaned.append(line.rstrip())
        previous_blank = blank
    return "\n".join(cleaned).strip() + "\n"

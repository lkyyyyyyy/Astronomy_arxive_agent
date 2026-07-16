from __future__ import annotations

import argparse
from collections import Counter
from datetime import date, timedelta
import json
import logging
from pathlib import Path

from config.loader import Config, load_config
from delivery.base import DeliveryContext
from delivery.factory import build_delivery_channels
from llm.providers import build_llm_client
from ranking.ranker import PaperRanker
from report.html_report import HtmlReportBuilder
from report.markdown import MarkdownReportBuilder
from sources.factory import build_sources
from summarizer.summarizer import PaperSummarizer
from utils.dates import parse_date
from utils.dedupe import dedupe_papers
from utils.logging import setup_logging
from utils.models import Briefing, Paper, RankedPaper

LOGGER = logging.getLogger(__name__)


def main() -> None:
    setup_logging()
    args = parse_args()
    config_path = resolve_config_path(args.config)
    config = load_config(config_path)
    requested_date = parse_date(args.date, config.app.timezone)

    LOGGER.info("Starting AI Research Daily Agent for requested date %s", requested_date)
    target_date, papers = collect_papers_with_fallback(config, requested_date)
    if target_date != requested_date:
        LOGGER.info(
            "Using %s as the report paper date because %s had no fetched papers.",
            target_date,
            requested_date,
        )
    ranked = rank_papers(config, papers)
    selected = select_papers(ranked, config.app.max_selected)
    briefing = build_briefing(config, target_date, selected, papers)

    markdown_builder = MarkdownReportBuilder()
    markdown = markdown_builder.build(briefing)
    markdown_filename = f"briefing-{target_date.isoformat()}.md"
    markdown_path = markdown_builder.save(
        markdown,
        config.app.output_dir,
        markdown_filename,
    )
    LOGGER.info("Markdown report written to %s", markdown_path)

    html_builder = HtmlReportBuilder()
    html = html_builder.build(briefing)
    html_filename = f"briefing-{target_date.isoformat()}.html"
    html_path = html_builder.save(html, config.app.output_dir, html_filename)
    LOGGER.info("HTML report written to %s", html_path)

    site_path = publish_site_report(config, html, html_filename)
    delivery_errors = 0

    if args.no_delivery or (args.skip_delivery_if_empty and not papers):
        if args.no_delivery:
            LOGGER.info("Delivery skipped because --no-delivery was set.")
        else:
            LOGGER.warning("Delivery skipped because no papers were fetched.")
        write_run_summary(
            args.summary_json,
            target_date,
            len(papers),
            len(selected),
            markdown_path,
            html_path,
            site_path,
            delivery_errors,
        )
        return

    title = f"天文论文日报（文章日期：{target_date.isoformat()}）"
    delivery_context = DeliveryContext(
        markdown=markdown,
        markdown_path=markdown_path,
        html_path=html_path,
        total_fetched=len(papers),
        selected_papers=selected,
        public_url=config.site.public_url,
    )
    for channel in build_delivery_channels(config.delivery):
        try:
            channel.send(title, delivery_context)
        except Exception as exc:
            delivery_errors += 1
            LOGGER.error("Delivery failed for %s: %s", channel.__class__.__name__, exc)

    write_run_summary(
        args.summary_json,
        target_date,
        len(papers),
        len(selected),
        markdown_path,
        html_path,
        site_path,
        delivery_errors,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="AI Research Daily Agent")
    parser.add_argument(
        "--config",
        default="config/config.yaml",
        help="Path to YAML config. Falls back to config.example.yaml if missing.",
    )
    parser.add_argument(
        "--date",
        default=None,
        help="Target publication date in YYYY-MM-DD. Defaults to previous day.",
    )
    parser.add_argument(
        "--no-delivery",
        action="store_true",
        help="Generate the report but do not send it.",
    )
    parser.add_argument(
        "--skip-delivery-if-empty",
        action="store_true",
        help="For scheduled runs, avoid sending an empty briefing when all sources fail.",
    )
    parser.add_argument(
        "--summary-json",
        default=None,
        help="Optional path for a small machine-readable run summary.",
    )
    return parser.parse_args()


def resolve_config_path(path: str) -> Path:
    requested = Path(path)
    if requested.exists():
        return requested
    root_config = Path("config.yaml")
    if root_config.exists():
        LOGGER.warning("Config %s not found; using %s", requested, root_config)
        return root_config
    nested_config = Path("config/config.yaml")
    if nested_config.exists():
        LOGGER.warning("Config %s not found; using %s", requested, nested_config)
        return nested_config
    fallback = Path("config.example.yaml")
    if fallback.exists():
        LOGGER.warning("Config %s not found; using %s", requested, fallback)
        return fallback
    raise FileNotFoundError(f"Config file not found: {requested}")


def collect_papers(config: Config, target_date: date) -> list[Paper]:
    papers: list[Paper] = []
    sources = build_sources(config.sources)
    if not sources:
        LOGGER.warning("No sources are enabled.")
        return []

    for source in sources:
        try:
            papers.extend(source.fetch(target_date, config.topics))
        except Exception as exc:
            LOGGER.error("Source %s failed: %s", source.name, exc)

    unique = dedupe_papers(papers)
    if len(unique) != len(papers):
        LOGGER.info("Removed %d duplicate item(s).", len(papers) - len(unique))
    return unique[: config.app.max_items]


def collect_papers_with_fallback(config: Config, requested_date: date) -> tuple[date, list[Paper]]:
    fallback_days = max(0, int(config.app.fallback_days))
    for offset in range(fallback_days + 1):
        candidate_date = requested_date - timedelta(days=offset)
        papers = collect_papers(config, candidate_date)
        if papers:
            return candidate_date, papers
        if offset < fallback_days:
            LOGGER.info("No papers fetched for %s; trying previous day.", candidate_date)
    return requested_date, []


def publish_site_report(config: Config, html: str, html_filename: str) -> Path | None:
    if not config.site.enabled:
        return None

    site_dir = Path(config.site.output_dir)
    archive_dir = site_dir / config.site.archive_dir
    site_dir.mkdir(parents=True, exist_ok=True)
    archive_dir.mkdir(parents=True, exist_ok=True)
    (site_dir / ".nojekyll").write_text("", encoding="utf-8")

    latest_path = site_dir / config.site.latest_filename
    archive_path = archive_dir / html_filename
    latest_path.write_text(html, encoding="utf-8")
    archive_path.write_text(html, encoding="utf-8")
    LOGGER.info("GitHub Pages site report written to %s", latest_path)
    return latest_path


def write_run_summary(
    path: str | None,
    target_date: date,
    total_fetched: int,
    selected_count: int,
    markdown_path: Path,
    html_path: Path,
    site_path: Path | None,
    delivery_errors: int,
) -> None:
    if not path:
        return
    summary_path = Path(path)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "target_date": target_date.isoformat(),
        "total_fetched": total_fetched,
        "selected_count": selected_count,
        "markdown_path": str(markdown_path),
        "html_path": str(html_path),
        "site_path": str(site_path) if site_path else "",
        "delivery_errors": delivery_errors,
    }
    summary_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def rank_papers(config: Config, papers: list[Paper]) -> list[RankedPaper]:
    llm = build_llm_client(config.llm)
    ranker = PaperRanker(
        llm=llm,
        language=config.app.language,
        system_prompt=config.llm.system_prompt,
    )
    return ranker.rank(papers, config.topics)


def select_papers(ranked: list[RankedPaper], max_selected: int) -> list[RankedPaper]:
    if not ranked:
        return []

    priority = [item for item in ranked if _is_priority_source(item.paper)]
    selected: list[RankedPaper] = []
    seen_urls: set[str] = set()

    for item in priority + ranked:
        if item.paper.url in seen_urls:
            continue
        selected.append(item)
        seen_urls.add(item.paper.url)
        if len(selected) >= max_selected:
            break

    return selected


def build_briefing(
    config: Config,
    target_date: date,
    selected: list[RankedPaper],
    all_papers: list[Paper],
) -> Briefing:
    summarizer = PaperSummarizer(
        llm=build_llm_client(config.llm),
        language=config.app.language,
        system_prompt=config.llm.system_prompt,
    )
    summaries = summarizer.summarize(selected)
    paired = [(item, summaries[item.paper.url]) for item in selected]
    must_read_count = min(3, len(paired))

    return Briefing(
        target_date=target_date,
        highlights=_build_highlights(selected),
        must_read=paired[:must_read_count],
        recommended=paired[must_read_count:],
        research_trends=_build_research_trends(all_papers, config.topics),
        open_questions=_build_open_questions(selected),
    )


def _is_priority_source(paper: Paper) -> bool:
    text = f"{paper.source} {paper.journal or ''}".casefold()
    return any(name in text for name in ["nature", "science"])


def _build_highlights(selected: list[RankedPaper]) -> list[str]:
    highlights = []
    for item in selected[:5]:
        highlights.append(
            f"{item.paper.title} ({item.interest_score}/100): {item.reason}"
        )
    return highlights


def _build_research_trends(papers: list[Paper], topics: list[str]) -> list[str]:
    paper_date = papers[0].published_date.isoformat() if papers else ""
    total = len(papers)
    if not papers:
        return ["本期共抓取到 0 篇论文，暂时无法判断主题趋势。"]

    counter: Counter[str] = Counter()
    for paper in papers:
        haystack = f"{paper.title} {paper.abstract}".casefold()
        for topic in topics:
            if _topic_matches(topic, haystack):
                counter[_topic_label(topic)] += 1

    trends = [f"本期文章日期为 {paper_date}，共抓取到 {total} 篇论文。"]
    if not counter:
        trends.append("这些论文的主题较分散，暂时没有形成明显的配置关键词热点。")
        return trends
    trends.extend(
        f"在 {paper_date} 的 arXiv 论文中，{topic}相关论文共有 {count} 篇。"
        for topic, count in counter.most_common(6)
    )
    return trends


def _topic_matches(topic: str, haystack: str) -> bool:
    topic_key = topic.casefold()
    aliases = {
        "agn": ["agn", "active galactic nucleus", "active galactic nuclei"],
        "black holes": ["black hole", "black holes"],
        "intermediate-mass black holes": [
            "intermediate-mass black hole",
            "intermediate mass black hole",
            "imbh",
        ],
        "dwarf galaxies": ["dwarf galaxy", "dwarf galaxies"],
        "galaxy evolution": ["galaxy evolution"],
        "jwst": ["jwst", "james webb"],
        "muse": ["muse"],
        "lensing": ["lensing", "gravitational lens"],
    }
    keys = aliases.get(topic_key, [topic_key])
    return any(key in haystack for key in keys)


def _topic_label(topic: str) -> str:
    labels = {
        "agn": "活动星系核（AGN）",
        "black holes": "黑洞（black holes）",
        "intermediate-mass black holes": "中等质量黑洞（intermediate-mass black holes）",
        "dwarf galaxies": "矮星系（dwarf galaxies）",
        "galaxy evolution": "星系演化（galaxy evolution）",
        "jwst": "JWST",
        "muse": "MUSE",
        "lensing": "引力透镜（gravitational lensing）",
    }
    return labels.get(topic.casefold(), f"{topic}")


def _build_open_questions(selected: list[RankedPaper]) -> list[str]:
    if not selected:
        return []
    return [
        "这些结果中，哪些已经足够可靠，可以影响近期的观测申请、样本选择或模型设定？",
        "是否有论文给出了值得继续跟踪的目标源、公开数据集、仪器配置或后续观测线索？",
        "这些结论与近期同领域结果是否存在张力，例如样本选择、测量方法或物理解释上的差异？",
    ]


if __name__ == "__main__":
    main()

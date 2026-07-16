from __future__ import annotations

import base64
from io import BytesIO
from html import escape
from pathlib import Path
import random
import re

from utils.dates import format_beijing_window
from utils.models import Briefing, PaperSummary, RankedPaper


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPO_IMAGE_POOL = [
    PROJECT_ROOT / "assets/astronomy/astronomy-01.jpg",
    PROJECT_ROOT / "assets/astronomy/astronomy-02.jpg",
    PROJECT_ROOT / "assets/astronomy/astronomy-03.jpg",
    PROJECT_ROOT / "assets/astronomy/astronomy-04.jpg",
    PROJECT_ROOT / "assets/astronomy/astronomy-05.jpg",
    PROJECT_ROOT / "assets/astronomy/astronomy-06.jpg",
    PROJECT_ROOT / "assets/astronomy/astronomy-07.jpg",
    PROJECT_ROOT / "assets/astronomy/astronomy-08.jpg",
    PROJECT_ROOT / "assets/astronomy/astronomy-09.jpg",
    PROJECT_ROOT / "assets/astronomy/astronomy-10.jpg",
]

ASTRONOMY_IMAGE_POOL = [
    *REPO_IMAGE_POOL,
    Path("/Users/lky/Desktop/图片/酷炫天文图片/gsfc-20171208-archive-e001885orig.jpg"),
    Path("/Users/lky/Desktop/图片/酷炫天文图片/potw2129a.jpg"),
    Path("/Users/lky/Desktop/图片/酷炫天文图片/stephan_quintet~large.jpg"),
    Path("/Users/lky/Desktop/图片/酷炫天文图片/52303461859_0db4d9b739_o.png"),
    Path("/Users/lky/Desktop/图片/酷炫天文图片/cena-wide.jpg"),
    Path("/Users/lky/Desktop/图片/酷炫天文图片/stsci-01gfnn3pwjmy4rqxkz585bc4qh.png"),
    Path("/Users/lky/Desktop/图片/酷炫天文图片/helix.jpg"),
    Path("/Users/lky/Desktop/图片/酷炫天文图片/x25th-casa.jpg"),
    Path("/Users/lky/Desktop/图片/酷炫天文图片/timelapse-crab-nebula.jpg"),
    Path("/Users/lky/Desktop/图片/酷炫天文图片/55062198784-290b7ea74c-o.png"),
]


class HtmlReportBuilder:
    def build(self, briefing: Briefing) -> str:
        must_read = briefing.must_read
        recommended = briefing.recommended
        all_items = must_read + recommended
        report_title = _report_title(briefing)

        return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(report_title)}</title>
  <style>
{_css()}
  </style>
  <script>
    window.MathJax = {{
      tex: {{
        inlineMath: [["$", "$"], ["\\\\(", "\\\\)"]],
        displayMath: [["$$", "$$"], ["\\\\[", "\\\\]"]],
        processEscapes: true
      }},
      options: {{
        skipHtmlTags: ["script", "noscript", "style", "textarea", "pre", "code"]
      }}
    }};
  </script>
  <script defer src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-chtml.js"></script>
</head>
<body{_theme_image_style()}>
  <main class="page-shell">
    <header class="hero">
      <div class="hero-content">
        <p class="subtitle">ASTRONOMY RESEARCH DAILY</p>
        <h1>天文论文<span class="title-gradient">日报</span><span class="title-cutoff">（本期：{_window_label(briefing)}）</span></h1>
        <p class="hero-tagline">探索宇宙 · 追踪前沿 · 启发研究</p>
      </div>
      <div class="hero-grid">
        {_stat_tile("本期抓取论文数", str(_total_fetched(briefing)))}
        {_stat_tile("入选推荐论文数", str(len(all_items)))}
        {_stat_tile("最高推荐等级", _highest_rating(all_items))}
        {_stat_tile("主要趋势关键词", _main_trend_keyword(briefing))}
      </div>
    </header>

    <section id="trends" class="trend-dashboard" aria-label="本期趋势">
      <div class="section-heading">
        <p class="section-kicker">Signals</p>
        <h2>本期趋势</h2>
        <p class="section-note">基于 {_window_label(briefing)} 的全部天体物理论文统计，共 {_total_fetched(briefing)} 篇。</p>
      </div>
      {_trend_widgets(briefing.research_trends)}
    </section>

    <div class="dashboard-layout" id="dashboard-layout">
      <aside class="dashboard-sidebar">
        <button class="sidebar-toggle" id="sidebar-toggle" type="button" aria-label="折叠或展开论文目录" aria-expanded="true">
          <span>目录</span>
        </button>
        {_toc(all_items)}
      </aside>
      <div class="paper-column">
        <section id="must-read" class="section">
          <div class="section-heading">
            <p class="section-kicker">Your interests</p>
            <h2>你感兴趣的文章</h2>
          </div>
          {_paper_cards(must_read, start_index=1)}
        </section>

        <section id="recommended" class="section">
          <div class="section-heading">
            <p class="section-kicker">Recommended</p>
            <h2>推荐阅读</h2>
          </div>
          {_paper_cards(recommended, start_index=len(must_read) + 1)}
        </section>
      </div>
    </div>

    <section class="section">
      <article class="panel questions-panel">
        <p class="section-kicker">Questions</p>
        <h2>可以关注的问题</h2>
        {_list_block(briefing.open_questions, "今天暂无可进一步追踪的问题。")}
      </article>
    </section>
  </main>
  <script>
{_interaction_script()}
  </script>
</body>
</html>
"""

    def save(self, html: str, output_dir: str | Path, filename: str) -> Path:
        path = Path(output_dir)
        path.mkdir(parents=True, exist_ok=True)
        output_path = path / filename
        output_path.write_text(html, encoding="utf-8")
        return output_path


def _report_title(briefing: Briefing) -> str:
    return f"天文论文日报（本期：{_window_label(briefing)}）"


def _window_label(briefing: Briefing) -> str:
    label = format_beijing_window(briefing.window_start, briefing.window_end)
    if label:
        return label
    return f"{briefing.target_date.isoformat()} 08:00 至次日 08:00，北京时间"


def _stat_tile(label: str, value: str) -> str:
    return f"""
        <div class="hero-tile">
          <span class="tile-label">{escape(label)}</span>
          <strong>{escape(value)}</strong>
        </div>
"""


def _total_fetched(briefing: Briefing) -> int:
    for trend in briefing.research_trends:
        match = re.search(r"抓取到\s*(\d+)\s*篇", trend)
        if match:
            return int(match.group(1))
    return len(briefing.must_read) + len(briefing.recommended)


def _highest_rating(items: list[tuple[RankedPaper, PaperSummary]]) -> str:
    if not items:
        return "暂无"
    return _score_to_stars(max(ranked.interest_score for ranked, _ in items))


def _main_trend_keyword(briefing: Briefing) -> str:
    for trend in briefing.research_trends:
        match = re.search(r"，(.+?)相关论文", trend)
        if match:
            return match.group(1)
    return "待观察"


def _trend_widgets(trends: list[str]) -> str:
    items = _parse_trend_items(trends)
    if not items:
        items = [("待观察", 0)]
    max_count = max((count for _, count in items), default=1) or 1
    widgets = []
    for label, count in items[:5]:
        angle = 36 + int((count / max_count) * 282) if count else 42
        widgets.append(
            f"""
        <article class="trend-widget">
          <div class="trend-ring" style="--angle: {angle}deg;">
            <span>{count}</span>
          </div>
          <p>{escape(label)}</p>
        </article>
"""
        )
    return f'<div class="trend-grid">{"".join(widgets)}</div>'


def _parse_trend_items(trends: list[str]) -> list[tuple[str, int]]:
    items: list[tuple[str, int]] = []
    for trend in trends:
        match = re.search(r"，(.+?)相关论文共有\s*(\d+)\s*篇", trend)
        if not match:
            continue
        items.append((_trend_display_label(match.group(1)), int(match.group(2))))
    return items


def _trend_display_label(label: str) -> str:
    normalized = label.casefold()
    mapping = {
        "活动星系核（agn）": "AGN",
        "黑洞（black holes）": "Black Holes",
        "中等质量黑洞（intermediate-mass black holes）": "IMBH",
        "星系演化（galaxy evolution）": "Galaxy Evolution",
        "矮星系（dwarf galaxies）": "Dwarf Galaxies",
        "引力透镜（gravitational lensing）": "Gravitational Lensing",
        "jwst": "JWST",
        "muse": "MUSE",
    }
    return mapping.get(normalized, label)


def _select_theme_images(count: int = 2) -> list[Path]:
    existing = [path for path in ASTRONOMY_IMAGE_POOL if path.exists()]
    if not existing:
        return []
    return random.sample(existing, k=min(count, len(existing)))


def _theme_image_style() -> str:
    image_uris = _select_theme_image_uris()
    hero_uri = image_uris[0] if image_uris else ""
    page_uri = image_uris[1] if len(image_uris) > 1 else hero_uri
    declarations = []
    if hero_uri:
        declarations.append(f"--hero-image: url({hero_uri});")
    if page_uri:
        declarations.append(f"--page-image: url({page_uri});")
    if not declarations:
        return ""
    return f' style="{" ".join(declarations)}"'


def _select_theme_image_uris(count: int = 2) -> list[str]:
    paths = _select_theme_images(len(ASTRONOMY_IMAGE_POOL))
    uris: list[str] = []
    for path in paths:
        max_size = 1500 if not uris else 1800
        quality = 82 if not uris else 70
        uri = _image_data_uri(path, max_size=max_size, quality=quality)
        if uri:
            uris.append(uri)
        if len(uris) >= count:
            break
    return uris


def _image_data_uri(path: Path, max_size: int, quality: int) -> str:
    try:
        from PIL import Image

        with Image.open(path) as image:
            image.thumbnail((max_size, max_size))
            if image.mode in {"RGBA", "LA"}:
                background = Image.new("RGB", image.size, (3, 7, 18))
                background.paste(image, mask=image.getchannel("A"))
                image = background
            else:
                image = image.convert("RGB")
            buffer = BytesIO()
            image.save(buffer, format="JPEG", quality=quality, optimize=True)
            encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
            return f"data:image/jpeg;base64,{encoded}"
    except Exception:
        if path.stat().st_size > 5 * 1024 * 1024:
            return ""
        mime = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
        encoded = base64.b64encode(path.read_bytes()).decode("ascii")
        return f"data:{mime};base64,{encoded}"


def _toc(items: list[tuple[RankedPaper, PaperSummary]]) -> str:
    if not items:
        return """
    <nav class="toc" aria-label="论文目录">
      <div class="toc-title">论文目录</div>
      <p class="empty">今天暂无入选论文。</p>
    </nav>
"""

    links = []
    for index, (ranked, _) in enumerate(items, start=1):
        anchor = _paper_anchor(ranked, index)
        links.append(
            f'<a href="#{anchor}" data-paper-link="{anchor}">'
            f'<span>{index:02d}</span>{escape(ranked.paper.title)}</a>'
        )
    return f"""
    <nav class="toc" aria-label="论文目录">
      <div class="toc-title">论文目录</div>
      <div class="toc-links">
        {"".join(links)}
      </div>
    </nav>
"""


def _paper_cards(
    items: list[tuple[RankedPaper, PaperSummary]],
    start_index: int,
) -> str:
    if not items:
        return '<p class="empty">暂无。</p>'

    cards = []
    for index, (ranked, summary) in enumerate(items, start=1):
        paper = ranked.paper
        sequence = start_index + index - 1
        anchor = _paper_anchor(ranked, sequence)
        why_read = summary.why_read or ranked.reason
        cards.append(
            f"""
      <article class="paper-card" id="{anchor}">
        <div class="card-topline">
          <span class="sequence-badge">{sequence:02d}</span>
          <span class="stars-badge" aria-label="推荐星级">{_score_to_stars(ranked.interest_score)}</span>
          <span class="source-pill">{escape(paper.journal or paper.source)}</span>
        </div>
        <h2 class="english-title">{escape(paper.title)}</h2>
        <h3>{escape(_clean_text(summary.one_sentence) or paper.title)}</h3>
        {_paper_figure(ranked)}

        <div class="content-grid">
          {_info_block("主要贡献", summary.key_contribution)}
          {_info_block("为什么值得读", why_read)}
          {_info_block("方法", summary.methods)}
          {_info_block("局限性", summary.limitations)}
          {_info_block("后续方向", summary.future_work)}
        </div>

        {_bilingual_abstract_panel(paper.abstract, summary.abstract_translation)}

        <footer class="metadata">
          <div>
            <span class="meta-label">Authors</span>
            <p>{escape(_authors_display(paper.authors))}</p>
          </div>
          <div>
            <span class="meta-label">Source</span>
            <p>{escape(paper.journal or paper.source)}</p>
          </div>
          <div class="button-row">
            {_link_button(paper.url, "Read on arXiv")}
            {_link_button(paper.pdf_url, "Open PDF")}
          </div>
        </footer>
      </article>
"""
        )
    return "".join(cards)


def _paper_figure(ranked: RankedPaper) -> str:
    """Placeholder for future paper-specific figure extraction.

    We intentionally do not reuse decorative astronomy photos inside paper cards:
    those images may imply paper-specific evidence where none was extracted.
    A future implementation can download the PDF or source HTML, identify figures,
    and return an image only when it is clearly associated with this paper.
    """
    return ""


def _info_block(title: str, value: str) -> str:
    value = _clean_text(value)
    if not value:
        return ""
    return f"""
          <section class="info-block">
            <h4>{escape(title)}</h4>
            <p>{escape(value)}</p>
          </section>
"""


def _details_block(title: str, value: str) -> str:
    value = _clean_text(value)
    if not value:
        return ""
    return f"""
          <details class="abstract-block">
            <summary>{escape(title)}</summary>
            <p>{escape(value)}</p>
          </details>
"""


def _bilingual_abstract_panel(original: str, translation: str) -> str:
    original = _clean_text(original)
    translation = _clean_text(translation)
    if not original and not translation:
        return ""

    english_lines = _split_english_abstract(original)
    chinese_lines = _split_chinese_abstract(translation)
    max_lines = max(len(english_lines), len(chinese_lines), 1)
    rows = []
    for index in range(max_lines):
        english = english_lines[index] if index < len(english_lines) else ""
        chinese = chinese_lines[index] if index < len(chinese_lines) else ""
        rows.append(
            f"""
              <div class="abstract-row">
                <p lang="en">{escape(english)}</p>
                <p lang="zh-CN">{escape(chinese)}</p>
              </div>
"""
        )
    return f"""
        <details class="bilingual-abstract">
          <summary>摘要对照阅读</summary>
          <div class="abstract-head">
            <span>Original Abstract</span>
            <span>中文翻译</span>
          </div>
          <div class="abstract-sync">
            {"".join(rows)}
          </div>
        </details>
"""


def _list_block(items: list[str], empty_text: str) -> str:
    safe_items = items or [empty_text]
    lines = "".join(f"<li>{escape(item)}</li>" for item in safe_items)
    return f'<ul class="insight-list">{lines}</ul>'


def _link_button(url: str | None, label: str) -> str:
    if not url:
        return f'<span class="button disabled">{escape(label)}</span>'
    return (
        f'<a class="button" href="{escape(url, quote=True)}" '
        f'target="_blank" rel="noopener noreferrer">{escape(label)}</a>'
    )


def _score_to_stars(score: int) -> str:
    if score >= 90:
        return "★★★★★"
    if score >= 75:
        return "★★★★"
    if score >= 60:
        return "★★★"
    if score >= 40:
        return "★★"
    return "★"


def _clean_text(value: str) -> str:
    return " ".join(value.split())


def _authors_display(authors: list[str]) -> str:
    clean_authors = [author.strip() for author in authors if author.strip()]
    if not clean_authors:
        return "Unknown"
    if len(clean_authors) <= 3:
        return ", ".join(clean_authors)
    return ", ".join(clean_authors[:3]) + " et al."


def _split_english_abstract(value: str) -> list[str]:
    value = _clean_text(value)
    if not value:
        return []
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9$\\])", value)
    return [part.strip() for part in parts if part.strip()]


def _split_chinese_abstract(value: str) -> list[str]:
    value = _clean_text(value)
    if not value:
        return []
    parts = re.split(r"(?<=[。！？；])", value)
    return [part.strip() for part in parts if part.strip()]


def _paper_anchor(ranked: RankedPaper, index: int) -> str:
    title = ranked.paper.title.casefold()
    slug = re.sub(r"[^a-z0-9]+", "-", title).strip("-")
    return f"paper-{index}-{slug[:48] or 'untitled'}"


def _interaction_script() -> str:
    return """
    (() => {
      const layout = document.getElementById("dashboard-layout");
      const toggle = document.getElementById("sidebar-toggle");
      const storageKey = "astro-report-sidebar-collapsed";

      const applyState = (collapsed) => {
        if (!layout || !toggle) return;
        layout.classList.toggle("sidebar-collapsed", collapsed);
        toggle.setAttribute("aria-expanded", String(!collapsed));
      };

      applyState(sessionStorage.getItem(storageKey) === "true");

      if (toggle) {
        toggle.addEventListener("click", () => {
          const collapsed = !layout.classList.contains("sidebar-collapsed");
          sessionStorage.setItem(storageKey, String(collapsed));
          applyState(collapsed);
        });
      }

      const links = Array.from(document.querySelectorAll("[data-paper-link]"));
      const byId = new Map(links.map((link) => [link.dataset.paperLink, link]));
      const observer = new IntersectionObserver((entries) => {
        const visible = entries
          .filter((entry) => entry.isIntersecting)
          .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
        if (!visible) return;
        links.forEach((link) => link.classList.remove("is-current"));
        const active = byId.get(visible.target.id);
        if (active) active.classList.add("is-current");
      }, {
        rootMargin: "-18% 0px -58% 0px",
        threshold: [0.12, 0.28, 0.5]
      });

      document.querySelectorAll(".paper-card[id]").forEach((card) => observer.observe(card));
    })();
"""


def _css() -> str:
    return """
    :root {
      color-scheme: dark;
      --bg: #030712;
      --bg-deep: #050818;
      --card: rgba(8, 18, 38, 0.72);
      --card-strong: rgba(11, 24, 52, 0.82);
      --line: rgba(151, 186, 255, 0.18);
      --line-strong: rgba(128, 202, 255, 0.38);
      --ink: #edf5ff;
      --muted: #a7b5cc;
      --faint: #718097;
      --cyan: #5fd7ff;
      --blue: #6aa3ff;
      --violet: #b79cff;
      --gold: #ffd166;
      --pink: #ff8bd1;
      --glow: 0 0 34px rgba(103, 232, 249, 0.14), 0 24px 80px rgba(0, 0, 0, 0.35);
      --title-font: "Avenir Next", "Inter", "Helvetica Neue", Arial, sans-serif;
      --body-font: "PingFang SC", "Microsoft YaHei", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }

    * {
      box-sizing: border-box;
    }

    html {
      scroll-behavior: smooth;
    }

    body {
      margin: 0;
      min-height: 100vh;
      font-family: var(--body-font);
      color: var(--ink);
      background:
        radial-gradient(circle at 18% 8%, rgba(95, 215, 255, 0.12), transparent 20rem),
        radial-gradient(circle at 82% 12%, rgba(106, 163, 255, 0.10), transparent 24rem),
        radial-gradient(circle at 52% 58%, rgba(41, 121, 255, 0.08), transparent 30rem),
        linear-gradient(180deg, #02040d 0%, var(--bg-deep) 42%, #060816 100%);
      line-height: 1.68;
      overflow-x: hidden;
    }

    body::before,
    body::after {
      content: "";
      position: fixed;
      inset: 0;
      pointer-events: none;
      z-index: -2;
    }

    body::before {
      background-image:
        radial-gradient(circle, rgba(255,255,255,0.82) 0 1px, transparent 1.6px),
        radial-gradient(circle, rgba(151,186,255,0.54) 0 1px, transparent 1.4px),
        radial-gradient(circle, rgba(103,232,249,0.34) 0 1px, transparent 1.2px);
      background-size: 112px 112px, 168px 168px, 236px 236px;
      background-position: 0 0, 34px 62px, 90px 28px;
      opacity: 0.38;
    }

    body::after {
      z-index: -1;
      background:
        linear-gradient(115deg, transparent 0 28%, rgba(103,232,249,0.06) 38%, transparent 49%),
        radial-gradient(ellipse at 50% 0%, rgba(122,167,255,0.15), transparent 46%);
      filter: blur(0.2px);
    }

    a {
      color: inherit;
    }

    .page-shell {
      width: min(1180px, calc(100% - 32px));
      margin: 0 auto;
      padding: 24px 0 64px;
    }

    .hero {
      position: relative;
      min-height: 300px;
      display: flex;
      flex-direction: column;
      justify-content: center;
      padding: 38px 42px;
      border: 1px solid var(--line-strong);
      border-radius: 22px;
      background:
        linear-gradient(105deg, rgba(2, 6, 18, 0.90) 0%, rgba(5, 12, 30, 0.78) 46%, rgba(5, 10, 24, 0.64) 100%),
        radial-gradient(circle at 78% 20%, rgba(95, 215, 255, 0.12), transparent 20rem),
        var(--hero-image, linear-gradient(135deg, rgba(7, 22, 48, 0.88), rgba(5, 10, 24, 0.72)));
      background-size: auto, auto, cover;
      background-position: center, center, center;
      box-shadow: var(--glow);
      backdrop-filter: blur(22px);
      overflow: hidden;
    }

    .hero::before {
      content: "";
      position: absolute;
      inset: -1px;
      background:
        linear-gradient(90deg, transparent, rgba(103, 232, 249, 0.18), transparent),
        radial-gradient(circle at 20% 30%, rgba(255,255,255,0.14) 0 1px, transparent 1.5px);
      background-size: 100% 100%, 140px 140px;
      opacity: 0.55;
      pointer-events: none;
    }

    .hero > * {
      position: relative;
      z-index: 1;
    }

    .section-kicker,
    .meta-label {
      margin: 0;
      color: var(--cyan);
      font-size: 0.76rem;
      font-weight: 750;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }

    h1,
    h2,
    h3,
    h4,
    p {
      margin-top: 0;
    }

    h1 {
      margin-bottom: 0;
      font-family: var(--title-font);
      font-size: clamp(2.2rem, 6.2vw, 5.4rem);
      font-weight: 820;
      line-height: 1;
      letter-spacing: 0;
      background: linear-gradient(92deg, #ffffff 0%, #bfe9ff 38%, #b79cff 72%, #ffffff 100%);
      -webkit-background-clip: text;
      background-clip: text;
      color: transparent;
      text-shadow: 0 0 28px rgba(95, 215, 255, 0.14);
    }

    .title-cutoff {
      display: block;
      margin-top: 0.16em;
      color: rgba(238, 233, 255, 0.88);
      background: none;
      -webkit-background-clip: initial;
      background-clip: initial;
      font-family: var(--body-font);
      font-size: clamp(1.05rem, 2vw, 1.8rem);
      font-weight: 420;
      line-height: 1.25;
      text-shadow: none;
    }

    .subtitle {
      display: inline-flex;
      width: fit-content;
      margin: 0 0 13px;
      padding: 6px 11px;
      border: 1px solid rgba(103, 232, 249, 0.32);
      border-radius: 999px;
      color: var(--cyan);
      background: rgba(103, 232, 249, 0.08);
      font-family: var(--title-font);
      font-size: 0.74rem;
      font-weight: 760;
      letter-spacing: 0.14em;
      text-transform: uppercase;
    }

    .hero-intro {
      max-width: 760px;
      margin: 18px 0 24px;
      padding-left: 14px;
      border-left: 2px solid rgba(103, 232, 249, 0.62);
      color: #dbeafe;
      font-size: clamp(0.98rem, 1.5vw, 1.1rem);
      letter-spacing: 0.02em;
    }

    .hero-grid {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 12px;
    }

    .hero-tile {
      display: block;
      min-height: 82px;
      padding: 14px;
      border: 1px solid var(--line);
      border-radius: 14px;
      background: linear-gradient(180deg, rgba(255,255,255,0.10), rgba(255,255,255,0.045));
      text-decoration: none;
      box-shadow: inset 0 1px 0 rgba(255,255,255,0.08);
    }

    .tile-label {
      display: block;
      color: var(--muted);
      font-size: 0.78rem;
    }

    .hero-tile strong {
      display: block;
      margin-top: 8px;
      font-family: var(--title-font);
      font-size: clamp(1.2rem, 2.1vw, 1.65rem);
      line-height: 1;
      color: #ffffff;
      text-shadow: 0 0 20px rgba(103, 232, 249, 0.22);
    }

    .toc,
    .panel,
    .paper-card {
      border: 1px solid var(--line);
      border-radius: 24px;
      background: var(--card);
      box-shadow: var(--glow);
      backdrop-filter: blur(20px);
    }

    .toc {
      margin-top: 24px;
      padding: 20px;
      background: rgba(6, 12, 28, 0.70);
    }

    .toc-title,
    .toc h2,
    .section-heading h2,
    .panel h2 {
      margin-bottom: 0;
      font-family: var(--title-font);
      font-size: 1.48rem;
    }

    .toc-title {
      color: #f6f9ff;
      font-size: 0.92rem;
      font-weight: 760;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }

    .toc-links {
      display: grid;
      gap: 10px;
      margin-top: 18px;
    }

    .toc-links a {
      display: flex;
      gap: 12px;
      align-items: baseline;
      padding: 12px 14px;
      border: 1px solid transparent;
      border-radius: 14px;
      color: var(--ink);
      background: rgba(255,255,255,0.045);
      text-decoration: none;
      transition: border-color 160ms ease, background 160ms ease, transform 160ms ease;
    }

    .toc-links a:hover {
      transform: translateY(-1px);
      border-color: rgba(103, 232, 249, 0.28);
      background: rgba(103, 232, 249, 0.09);
    }

    .toc-links span {
      color: var(--cyan);
      font-weight: 800;
    }

    .section {
      margin-top: 48px;
    }

    .section-heading {
      margin-bottom: 20px;
    }

    .section-note {
      margin: 8px 0 0;
      color: rgba(218, 226, 245, 0.72);
      font-size: 0.92rem;
      line-height: 1.55;
    }

    .paper-card {
      position: relative;
      margin-bottom: 26px;
      padding: 32px;
      scroll-margin-top: 24px;
      overflow: hidden;
    }

    .paper-card::before {
      content: "";
      position: absolute;
      inset: 0;
      background: radial-gradient(circle at 88% 12%, rgba(103,232,249,0.16), transparent 18rem);
      pointer-events: none;
    }

    .card-topline {
      position: relative;
      display: flex;
      justify-content: flex-start;
      align-items: center;
      gap: 12px;
      margin-bottom: 22px;
    }

    .sequence-badge,
    .stars-badge {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-height: 36px;
      border-radius: 999px;
      font-weight: 850;
      white-space: nowrap;
      box-shadow: 0 0 22px rgba(103,232,249,0.12);
    }

    .sequence-badge {
      min-width: 48px;
      padding: 4px 13px;
      color: #03111f;
      background: linear-gradient(135deg, var(--cyan), #b79cff);
      letter-spacing: 0.04em;
    }

    .stars-badge {
      padding: 4px 12px;
      color: var(--gold);
      background: rgba(255, 209, 102, 0.10);
      border: 1px solid rgba(255, 209, 102, 0.28);
      font-size: 1.1rem;
      letter-spacing: 0.08em;
    }

    .source-pill {
      padding: 5px 10px;
      border-radius: 999px;
      color: #cfe9ff;
      background: rgba(122, 167, 255, 0.12);
      border: 1px solid rgba(122, 167, 255, 0.22);
      font-size: 0.82rem;
      font-weight: 700;
    }

    .paper-card h3 {
      position: relative;
      max-width: 920px;
      margin-bottom: 18px;
      color: #ffffff;
      font-size: clamp(1.42rem, 2.6vw, 2.15rem);
      line-height: 1.28;
      letter-spacing: 0;
    }

    .english-title {
      position: relative;
      margin-bottom: 26px;
      color: #dbeafe;
      font-family: var(--title-font);
      font-size: clamp(1.55rem, 3vw, 2.55rem);
      font-weight: 780;
      line-height: 1.15;
      letter-spacing: 0;
    }

    .content-grid {
      position: relative;
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 16px;
    }

    .info-block {
      padding: 18px;
      border: 1px solid rgba(151, 186, 255, 0.16);
      border-radius: 18px;
      background: rgba(255,255,255,0.055);
      box-shadow: inset 0 1px 0 rgba(255,255,255,0.06);
    }

    .info-block:first-child {
      grid-column: 1 / -1;
      background: linear-gradient(135deg, rgba(103,232,249,0.10), rgba(183,156,255,0.08));
      border-color: rgba(103,232,249,0.24);
    }

    .abstract-grid {
      position: relative;
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 16px;
      margin-top: 18px;
    }

    .abstract-block {
      border: 1px solid rgba(151, 186, 255, 0.16);
      border-radius: 18px;
      background: rgba(255,255,255,0.045);
      overflow: hidden;
    }

    .abstract-block summary {
      cursor: pointer;
      padding: 15px 18px;
      color: var(--cyan);
      background: rgba(103,232,249,0.07);
      font-weight: 800;
    }

    .abstract-block p {
      margin: 0;
      padding: 16px 18px 18px;
      color: #d3def1;
    }

    .info-block h4 {
      margin-bottom: 8px;
      color: var(--cyan);
      font-size: 1rem;
    }

    .info-block p,
    .metadata p,
    .insight-list {
      margin-bottom: 0;
    }

    .metadata {
      position: relative;
      display: grid;
      grid-template-columns: minmax(0, 2fr) minmax(140px, 0.8fr) auto;
      gap: 18px;
      align-items: end;
      margin-top: 24px;
      padding-top: 18px;
      border-top: 1px solid var(--line);
      color: var(--muted);
      font-size: 0.92rem;
    }

    .button-row {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      justify-content: flex-end;
    }

    .button {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-height: 42px;
      padding: 10px 16px;
      border: 1px solid rgba(103,232,249,0.42);
      border-radius: 12px;
      color: #eaffff;
      background: linear-gradient(135deg, rgba(103,232,249,0.22), rgba(122,167,255,0.18));
      font-weight: 750;
      text-decoration: none;
      white-space: nowrap;
      box-shadow: 0 0 24px rgba(103,232,249,0.16), inset 0 1px 0 rgba(255,255,255,0.10);
      transition: transform 160ms ease, border-color 160ms ease, background 160ms ease;
    }

    .button:hover {
      transform: translateY(-2px);
      border-color: rgba(103,232,249,0.78);
      background: linear-gradient(135deg, rgba(103,232,249,0.34), rgba(183,156,255,0.22));
    }

    .button.disabled {
      color: var(--muted);
      background: rgba(255,255,255,0.06);
      box-shadow: none;
    }

    .two-column {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 20px;
    }

    .panel {
      padding: 26px;
      background: var(--card-strong);
    }

    .insight-list {
      padding-left: 1.2rem;
      color: #d5e2f6;
    }

    .insight-list li + li {
      margin-top: 10px;
    }

    .empty {
      margin: 0;
      color: var(--muted);
    }

    @media (max-width: 820px) {
      .page-shell {
        width: min(100% - 20px, 680px);
        padding-top: 10px;
      }

      .hero,
      .paper-card,
      .toc,
      .panel {
        border-radius: 20px;
      }

      .hero {
        min-height: auto;
        padding: 28px 20px;
      }

      .hero-grid,
      .content-grid,
      .abstract-grid,
      .two-column,
      .metadata {
        grid-template-columns: 1fr;
      }

      .paper-card {
        padding: 22px 18px;
      }

      .card-topline {
        align-items: flex-start;
        flex-wrap: wrap;
      }

      .button-row {
        justify-content: flex-start;
      }

      .button {
        width: 100%;
      }
    }

    /* NASA-style redesign overrides */
    :root {
      --nasa-red: #fc3d21;
      --nasa-blue: #0b3d91;
      --space-black: #02030a;
      --panel-dark: rgba(5, 12, 28, 0.78);
      --panel-soft: rgba(9, 20, 44, 0.64);
      --hairline: rgba(190, 214, 255, 0.16);
      --hairline-bright: rgba(126, 180, 255, 0.34);
      --title-serif: "Songti SC", STSong, "SimSun", "Noto Serif CJK SC", serif;
      --label-sans: "Avenir Next", "Inter", "Helvetica Neue", Arial, sans-serif;
    }

    body {
      background:
        radial-gradient(circle at 18% 10%, rgba(11, 61, 145, 0.28), transparent 24rem),
        radial-gradient(circle at 84% 14%, rgba(130, 87, 255, 0.13), transparent 26rem),
        linear-gradient(180deg, #01020a 0%, #050816 46%, #02030a 100%);
    }

    .page-shell {
      width: min(1240px, calc(100% - 36px));
      padding-top: 28px;
    }

    .hero {
      min-height: 430px;
      display: grid;
      grid-template-columns: minmax(0, 0.95fr) minmax(320px, 0.75fr);
      grid-template-rows: 1fr auto;
      gap: 28px;
      align-items: end;
      padding: 48px;
      border-radius: 26px;
      border-color: rgba(255, 255, 255, 0.16);
      background:
        linear-gradient(90deg, rgba(1, 3, 12, 0.96) 0%, rgba(5, 13, 31, 0.88) 44%, rgba(5, 12, 27, 0.28) 100%),
        var(--hero-image, linear-gradient(135deg, #06122a, #02030a));
      background-size: cover;
      background-position: center;
      box-shadow: 0 28px 90px rgba(0, 0, 0, 0.42);
    }

    .hero::before {
      background:
        linear-gradient(180deg, transparent 0%, rgba(1, 3, 12, 0.26) 56%, rgba(1, 3, 12, 0.84) 100%),
        radial-gradient(circle at 20% 28%, rgba(255, 255, 255, 0.18) 0 1px, transparent 1.6px);
      background-size: auto, 150px 150px;
      opacity: 0.68;
    }

    .hero::after {
      content: "";
      position: absolute;
      top: 0;
      right: 0;
      width: 58%;
      height: 100%;
      background: var(--hero-image, none);
      background-size: cover;
      background-position: center;
      opacity: 0.64;
      filter: saturate(1.05) contrast(1.04);
      mask-image: linear-gradient(90deg, transparent 0%, rgba(0,0,0,0.62) 28%, #000 100%);
      pointer-events: none;
    }

    .hero-content {
      grid-column: 1;
      grid-row: 1;
      max-width: 620px;
    }

    .subtitle,
    .section-kicker,
    .meta-label {
      font-family: var(--label-sans);
      letter-spacing: 0.18em;
    }

    .subtitle {
      margin-bottom: 18px;
      padding: 0;
      border: 0;
      border-radius: 0;
      color: rgba(215, 229, 255, 0.82);
      background: transparent;
      font-size: 0.78rem;
    }

    h1 {
      font-family: var(--title-serif);
      font-size: clamp(3.1rem, 6.6vw, 6.15rem);
      font-weight: 500;
      line-height: 1.03;
      color: #f7fbff;
      background: none;
      text-shadow: 0 0 26px rgba(97, 161, 255, 0.22);
    }

    .hero-tagline {
      margin: 22px 0 0;
      color: rgba(231, 239, 255, 0.88);
      font-size: clamp(1rem, 1.6vw, 1.18rem);
      letter-spacing: 0.08em;
    }

    .hero-grid {
      grid-column: 1 / -1;
      grid-row: 2;
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 12px;
      max-width: 880px;
    }

    .hero-tile {
      min-height: 78px;
      padding: 13px 14px;
      border-radius: 12px;
      background: rgba(4, 10, 24, 0.58);
      border-color: rgba(255, 255, 255, 0.14);
      backdrop-filter: blur(18px);
    }

    .hero-tile strong {
      font-family: var(--label-sans);
      font-size: clamp(1.12rem, 1.8vw, 1.48rem);
    }

    .trend-dashboard {
      margin-top: 34px;
      padding: 28px;
      border: 1px solid var(--hairline);
      border-radius: 22px;
      background: linear-gradient(180deg, rgba(8, 18, 42, 0.74), rgba(4, 9, 22, 0.64));
      box-shadow: 0 22px 70px rgba(0, 0, 0, 0.34);
      backdrop-filter: blur(18px);
    }

    .trend-grid {
      display: grid;
      grid-template-columns: repeat(5, minmax(0, 1fr));
      gap: 18px;
      margin-top: 22px;
    }

    .trend-widget {
      display: grid;
      justify-items: center;
      gap: 12px;
      min-height: 164px;
      padding: 18px 12px 14px;
      border: 1px solid rgba(255, 255, 255, 0.11);
      border-radius: 18px;
      background: rgba(255, 255, 255, 0.045);
    }

    .trend-ring {
      width: 96px;
      height: 96px;
      display: grid;
      place-items: center;
      border-radius: 50%;
      background:
        radial-gradient(circle at center, #071127 0 56%, transparent 57%),
        conic-gradient(var(--nasa-red) var(--angle), rgba(130, 160, 210, 0.16) 0);
      box-shadow: 0 0 32px rgba(252, 61, 33, 0.14);
    }

    .trend-ring span {
      font-family: var(--label-sans);
      color: #ffffff;
      font-size: 1.65rem;
      font-weight: 760;
    }

    .trend-widget p {
      margin: 0;
      color: #dce8ff;
      font-family: var(--label-sans);
      font-size: 0.86rem;
      text-align: center;
      line-height: 1.35;
    }

    .dashboard-layout {
      display: grid;
      grid-template-columns: minmax(220px, 290px) minmax(0, 1fr);
      gap: 24px;
      align-items: start;
      margin-top: 34px;
    }

    .dashboard-sidebar {
      position: relative;
    }

    .toc {
      margin-top: 0;
      padding: 0;
      overflow: hidden;
      background: rgba(5, 12, 28, 0.72);
    }

    .toc-title {
      padding: 18px 20px;
      color: #f6f9ff;
      font-family: var(--label-sans);
      font-size: 0.92rem;
      font-weight: 760;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      border-bottom: 1px solid var(--hairline);
    }

    .toc-links {
      max-height: 72vh;
      overflow: auto;
      padding: 14px;
      margin-top: 0;
    }

    .toc-links a {
      align-items: flex-start;
      color: rgba(233, 241, 255, 0.88);
      background: rgba(255, 255, 255, 0.035);
    }

    .paper-column .section:first-child {
      margin-top: 0;
    }

    .section-heading h2,
    .panel h2,
    .trend-dashboard h2 {
      font-family: var(--title-serif);
      font-weight: 500;
      font-size: clamp(1.7rem, 2.6vw, 2.4rem);
    }

    .paper-card {
      border-radius: 22px;
      background:
        linear-gradient(180deg, rgba(9, 22, 50, 0.78), rgba(5, 10, 24, 0.72));
      border-color: var(--hairline);
      box-shadow: 0 20px 70px rgba(0, 0, 0, 0.36);
    }

    .english-title {
      font-family: var(--title-serif);
      font-weight: 500;
      color: #ffffff;
      font-size: clamp(1.85rem, 3vw, 3rem);
      line-height: 1.12;
    }

    .paper-card h3 {
      color: rgba(219, 234, 254, 0.95);
      font-size: clamp(1.1rem, 1.8vw, 1.45rem);
      font-weight: 520;
    }

    .sequence-badge {
      background: #f7fbff;
      color: #061225;
    }

    .stars-badge {
      color: #ffd166;
      background: rgba(255, 209, 102, 0.08);
    }

    .source-pill {
      color: #eaf2ff;
      background: rgba(11, 61, 145, 0.34);
    }

    .button {
      border-color: rgba(255, 255, 255, 0.22);
      background: linear-gradient(135deg, rgba(11, 61, 145, 0.84), rgba(85, 117, 210, 0.46));
      box-shadow: 0 0 26px rgba(76, 141, 255, 0.16);
    }

    .button:hover {
      border-color: rgba(252, 61, 33, 0.68);
      background: linear-gradient(135deg, rgba(11, 61, 145, 0.95), rgba(252, 61, 33, 0.30));
    }

    .questions-panel {
      max-width: 900px;
      margin-left: auto;
    }

    @media (max-width: 960px) {
      .hero {
        min-height: 390px;
        grid-template-columns: 1fr;
        padding: 34px 24px;
      }

      .hero::after {
        width: 100%;
        opacity: 0.32;
        mask-image: linear-gradient(180deg, rgba(0,0,0,0.65), transparent 100%);
      }

      .hero-grid,
      .trend-grid,
      .dashboard-layout {
        grid-template-columns: 1fr;
      }

      .trend-widget {
        min-height: auto;
      }

      .toc-links {
        max-height: none;
      }
    }

    /* Premium publication pass: purple/blue ESA-NASA editorial system */
    :root {
      --purple: #9b7cff;
      --purple-soft: #c7b7ff;
      --purple-deep: #5d4bff;
      --blue-soft: #7aa7ff;
      --magazine-card: rgba(7, 12, 27, 0.72);
      --magazine-line: rgba(155, 124, 255, 0.22);
      --magazine-line-bright: rgba(199, 183, 255, 0.42);
      --magazine-shadow: 0 18px 58px rgba(0, 0, 0, 0.28);
    }

    html {
      scroll-behavior: smooth;
    }

    body {
      background:
        radial-gradient(circle at 78% 12%, rgba(155, 124, 255, 0.18), transparent 26rem),
        radial-gradient(circle at 18% 18%, rgba(75, 106, 255, 0.14), transparent 24rem),
        linear-gradient(180deg, #02030a 0%, #050713 52%, #02030a 100%);
    }

    .title-gradient {
      background: linear-gradient(110deg, #f4efff 0%, var(--purple-soft) 38%, var(--purple-deep) 100%);
      -webkit-background-clip: text;
      background-clip: text;
      color: transparent;
      text-shadow: 0 0 28px rgba(155, 124, 255, 0.28);
    }

    .subtitle,
    .section-kicker,
    .meta-label {
      color: var(--purple-soft);
    }

    .hero {
      border: 1px solid var(--magazine-line);
      box-shadow: 0 24px 80px rgba(0, 0, 0, 0.32);
    }

    .hero-tile,
    .trend-dashboard,
    .toc,
    .paper-card,
    .panel {
      border: 1px solid var(--magazine-line);
      box-shadow: var(--magazine-shadow);
    }

    .hero-tile {
      background: rgba(10, 14, 32, 0.58);
    }

    .dashboard-layout {
      transition: none;
    }

    .dashboard-sidebar {
      min-width: 0;
      overflow: hidden;
      transition: opacity 240ms ease, transform 240ms ease;
    }

    .sidebar-toggle {
      width: 100%;
      margin-bottom: 12px;
      padding: 10px 14px;
      border: 1px solid var(--magazine-line);
      border-radius: 999px;
      color: #eee9ff;
      background: linear-gradient(135deg, rgba(155, 124, 255, 0.18), rgba(75, 106, 255, 0.10));
      font-family: var(--label-sans);
      font-size: 0.78rem;
      font-weight: 650;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      cursor: pointer;
      transition: border-color 180ms ease, box-shadow 180ms ease, transform 180ms ease;
    }

    .sidebar-toggle:hover {
      border-color: var(--magazine-line-bright);
      box-shadow: 0 0 24px rgba(155, 124, 255, 0.18);
      transform: translateY(-1px);
    }

    .dashboard-layout.sidebar-collapsed {
      grid-template-columns: 68px minmax(0, 1fr);
    }

    .dashboard-layout.sidebar-collapsed .toc {
      opacity: 0;
      transform: translateX(-10px);
      pointer-events: none;
      padding: 0;
      border-width: 0;
      visibility: hidden;
      overflow: hidden;
    }

    .dashboard-layout.sidebar-collapsed .sidebar-toggle span {
      writing-mode: vertical-rl;
      letter-spacing: 0.16em;
    }

    .toc {
      will-change: opacity, transform;
      transition: opacity 180ms ease, transform 180ms ease, visibility 180ms ease;
    }

    .toc-title {
      color: #f6f2ff;
      border-bottom-color: var(--magazine-line);
    }

    .toc-links a {
      border: 1px solid transparent;
      transition: border-color 180ms ease, background 180ms ease, color 180ms ease;
    }

    .toc-links a:hover,
    .toc-links a.is-current {
      color: #ffffff;
      border-color: var(--magazine-line-bright);
      background: rgba(155, 124, 255, 0.13);
    }

    .toc-links a.is-current span {
      color: var(--purple-soft);
    }

    .trend-dashboard {
      background: rgba(5, 9, 22, 0.62);
    }

    .trend-widget {
      border-color: var(--magazine-line);
      background: rgba(255, 255, 255, 0.035);
      box-shadow: none;
    }

    .trend-ring {
      background:
        radial-gradient(circle at center, #070b18 0 57%, transparent 58%),
        conic-gradient(var(--purple-soft) var(--angle), rgba(155, 124, 255, 0.13) 0);
      box-shadow: 0 0 28px rgba(155, 124, 255, 0.16);
    }

    .paper-card {
      padding: 38px;
      border-radius: 30px;
      background:
        linear-gradient(180deg, rgba(12, 18, 38, 0.74), rgba(5, 8, 20, 0.70));
      border-color: var(--magazine-line);
      box-shadow: 0 18px 56px rgba(0, 0, 0, 0.24);
      animation: fadeInUp 520ms ease both;
    }

    .card-topline {
      margin-bottom: 26px;
    }

    .sequence-badge {
      background: linear-gradient(135deg, #ffffff, #dcd3ff);
    }

    .stars-badge {
      border-color: rgba(199, 183, 255, 0.28);
      color: #d9ccff;
      background: rgba(155, 124, 255, 0.09);
    }

    .source-pill {
      border-color: rgba(155, 124, 255, 0.24);
      background: rgba(155, 124, 255, 0.10);
    }

    .english-title {
      margin-bottom: 18px;
      letter-spacing: 0.01em;
    }

    .paper-card h3 {
      max-width: 940px;
      margin-bottom: 30px;
      color: rgba(234, 240, 255, 0.94);
      line-height: 1.75;
    }

    .content-grid {
      gap: 18px;
    }

    .info-block {
      padding: 20px;
      border-radius: 20px;
      border-color: rgba(155, 124, 255, 0.16);
      background: rgba(255, 255, 255, 0.035);
    }

    .info-block:first-child {
      border-color: rgba(199, 183, 255, 0.26);
      background: linear-gradient(135deg, rgba(155, 124, 255, 0.08), rgba(122, 167, 255, 0.05));
    }

    .info-block h4 {
      color: var(--purple-soft);
      font-weight: 560;
    }

    .info-block p,
    .metadata p,
    .abstract-row p,
    .insight-list {
      line-height: 1.82;
    }

    .bilingual-abstract {
      margin-top: 20px;
      border: 1px solid rgba(155, 124, 255, 0.18);
      border-radius: 24px;
      background: rgba(255, 255, 255, 0.035);
      overflow: hidden;
      transition: border-color 180ms ease, background 180ms ease;
    }

    .bilingual-abstract[open] {
      border-color: rgba(199, 183, 255, 0.30);
      background: rgba(255, 255, 255, 0.045);
    }

    .bilingual-abstract summary {
      cursor: pointer;
      padding: 18px 22px;
      color: #f1ecff;
      font-family: var(--label-sans);
      font-size: 0.88rem;
      font-weight: 650;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      border-bottom: 1px solid rgba(155, 124, 255, 0.14);
    }

    .abstract-head,
    .abstract-row {
      display: grid;
      grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
      gap: 22px;
    }

    .abstract-head {
      padding: 18px 22px 0;
      color: var(--purple-soft);
      font-family: var(--label-sans);
      font-size: 0.76rem;
      font-weight: 680;
      letter-spacing: 0.10em;
      text-transform: uppercase;
    }

    .abstract-sync {
      padding: 12px 22px 22px;
    }

    .abstract-row {
      padding: 14px 0;
      border-top: 1px solid rgba(155, 124, 255, 0.10);
    }

    .abstract-row:first-child {
      border-top: 0;
    }

    .abstract-row p {
      margin: 0;
      color: rgba(226, 235, 255, 0.88);
      font-family: Georgia, "Times New Roman", "Songti SC", STSong, serif;
      font-size: 0.98rem;
    }

    .abstract-row p[lang="zh-CN"] {
      color: rgba(240, 238, 255, 0.92);
      font-family: "Songti SC", STSong, "Microsoft YaHei", serif;
    }

    .metadata {
      margin-top: 28px;
      border-top-color: rgba(155, 124, 255, 0.16);
    }

    .button {
      border-radius: 999px;
      border-color: rgba(199, 183, 255, 0.42);
      background: linear-gradient(135deg, rgba(155, 124, 255, 0.82), rgba(88, 111, 255, 0.54));
      box-shadow: 0 0 28px rgba(155, 124, 255, 0.18);
    }

    .button:hover {
      border-color: rgba(226, 214, 255, 0.82);
      background: linear-gradient(135deg, rgba(199, 183, 255, 0.92), rgba(93, 75, 255, 0.66));
      box-shadow: 0 0 34px rgba(155, 124, 255, 0.28);
    }

    body::after {
      z-index: -1;
      background:
        linear-gradient(180deg, rgba(2, 3, 10, 0.72), rgba(2, 3, 10, 0.96)),
        radial-gradient(circle at 82% 8%, rgba(155, 124, 255, 0.18), transparent 28rem),
        var(--page-image, none);
      background-size: auto, auto, cover;
      background-position: center;
      opacity: 0.30;
      filter: saturate(0.92) contrast(1.04) brightness(0.74);
    }

    .hero {
      background:
        linear-gradient(90deg, rgba(2, 3, 10, 0.96) 0%, rgba(5, 10, 24, 0.88) 42%, rgba(5, 10, 24, 0.30) 100%),
        var(--hero-image, linear-gradient(135deg, #06122a, #02030a));
      background-size: cover;
      background-position: center;
    }

    .paper-card,
    .trend-dashboard,
    .toc,
    .panel {
      position: relative;
      background:
        linear-gradient(180deg, rgba(8, 14, 28, 0.74), rgba(5, 8, 18, 0.68));
      border: 1px solid rgba(187, 170, 255, 0.14);
      box-shadow:
        inset 0 1px 0 rgba(255, 255, 255, 0.045),
        inset 0 -18px 42px rgba(122, 167, 255, 0.025),
        0 20px 62px rgba(0, 0, 0, 0.24);
      backdrop-filter: blur(18px);
    }

    .paper-card::after,
    .trend-dashboard::after,
    .toc::after,
    .panel::after {
      content: "";
      position: absolute;
      inset: 0;
      padding: 1px;
      border-radius: inherit;
      background:
        linear-gradient(138deg,
          rgba(199, 183, 255, 0.48),
          rgba(122, 167, 255, 0.08) 32%,
          rgba(95, 215, 255, 0.18) 58%,
          rgba(155, 124, 255, 0.36));
      -webkit-mask:
        linear-gradient(#000 0 0) content-box,
        linear-gradient(#000 0 0);
      -webkit-mask-composite: xor;
      mask-composite: exclude;
      pointer-events: none;
      opacity: 0.72;
    }

    .paper-card {
      border-radius: 34px;
      padding: 42px;
    }

    .info-block,
    .bilingual-abstract,
    .abstract-block {
      background: rgba(8, 14, 28, 0.46);
      border-color: rgba(187, 170, 255, 0.12);
      box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.035);
    }

    .trend-grid {
      grid-template-columns: repeat(5, minmax(0, 1fr));
      gap: 14px;
    }

    .trend-dashboard {
      padding: 24px;
    }

    .trend-widget {
      min-height: 138px;
      padding: 14px 10px 12px;
      background: rgba(8, 14, 28, 0.42);
      border-color: rgba(187, 170, 255, 0.12);
    }

    .trend-ring {
      width: 82px;
      height: 82px;
      background:
        radial-gradient(circle at center, rgba(5, 8, 18, 0.98) 0 57%, transparent 58%),
        conic-gradient(#d7c9ff var(--angle), rgba(155, 124, 255, 0.12) 0);
      box-shadow: 0 0 24px rgba(155, 124, 255, 0.14);
    }

    .trend-ring span {
      font-size: 1.38rem;
      font-weight: 640;
    }

    .trend-widget p {
      font-size: 0.78rem;
      color: rgba(229, 236, 255, 0.86);
    }

    .stars-badge {
      color: transparent;
      background:
        linear-gradient(180deg, #fff8cc 0%, #ffd166 42%, #c9861a 100%);
      -webkit-background-clip: text;
      background-clip: text;
      border-color: rgba(255, 209, 102, 0.18);
      letter-spacing: 0.14em;
      text-shadow:
        0 0 10px rgba(255, 209, 102, 0.32),
        0 0 26px rgba(255, 174, 61, 0.16);
      filter: drop-shadow(0 0 8px rgba(255, 209, 102, 0.16));
      font-family: Georgia, "Times New Roman", serif;
      font-size: 1.05rem;
    }

    .metadata p {
      color: rgba(218, 226, 245, 0.82);
    }

    /* Keep the embedded page image visible above the body paint but behind content. */
    body {
      position: relative;
      isolation: isolate;
      background:
        linear-gradient(180deg, rgba(2, 3, 10, 0.64), rgba(2, 3, 10, 0.88) 42%, rgba(2, 3, 10, 0.96)),
        radial-gradient(circle at 18% 8%, rgba(155, 124, 255, 0.20), transparent 23rem),
        radial-gradient(circle at 84% 18%, rgba(75, 106, 255, 0.16), transparent 27rem),
        var(--page-image, none),
        linear-gradient(180deg, #02030a 0%, #050713 52%, #02030a 100%);
      background-size: auto, auto, auto, cover, auto;
      background-position: center;
      background-attachment: fixed;
    }

    body::before,
    body::after {
      z-index: 0;
    }

    body::before {
      background:
        linear-gradient(180deg, rgba(2, 3, 10, 0.42), rgba(2, 3, 10, 0.78) 48%, rgba(2, 3, 10, 0.92)),
        radial-gradient(circle at 80% 6%, rgba(155, 124, 255, 0.18), transparent 28rem),
        var(--page-image, none);
      background-size: auto, auto, cover;
      background-position: center;
      opacity: 0.62;
      filter: saturate(0.95) contrast(1.06) brightness(0.82);
    }

    body::after {
      background:
        radial-gradient(circle, rgba(255,255,255,0.72) 0 1px, transparent 1.5px),
        radial-gradient(circle, rgba(174, 154, 255, 0.35) 0 1px, transparent 1.4px),
        radial-gradient(ellipse at 50% 0%, rgba(122,167,255,0.12), transparent 46%);
      background-size: 118px 118px, 190px 190px, auto;
      background-position: 0 0, 42px 68px, center;
      opacity: 0.42;
      mix-blend-mode: screen;
    }

    .page-shell {
      position: relative;
      z-index: 1;
    }

    details::details-content {
      block-size: 0;
      overflow: hidden;
      transition: block-size 260ms ease, content-visibility 260ms ease allow-discrete;
    }

    details[open]::details-content {
      block-size: auto;
    }

    .trend-grid {
      grid-template-columns: repeat(auto-fit, minmax(136px, 1fr));
      align-items: stretch;
    }

    .trend-widget {
      min-width: 0;
      overflow: hidden;
    }

    .trend-ring {
      width: clamp(72px, 18vw, 84px);
      height: clamp(72px, 18vw, 84px);
      flex: 0 0 auto;
    }

    @keyframes fadeInUp {
      from {
        opacity: 0;
        transform: translateY(14px);
      }
      to {
        opacity: 1;
        transform: translateY(0);
      }
    }

    @media (max-width: 960px) {
      .dashboard-layout,
      .dashboard-layout.sidebar-collapsed {
        grid-template-columns: 1fr;
      }

      .dashboard-layout.sidebar-collapsed .toc {
        opacity: 1;
        transform: none;
        pointer-events: auto;
        max-height: none;
        padding: 0;
        border-width: 1px;
      }

      .dashboard-layout.sidebar-collapsed .sidebar-toggle span {
        writing-mode: horizontal-tb;
      }

      .abstract-head {
        display: none;
      }

      .abstract-row {
        grid-template-columns: 1fr;
        gap: 10px;
      }

      .trend-grid {
        grid-template-columns: repeat(auto-fit, minmax(118px, 1fr));
        gap: 12px;
      }

      .paper-card {
        padding: 24px 20px;
      }
    }

    @media (max-width: 430px) {
      .trend-grid {
        grid-template-columns: 1fr 1fr;
      }

      .trend-ring {
        width: 68px;
        height: 68px;
      }

      .trend-widget {
        padding: 12px 8px;
      }
    }

    /* Final interaction polish: smoother sidebar and safer small-screen trend widgets. */
    .dashboard-layout {
      grid-template-columns: minmax(0, 300px) minmax(0, 1fr);
      transition: grid-template-columns 260ms cubic-bezier(0.22, 1, 0.36, 1);
    }

    .dashboard-layout.sidebar-collapsed {
      grid-template-columns: 56px minmax(0, 1fr);
    }

    .dashboard-sidebar {
      position: sticky;
      top: 22px;
      align-self: start;
      contain: layout paint;
    }

    .toc {
      transform-origin: left center;
      transition:
        opacity 220ms ease,
        transform 260ms cubic-bezier(0.22, 1, 0.36, 1),
        visibility 220ms ease;
    }

    .dashboard-layout.sidebar-collapsed .toc {
      opacity: 0;
      transform: translateX(-8px) scaleX(0.96);
      pointer-events: none;
      visibility: hidden;
    }

    .trend-grid {
      grid-template-columns: repeat(auto-fit, minmax(136px, 1fr));
    }

    .trend-widget {
      min-width: 0;
    }

    mjx-container {
      color: rgba(240, 238, 255, 0.94);
      overflow-x: auto;
      overflow-y: hidden;
      max-width: 100%;
    }

    @media (max-width: 960px) {
      .dashboard-layout,
      .dashboard-layout.sidebar-collapsed {
        grid-template-columns: 1fr;
      }

      .dashboard-sidebar {
        position: relative;
        top: auto;
      }

      .dashboard-layout.sidebar-collapsed .toc {
        opacity: 1;
        transform: none;
        pointer-events: auto;
        visibility: visible;
      }
    }

    @media (max-width: 560px) {
      .trend-grid {
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 10px;
      }

      .trend-widget {
        min-height: 118px;
        padding: 12px 6px;
      }

      .trend-ring {
        width: clamp(58px, 22vw, 70px);
        height: clamp(58px, 22vw, 70px);
      }

      .trend-ring span {
        font-size: 1.12rem;
      }

      .trend-widget p {
        font-size: 0.72rem;
        line-height: 1.25;
        overflow-wrap: anywhere;
      }
    }
"""

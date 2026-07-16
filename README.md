# AI Research Daily Agent

A modular Python 3.12 agent that collects astronomy research items from the previous Beijing-time 08:00-to-08:00 window, ranks them against your interests and broader scientific value, summarizes the most interesting papers, writes a Markdown/HTML briefing, and optionally sends it to Email, Notion, PushPlus, or ServerChan.

The first version is intentionally simple: arXiv is implemented, Nature and Science source modules are clean placeholders, and the LLM layer supports OpenAI-compatible APIs plus DeepSeek through one interface.

## Features

- YAML config for topics, sources, models, max papers, language, and delivery methods.
- API keys and delivery secrets loaded from `.env`.
- arXiv search constrained to the previous 08:00-to-08:00 Beijing-time window by `submittedDate`.
- Duplicate removal by normalized title and URL.
- LLM ranking with score, novelty, impact, relevance, and recommendation reason.
- Markdown and self-contained HTML reports with highlights, must-read papers, recommendations, summaries, trends, open questions, and links.
- Delivery modules for SMTP email, Notion page creation, PushPlus, and ServerChan.
- Manual runs, cron, and GitHub Actions friendly.

## Quick Start

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
mkdir -p config
cp config.example.yaml config/config.yaml
python main.py --no-delivery
```

Reports are written to:

```text
reports/briefing-YYYY-MM-DD.md
reports/briefing-YYYY-MM-DD.html
site/index.html
site/archive/briefing-YYYY-MM-DD.html
```

The HTML report is self-contained, includes all CSS in the file, and can be opened directly in a browser by double-clicking it.

`site/index.html` is the latest report formatted for GitHub Pages. The archive copy in `site/archive/` keeps dated HTML snapshots.

The HTML report randomly embeds compressed astronomy images from `assets/astronomy/` as the hero and page background visuals. The file remains self-contained, so the images display on GitHub Pages and after downloading the email attachment.

Paper cards do not use random decorative images. A placeholder hook exists for future paper-specific figure extraction, but figures are omitted unless they can be clearly associated with the paper.

If you keep your config at the project root as `config.yaml`, the agent will also detect it automatically. You can also pass it explicitly:

```bash
python main.py --config config.yaml --no-delivery
```

By default, the agent targets the previous Beijing-time reporting window: 08:00 on the target date to 08:00 the next day. If no papers are fetched for that window, it looks backward up to `app.fallback_days` days and reports the latest window that actually has papers. The visible title uses the actual paper window, for example `天文论文日报（本期：2026-07-15 08:00 至 2026-07-16 08:00，北京时间）`.

This matters on weekends and holidays: if arXiv has no new matching papers, the website and email keep showing the most recent available paper window instead of pretending that stale papers are from today.

To test a specific day:

```bash
python main.py --date 2026-07-08 --no-delivery
```

`topics` are not fetch filters. They are preference signals for ranking and selection. The agent fetches all configured astrophysics papers first, then selects up to `app.max_selected` papers with at least a three-star score (`>= 60/100`) based on interest, novelty, scientific value, method usefulness, source priority, and overall recommendation strength.

## LLM Providers

OpenAI-compatible API:

```yaml
llm:
  provider: openai_compatible
  model: gpt-4o-mini
  base_url: https://api.openai.com/v1
  api_key_env: OPENAI_API_KEY
```

DeepSeek:

```yaml
llm:
  provider: deepseek
  model: deepseek-chat
  base_url: https://api.deepseek.com/v1
  api_key_env: DEEPSEEK_API_KEY
```

Future providers can be added by implementing `LLMClient` in `llm/base.py` and registering the provider in `llm/providers.py`.

If the API key is missing or a model call fails, ranking and summaries fall back to deterministic heuristics so the run can still finish.

### System Prompt

The model behavior is controlled by `llm.system_prompt` in your YAML config. Edit this field to change the assistant persona, scientific caution level, terminology style, or summary priorities without changing code.

The default prompt describes the model as an experienced astronomer and research assistant, asks it to avoid exaggeration, distinguish facts from inference, explain technical terms in Chinese with English in parentheses, and focus on contribution, methods, limitations, future work, and relevance.

## Sources

### arXiv

`sources/arxiv_source.py` uses the arXiv API and filters to items submitted inside the 08:00-to-08:00 Beijing-time report window. It fetches all configured astrophysics categories first; `topics` are used later for ranking, not as a fetch-time filter. The default astronomy categories cover all six arXiv astro-ph subcategories:

- `astro-ph.GA`
- `astro-ph.CO`
- `astro-ph.EP`
- `astro-ph.HE`
- `astro-ph.IM`
- `astro-ph.SR`

### Nature and Science

`sources/nature_source.py` and `sources/science_source.py` are placeholders because journal feeds and APIs vary by product, license, and institution. To add a real implementation:

1. Keep the `Source.fetch(target_date, topics, timezone) -> list[Paper]` interface.
2. Use an official API or RSS feed when available.
3. Filter published dates to the 08:00-to-08:00 report window in `timezone`.
4. Map results into `utils.models.Paper`.
5. Register the class in `sources/factory.py`.

Priority selection already keeps Nature, Science, and Nature sub-journal items in the final briefing when those sources return papers.

## Delivery

All delivery methods are disabled by default. Enable them in `config/config.yaml` and fill the matching `.env` keys.

- Email: SMTP via the standard library. The email body is a short notification; the full report is attached as an HTML file.
- SMTP authorization codes belong in `.env`, not in YAML. Put the code in the variable referenced by `password_env`, usually `SMTP_PASSWORD`.
- Notion: creates a page in a Notion database using `NOTION_TOKEN` and `NOTION_DATABASE_ID`; the database should have a title property named `Name`.
- PushPlus: Markdown WeChat-compatible push.
- ServerChan: Markdown WeChat-compatible push.

Email attachment behavior is controlled in config:

```yaml
delivery:
  email:
    enabled: true
    attach_html: true
    attach_markdown: false
    body_style: brief
```

Set `attach_markdown: true` if you also want the Markdown report attached. If the HTML report is missing, the agent falls back to sending the Markdown report in the email body.

You can always generate a local report without sending:

```bash
python main.py --no-delivery
```

The local HTML dashboard will still be generated even when delivery is skipped.

## Scheduling

This repository includes a guarded macOS LaunchAgent example in `launch_agents/com.lky.arxive-agent.plist`.
It calls `scripts/run_scheduled.py`, which prevents duplicate automatic emails:

- before 08:00, login/startup does not send early;
- at or after 08:00, it sends only if today's automatic run has not already succeeded;
- if all sources fail and zero papers are fetched, it generates local files but skips email and does not mark the day successful;
- manual runs with `python main.py` are never blocked by this guard.

Cron example, running every morning at 08:00:

```cron
0 8 * * * cd /path/to/arxive_agent && /path/to/arxive_agent/.venv/bin/python main.py
```

GitHub Actions example:

```yaml
name: AI Research Daily
on:
  schedule:
    - cron: "0 0 * * *"
  workflow_dispatch:
jobs:
  run:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -r requirements.txt
      - run: python main.py
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
          PUSHPLUS_TOKEN: ${{ secrets.PUSHPLUS_TOKEN }}
```

## GitHub Pages Website

The project can publish the HTML briefing as a mobile-friendly website through GitHub Pages.
The included workflow `.github/workflows/github-pages.yml` runs at 08:00 Asia/Shanghai time, deploys the generated `site/` folder, and sends a short email with the website link.

Setup:

1. Push this project to a GitHub repository.
2. In GitHub, open `Settings -> Pages` and choose `GitHub Actions` as the source.
3. Add `DEEPSEEK_API_KEY`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_SENDER`, and `SMTP_RECIPIENTS` under `Settings -> Secrets and variables -> Actions -> Repository secrets`.
4. Run the workflow manually once from `Actions -> Astronomy Daily Pages -> Run workflow`.
5. Copy the Pages URL into `config/config.yaml`:

```yaml
site:
  public_url: "https://YOUR_USER.github.io/YOUR_REPO/"
```

After `site.public_url` is configured, the brief email includes an online reading link. The GitHub Actions workflow uses `config.github-pages.yaml`.

## Project Structure

```text
config/       YAML loading and typed config dataclasses
sources/      arXiv implementation plus Nature/Science placeholders
llm/          unified LLM interface and providers
ranking/      paper ranking logic
summarizer/   structured paper summaries
report/       Markdown and HTML briefing generation
delivery/     Email, Notion, PushPlus, ServerChan
utils/        shared models, dates, logging, JSON parsing, de-duplication
main.py       orchestration entrypoint
```

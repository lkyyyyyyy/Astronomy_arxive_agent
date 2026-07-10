from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv


DEFAULT_LLM_SYSTEM_PROMPT = """你是一位经验丰富的天文学家和科研助理，熟悉星系演化、活动星系核、黑洞、观测天文学和多波段数据分析。
你的任务是帮助研究者准确筛选、排序、总结和翻译每日论文。
请严格基于题目、摘要和提供的元数据作答，避免夸大结论。
请区分论文中明确给出的事实与基于摘要做出的合理推断。
技术术语应以中文为主，并在必要时附英文括号，例如：活动星系核（AGN）、中等质量黑洞（intermediate-mass black hole）、引力透镜（gravitational lensing）。
重点关注科学贡献、研究方法、局限性、后续方向，以及与用户研究兴趣的相关性。
输出应清晰、克制、准确，避免营销式语言。"""


@dataclass(slots=True)
class AppConfig:
    timezone: str = "Asia/Shanghai"
    language: str = "English"
    max_items: int = 50
    max_selected: int = 10
    output_dir: str = "reports"


@dataclass(slots=True)
class SiteConfig:
    enabled: bool = True
    output_dir: str = "site"
    latest_filename: str = "index.html"
    archive_dir: str = "archive"
    public_url: str = ""


@dataclass(slots=True)
class SourceConfig:
    enabled: bool = True
    max_results: int = 50
    timeout_seconds: int = 90
    retries: int = 3
    categories: list[str] = field(default_factory=list)
    journals: list[str] = field(default_factory=list)


@dataclass(slots=True)
class LLMConfig:
    provider: str = "openai_compatible"
    model: str = "gpt-4o-mini"
    base_url: str = "https://api.openai.com/v1"
    api_key_env: str = "OPENAI_API_KEY"
    system_prompt: str = DEFAULT_LLM_SYSTEM_PROMPT
    temperature: float = 0.2
    max_tokens: int = 4000
    timeout_seconds: int = 60


@dataclass(slots=True)
class EmailConfig:
    enabled: bool = False
    smtp_host: str = ""
    smtp_port: int = 587
    username_env: str = "SMTP_USERNAME"
    password_env: str = "SMTP_PASSWORD"
    sender: str = ""
    recipients: list[str] = field(default_factory=list)
    use_tls: bool = True
    attach_html: bool = True
    attach_markdown: bool = False
    body_style: str = "brief"


@dataclass(slots=True)
class NotionConfig:
    enabled: bool = False
    token_env: str = "NOTION_TOKEN"
    database_id_env: str = "NOTION_DATABASE_ID"


@dataclass(slots=True)
class PushPlusConfig:
    enabled: bool = False
    token_env: str = "PUSHPLUS_TOKEN"


@dataclass(slots=True)
class ServerChanConfig:
    enabled: bool = False
    sendkey_env: str = "SERVERCHAN_SENDKEY"


@dataclass(slots=True)
class DeliveryConfig:
    email: EmailConfig = field(default_factory=EmailConfig)
    notion: NotionConfig = field(default_factory=NotionConfig)
    pushplus: PushPlusConfig = field(default_factory=PushPlusConfig)
    serverchan: ServerChanConfig = field(default_factory=ServerChanConfig)


@dataclass(slots=True)
class Config:
    app: AppConfig = field(default_factory=AppConfig)
    site: SiteConfig = field(default_factory=SiteConfig)
    topics: list[str] = field(default_factory=list)
    sources: dict[str, SourceConfig] = field(default_factory=dict)
    llm: LLMConfig = field(default_factory=LLMConfig)
    delivery: DeliveryConfig = field(default_factory=DeliveryConfig)


def _read_mapping(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Config file must contain a YAML mapping: {path}")
    return data


def load_config(path: str | Path) -> Config:
    """Load YAML config and .env variables."""
    load_dotenv()

    path = Path(path)
    data = _read_mapping(path)

    app = AppConfig(**(data.get("app") or {}))
    site = SiteConfig(**(data.get("site") or {}))
    llm = LLMConfig(**(data.get("llm") or {}))

    raw_sources = data.get("sources") or {}
    sources = {
        name: SourceConfig(**(settings or {}))
        for name, settings in raw_sources.items()
    }

    raw_delivery = data.get("delivery") or {}
    delivery = DeliveryConfig(
        email=EmailConfig(**(raw_delivery.get("email") or {})),
        notion=NotionConfig(**(raw_delivery.get("notion") or {})),
        pushplus=PushPlusConfig(**(raw_delivery.get("pushplus") or {})),
        serverchan=ServerChanConfig(**(raw_delivery.get("serverchan") or {})),
    )

    return Config(
        app=app,
        site=site,
        topics=list(data.get("topics") or []),
        sources=sources,
        llm=llm,
        delivery=delivery,
    )

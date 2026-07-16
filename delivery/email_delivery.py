from __future__ import annotations

from email.message import EmailMessage
import logging
import os
from pathlib import Path
import smtplib

from config.loader import EmailConfig
from delivery.base import DeliveryChannel, DeliveryContext

LOGGER = logging.getLogger(__name__)


class EmailDelivery(DeliveryChannel):
    def __init__(self, config: EmailConfig) -> None:
        self.config = config

    def send(self, title: str, context: DeliveryContext) -> None:
        username = os.getenv(self.config.username_env, "")
        password = os.getenv(self.config.password_env, "")
        sender = self.config.sender or os.getenv(self.config.sender_env, "") or username
        recipients = self.config.recipients or _env_list(self.config.recipients_env)
        missing = []
        if not self.config.smtp_host:
            missing.append("delivery.email.smtp_host")
        if not sender:
            missing.append(
                f"delivery.email.sender, env {self.config.sender_env}, or env {self.config.username_env}"
            )
        if not password:
            missing.append(f"env {self.config.password_env}")
        if not recipients:
            missing.append(f"delivery.email.recipients or env {self.config.recipients_env}")
        if missing:
            LOGGER.warning(
                "Email delivery skipped because settings are incomplete: %s",
                ", ".join(missing),
            )
            return

        message = EmailMessage()
        message["Subject"] = title
        message["From"] = sender
        message["To"] = ", ".join(recipients)

        html_available = bool(context.html_path and context.html_path.exists())
        if self.config.body_style == "brief" and html_available:
            message.set_content(_brief_body(context, title))
        else:
            if self.config.attach_html and not html_available:
                LOGGER.warning("HTML report is missing; falling back to Markdown email body.")
            message.set_content(context.markdown)

        if self.config.attach_html:
            _attach_text_file(
                message=message,
                path=context.html_path,
                subtype="html",
                missing_message="HTML attachment skipped because the file is missing.",
            )

        if self.config.attach_markdown:
            _attach_text_file(
                message=message,
                path=context.markdown_path,
                subtype="markdown",
                missing_message="Markdown attachment skipped because the file is missing.",
            )

        with smtplib.SMTP(self.config.smtp_host, self.config.smtp_port, timeout=30) as smtp:
            if self.config.use_tls:
                smtp.starttls()
            if username:
                smtp.login(username, password)
            smtp.send_message(message)
        LOGGER.info("Email briefing sent to %d recipient(s).", len(recipients))


def _brief_body(context: DeliveryContext, title: str) -> str:
    selected_count = len(context.selected_papers)
    lines = [
        title,
        "",
        f"今日共抓取论文：{context.total_fetched} 篇",
        f"入选推荐论文：{selected_count} 篇",
    ]
    if context.public_url:
        lines.extend(["", f"在线阅读：{context.public_url}"])

    lines.extend(["", "Top 3:"])

    top_papers = context.selected_papers[:3]
    if top_papers:
        for index, ranked in enumerate(top_papers, start=1):
            lines.append(
                f"{index:02d}. {_score_to_stars(ranked.interest_score)} {ranked.paper.title}"
            )
    else:
        lines.append("暂无入选论文。")

    if context.public_url:
        lines.extend(["", "完整日报也可以通过上方网页链接阅读。"])
    else:
        lines.extend(["", "完整日报见附件 HTML 文件。"])
    return "\n".join(lines)


def _attach_text_file(
    message: EmailMessage,
    path: Path | None,
    subtype: str,
    missing_message: str,
) -> None:
    if not path or not path.exists():
        LOGGER.warning(missing_message)
        return
    try:
        content = path.read_text(encoding="utf-8")
        message.add_attachment(content, subtype=subtype, filename=path.name)
        LOGGER.info("Attached report file: %s", path)
    except Exception as exc:
        LOGGER.error("Could not attach %s: %s", path, exc)


def _env_list(name: str) -> list[str]:
    raw = os.getenv(name, "")
    return [item.strip() for item in raw.replace(";", ",").split(",") if item.strip()]


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

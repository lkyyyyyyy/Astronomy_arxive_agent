from __future__ import annotations

import logging
import os

import requests

from config.loader import NotionConfig
from delivery.base import DeliveryChannel, DeliveryContext

LOGGER = logging.getLogger(__name__)


class NotionDelivery(DeliveryChannel):
    api_url = "https://api.notion.com/v1/pages"
    notion_version = "2022-06-28"

    def __init__(self, config: NotionConfig) -> None:
        self.config = config

    def send(self, title: str, context: DeliveryContext) -> None:
        token = os.getenv(self.config.token_env, "")
        database_id = os.getenv(self.config.database_id_env, "")
        if not token or not database_id:
            LOGGER.warning("Notion delivery skipped because token/database id is missing.")
            return

        payload = {
            "parent": {"database_id": database_id},
            "properties": {
                "Name": {"title": [{"text": {"content": title[:2000]}}]},
            },
            "children": _markdown_to_blocks(context.markdown),
        }
        headers = {
            "Authorization": f"Bearer {token}",
            "Notion-Version": self.notion_version,
            "Content-Type": "application/json",
        }
        response = requests.post(self.api_url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        LOGGER.info("Notion briefing page created.")


def _markdown_to_blocks(markdown: str) -> list[dict]:
    blocks: list[dict] = []
    for raw_line in markdown.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        block_type = "paragraph"
        content = line
        if line.startswith("# "):
            block_type = "heading_1"
            content = line[2:].strip()
        elif line.startswith("## "):
            block_type = "heading_2"
            content = line[3:].strip()
        elif line.startswith("### "):
            block_type = "heading_3"
            content = line[4:].strip()
        elif line.startswith("- "):
            block_type = "bulleted_list_item"
            content = line[2:].strip()

        blocks.append(
            {
                "object": "block",
                "type": block_type,
                block_type: {
                    "rich_text": [{"type": "text", "text": {"content": content[:2000]}}]
                },
            }
        )
        if len(blocks) >= 90:
            LOGGER.warning("Notion block limit guard reached; report was truncated.")
            break
    return blocks

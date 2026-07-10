from __future__ import annotations

import logging
import os

import requests

from config.loader import PushPlusConfig
from delivery.base import DeliveryChannel, DeliveryContext

LOGGER = logging.getLogger(__name__)


class PushPlusDelivery(DeliveryChannel):
    api_url = "https://www.pushplus.plus/send"

    def __init__(self, config: PushPlusConfig) -> None:
        self.config = config

    def send(self, title: str, context: DeliveryContext) -> None:
        token = os.getenv(self.config.token_env, "")
        if not token:
            LOGGER.warning("PushPlus delivery skipped because token is missing.")
            return
        payload = {
            "token": token,
            "title": title,
            "content": context.markdown,
            "template": "markdown",
        }
        response = requests.post(self.api_url, json=payload, timeout=30)
        response.raise_for_status()
        LOGGER.info("PushPlus briefing sent.")

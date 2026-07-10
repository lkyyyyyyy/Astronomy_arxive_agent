from __future__ import annotations

import logging
import os

import requests

from config.loader import ServerChanConfig
from delivery.base import DeliveryChannel, DeliveryContext

LOGGER = logging.getLogger(__name__)


class ServerChanDelivery(DeliveryChannel):
    def __init__(self, config: ServerChanConfig) -> None:
        self.config = config

    def send(self, title: str, context: DeliveryContext) -> None:
        sendkey = os.getenv(self.config.sendkey_env, "")
        if not sendkey:
            LOGGER.warning("ServerChan delivery skipped because sendkey is missing.")
            return
        url = f"https://sctapi.ftqq.com/{sendkey}.send"
        response = requests.post(
            url,
            data={"title": title, "desp": context.markdown},
            timeout=30,
        )
        response.raise_for_status()
        LOGGER.info("ServerChan briefing sent.")

from __future__ import annotations

from config.loader import DeliveryConfig
from delivery.base import DeliveryChannel
from delivery.email_delivery import EmailDelivery
from delivery.notion_delivery import NotionDelivery
from delivery.pushplus_delivery import PushPlusDelivery
from delivery.serverchan_delivery import ServerChanDelivery


def build_delivery_channels(config: DeliveryConfig) -> list[DeliveryChannel]:
    channels: list[DeliveryChannel] = []
    if config.email.enabled:
        channels.append(EmailDelivery(config.email))
    if config.notion.enabled:
        channels.append(NotionDelivery(config.notion))
    if config.pushplus.enabled:
        channels.append(PushPlusDelivery(config.pushplus))
    if config.serverchan.enabled:
        channels.append(ServerChanDelivery(config.serverchan))
    return channels


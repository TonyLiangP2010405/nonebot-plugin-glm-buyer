"""Shared helpers for the GLM Buyer plugin."""

from __future__ import annotations

import base64

from nonebot.adapters.onebot.v11 import MessageSegment


def qr_base64_to_image_segment(base64_str: str) -> MessageSegment:
    """Convert a data-uri QR base64 string to a OneBot image segment."""
    payload = base64_str.split(",", 1)[1] if "," in base64_str else base64_str
    return MessageSegment.image(file=base64.b64decode(payload))

"""NoneBot plugin entrypoint for GLM Coding buyer automation."""

from __future__ import annotations

import logging
from pathlib import Path

from nonebot import get_driver, get_plugin_config, require
from nonebot.plugin import PluginMetadata

from .config import Config

require("nonebot_plugin_localstore")
require("nonebot_plugin_apscheduler")

from nonebot_plugin_apscheduler import scheduler
from nonebot_plugin_localstore import get_plugin_data_dir

from .core.config import configure_core_settings, get_settings
from .core.proxy_pool.service import (
    get_builtin_proxy_pool_service,
    should_auto_start_proxy_pool,
)
from .core.services.ocr_service import get_ocr_service
from .core.services.scheduler_service import get_scheduler_service

logger = logging.getLogger(__name__)

__plugin_meta__ = PluginMetadata(
    name="GLM Buyer",
    description="通过 QQ 私聊控制 GLM Coding 账号抢购与支付二维码",
    usage="私聊发送 `glm 帮助` 查看指令",
    type="application",
    homepage="https://github.com/owner/nonebot-plugin-glm-buyer",
    config=Config,
    supported_adapters={"~onebot.v11"},
)


def _resolve_data_dir(plugin_config: Config) -> Path:
    explicit = (plugin_config.glm_buyer_data_dir or "").strip()
    if explicit:
        path = Path(explicit).expanduser()
        if not path.is_absolute():
            path = Path.cwd() / path
        return path.resolve()
    return Path(get_plugin_data_dir())


driver = get_driver()


@driver.on_startup
async def _on_startup() -> None:
    plugin_config = get_plugin_config(Config)
    data_dir = _resolve_data_dir(plugin_config)
    configure_core_settings(plugin_config, data_dir)
    settings = get_settings()

    logger.info("[glm-buyer] data dir: %s", data_dir)
    logger.info("[glm-buyer] network egress mode: %s", settings.network_egress_mode)

    # Warm up OCR workers in the background.
    ocr_service = get_ocr_service()
    if ocr_service.warmup_in_background():
        logger.info("[glm-buyer] OCR warmup started in background")

    # Start built-in proxy pool if configured to use it.
    if should_auto_start_proxy_pool():
        try:
            get_builtin_proxy_pool_service().start()
            logger.info("[glm-buyer] built-in proxy pool started")
        except Exception as exc:
            logger.warning("[glm-buyer] built-in proxy pool startup failed: %s", exc)

    # Start scheduler (apscheduler-backed).
    scheduler_service = get_scheduler_service()
    scheduler_service.start()

    # Register apscheduler tick for scheduled flows.
    scheduler.add_job(
        _scheduled_tick,
        "cron",
        second="*",
        id="glm_buyer_scheduled_tick",
        replace_existing=True,
    )

    logger.info("[glm-buyer] plugin started")


@driver.on_shutdown
async def _on_shutdown() -> None:
    logger.info("[glm-buyer] plugin shutting down")
    try:
        get_scheduler_service().stop()
    except Exception as exc:
        logger.warning("[glm-buyer] scheduler shutdown failed: %s", exc)

    if should_auto_start_proxy_pool():
        try:
            get_builtin_proxy_pool_service().stop()
        except Exception as exc:
            logger.warning("[glm-buyer] proxy pool shutdown failed: %s", exc)

    try:
        get_ocr_service().shutdown()
    except Exception as exc:
        logger.warning("[glm-buyer] OCR shutdown failed: %s", exc)


async def _scheduled_tick() -> None:
    """Called every second by apscheduler to run scheduled account flows."""
    from .commands import notify_superuser_qr

    scheduler_service = get_scheduler_service()
    scheduler_service.poll_once()

    # Notify superusers of newly completed scheduled tasks.
    try:
        await notify_superuser_qr()
    except Exception as exc:
        logger.warning("[glm-buyer] failed to notify superusers: %s", exc)


from . import commands  # noqa: E402, F401

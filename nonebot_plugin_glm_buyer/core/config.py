"""Internal application settings and path resolution.

The plugin layer (``nonebot_plugin_glm_buyer``) is responsible for calling
``configure_core_settings`` once at startup. After that, the legacy
``get_settings()`` cached accessor works unchanged for all core modules.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

# Protocol defaults from the original glm-coding .env.example.
# These are intentionally hard-coded so the plugin is zero-config importable.
DEFAULT_PROTOCOL_SETTINGS: dict[str, Any] = {
    "bigmodel_api_base": "https://www.bigmodel.cn/api",
    "bigmodel_origin": "https://www.bigmodel.cn",
    "bigmodel_referer": "https://www.bigmodel.cn/glm-coding",
    "browser_impersonate": "chrome146",
    "bootstrap_fingerprint_max_retries": 99,
    "request_timeout_seconds": 20.0,
    "default_language": "zh",
    "tencent_captcha_domain": "https://turing.captcha.qcloud.com",
    "tencent_captcha_aid": "196026326",
    "tencent_captcha_entry_url": "https://www.bigmodel.cn/glm-coding",
    "tencent_captcha_max_retries": 3,
    "tencent_captcha_min_confidence": 0.55,
    "tencent_captcha_node": "node",
    "tencent_ocr_enabled": True,
    "tencent_ocr_include_debug": False,
    "tencent_ocr_opencv_threads": 1,
    "tencent_ocr_onnx_threads": 1,
}


@dataclass(frozen=True)
class Settings:
    """Runtime settings used by the core payment flow."""

    data_dir: Path
    runtime_logs_dir: Path
    accounts_path: Path
    tasks_path: Path
    sessions_dir: Path
    bigmodel_api_base: str
    bigmodel_origin: str
    bigmodel_referer: str
    browser_impersonate: str
    bootstrap_fingerprint_max_retries: int
    request_timeout_seconds: float
    default_language: str
    tencent_captcha_domain: str
    tencent_captcha_aid: str
    tencent_captcha_entry_url: str
    tencent_captcha_max_retries: int
    tencent_captcha_min_confidence: float
    tencent_captcha_node: str
    tencent_ocr_enabled: bool
    tencent_ocr_include_debug: bool
    tencent_ocr_workers: int
    tencent_ocr_timeout_seconds: int
    tencent_ocr_opencv_threads: int
    tencent_ocr_onnx_threads: int
    runtime_log_level: str
    runtime_log_retention_days: int
    network_egress_mode: str
    fallback_proxy_url: str
    fallback_proxy_ticket_pool_only: bool
    proxy_pool_config_path: Path | None


# Global state populated by the plugin layer on startup.
_core_settings: Settings | None = None


def configure_core_settings(
    plugin_config: Any,
    data_dir: Path,
) -> Settings:
    """Build core Settings from the NoneBot plugin config and data directory."""
    global _core_settings

    data_dir = Path(data_dir).expanduser().resolve()
    sessions_dir = data_dir / "sessions"
    runtime_logs_dir = data_dir / "logs" / "runtime"
    data_dir.mkdir(parents=True, exist_ok=True)
    sessions_dir.mkdir(parents=True, exist_ok=True)
    runtime_logs_dir.mkdir(parents=True, exist_ok=True)

    proxy_config_raw = str(getattr(plugin_config, "glm_buyer_proxy_pool_config", "proxy_pool.yaml") or "").strip()
    if proxy_config_raw:
        candidate = Path(proxy_config_raw).expanduser()
        if not candidate.is_absolute():
            candidate = data_dir / candidate
        proxy_pool_config_path: Path | None = candidate
    else:
        # Fall back to the bundled default config shipped with the plugin.
        proxy_pool_config_path = Path(__file__).resolve().parents[1] / "proxy_pool.yaml"

    settings = Settings(
        data_dir=data_dir,
        runtime_logs_dir=runtime_logs_dir,
        accounts_path=data_dir / "accounts.json",
        tasks_path=data_dir / "tasks.json",
        sessions_dir=sessions_dir,
        bigmodel_api_base=DEFAULT_PROTOCOL_SETTINGS["bigmodel_api_base"],
        bigmodel_origin=DEFAULT_PROTOCOL_SETTINGS["bigmodel_origin"],
        bigmodel_referer=DEFAULT_PROTOCOL_SETTINGS["bigmodel_referer"],
        browser_impersonate=DEFAULT_PROTOCOL_SETTINGS["browser_impersonate"],
        bootstrap_fingerprint_max_retries=DEFAULT_PROTOCOL_SETTINGS["bootstrap_fingerprint_max_retries"],
        request_timeout_seconds=DEFAULT_PROTOCOL_SETTINGS["request_timeout_seconds"],
        default_language=DEFAULT_PROTOCOL_SETTINGS["default_language"],
        tencent_captcha_domain=DEFAULT_PROTOCOL_SETTINGS["tencent_captcha_domain"],
        tencent_captcha_aid=DEFAULT_PROTOCOL_SETTINGS["tencent_captcha_aid"],
        tencent_captcha_entry_url=DEFAULT_PROTOCOL_SETTINGS["tencent_captcha_entry_url"],
        tencent_captcha_max_retries=DEFAULT_PROTOCOL_SETTINGS["tencent_captcha_max_retries"],
        tencent_captcha_min_confidence=DEFAULT_PROTOCOL_SETTINGS["tencent_captcha_min_confidence"],
        tencent_captcha_node=DEFAULT_PROTOCOL_SETTINGS["tencent_captcha_node"],
        tencent_ocr_enabled=DEFAULT_PROTOCOL_SETTINGS["tencent_ocr_enabled"],
        tencent_ocr_include_debug=DEFAULT_PROTOCOL_SETTINGS["tencent_ocr_include_debug"],
        tencent_ocr_workers=int(getattr(plugin_config, "glm_buyer_ocr_workers", 4)),
        tencent_ocr_timeout_seconds=int(getattr(plugin_config, "glm_buyer_tesseract_ocr_timeout", 6)),
        tencent_ocr_opencv_threads=DEFAULT_PROTOCOL_SETTINGS["tencent_ocr_opencv_threads"],
        tencent_ocr_onnx_threads=DEFAULT_PROTOCOL_SETTINGS["tencent_ocr_onnx_threads"],
        runtime_log_level=str(getattr(plugin_config, "glm_buyer_log_level", "INFO")),
        runtime_log_retention_days=int(getattr(plugin_config, "glm_buyer_log_retention_days", 7)),
        network_egress_mode=str(getattr(plugin_config, "glm_buyer_network_egress_mode", "local")),
        fallback_proxy_url=str(getattr(plugin_config, "glm_buyer_fallback_proxy_url", "http://127.0.0.1:17286")),
        fallback_proxy_ticket_pool_only=bool(
            getattr(plugin_config, "glm_buyer_fallback_proxy_ticket_pool_only", False)
        ),
        proxy_pool_config_path=proxy_pool_config_path,
    )
    _core_settings = settings
    get_settings.cache_clear()
    return settings


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the configured core settings.

    Raises:
        RuntimeError: if ``configure_core_settings`` has not been called.
    """
    if _core_settings is None:
        raise RuntimeError(
            "Core settings have not been initialized. Call configure_core_settings() during plugin startup first."
        )
    return _core_settings

"""NoneBot plugin configuration."""

from pydantic import BaseModel, Field


class Config(BaseModel):
    """Plugin configuration exposed to NoneBot .env file.

    Protocol defaults (BigModel URLs, captcha aid, etc.) are hard-coded in
    ``core/config.py`` so that the plugin works out of the box. Only runtime
    tunables are exposed here.
    """

    # Data directory
    glm_buyer_data_dir: str = Field(
        default="",
        description="数据目录；留空则使用 nonebot-plugin-localstore 提供的插件数据目录",
    )

    # Runtime / logging
    glm_buyer_ocr_workers: int = Field(default=4, ge=1, le=16)
    glm_buyer_log_level: str = Field(default="INFO")
    glm_buyer_log_retention_days: int = Field(default=7, ge=1)

    # Network egress
    glm_buyer_network_egress_mode: str = Field(default="local")
    glm_buyer_fallback_proxy_url: str = Field(default="http://127.0.0.1:17286")
    glm_buyer_fallback_proxy_ticket_pool_only: bool = Field(default=False)
    glm_buyer_proxy_pool_config: str = Field(default="proxy_pool.yaml")

    # OCR / captcha
    glm_buyer_tesseract_ocr_enabled: bool = Field(default=True)
    glm_buyer_tesseract_ocr_timeout: int = Field(default=6, ge=1)
    glm_buyer_tesseract_ocr_min_confidence: float = Field(default=0.55, ge=0.0, le=1.0)
    glm_buyer_tesseract_captcha_max_retries: int = Field(default=3, ge=1)

    # Notifications
    glm_buyer_notify_superuser_on_schedule: bool = Field(default=True)

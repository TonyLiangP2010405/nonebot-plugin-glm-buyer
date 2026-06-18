"""QQ private-chat command handlers for GLM Buyer."""

from __future__ import annotations

import logging
from datetime import datetime

from nonebot import on_regex
from nonebot.adapters.onebot.v11 import (
    Bot,
    Message,
    MessageEvent,
    MessageSegment,
    PrivateMessageEvent,
)
from nonebot.exception import FinishedException
from nonebot.rule import to_me
from nonebot.utils import run_sync

from nonebot_plugin_glm_buyer.core.config import get_settings
from nonebot_plugin_glm_buyer.core.models import (
    AccountImportRequest,
    AccountPreferencesRequest,
)
from nonebot_plugin_glm_buyer.core.services.account_state import get_account_state_service
from nonebot_plugin_glm_buyer.core.services.network_mode_service import get_network_mode_service
from nonebot_plugin_glm_buyer.core.services.payment_service import get_payment_service
from nonebot_plugin_glm_buyer.core.services.scheduler_service import get_scheduler_service
from nonebot_plugin_glm_buyer.utils import qr_base64_to_image_segment

logger = logging.getLogger(__name__)

matcher = on_regex(r"^glm\s+(\S+)\s*(.*)$", rule=to_me(), priority=10, block=True)


def _is_authorized(event: MessageEvent) -> bool:
    from nonebot import get_driver

    if not isinstance(event, PrivateMessageEvent):
        return False
    return str(event.user_id) in get_driver().config.superusers


def _reply(message: str | Message) -> Message:
    if isinstance(message, str):
        return Message(message)
    return message


def _format_account(public_account) -> str:
    status = public_account.account_status or "unchecked"
    schedule = public_account.last_schedule_status or "idle"
    return (
        f"[{public_account.label}] {status}\n"
        f"  ID: {public_account.id}\n"
        f"  指纹: {public_account.browser_impersonate}\n"
        f"  套餐: {public_account.selected_product_id or '未选'}\n"
        f"  定时: {'开' if public_account.schedule_enabled else '关'} {public_account.scheduled_start_time or ''}\n"
        f"  任务: {schedule} {public_account.last_schedule_message or ''}"
    )


@matcher.handle()
async def handle_command(bot: Bot, event: MessageEvent):
    if not _is_authorized(event):
        await matcher.finish("该功能仅 superuser 私聊可用。")

    matched = event.get_plaintext().strip()
    parts = matched.split(None, 2)
    if len(parts) < 2:
        await matcher.finish(_help_text())

    action = parts[1]
    args = parts[2] if len(parts) > 2 else ""

    handlers = {
        "帮助": _cmd_help,
        "添加账号": _cmd_add_account,
        "账号列表": _cmd_list_accounts,
        "账号": _cmd_account_detail,
        "删除账号": _cmd_delete_account,
        "同步": _cmd_bootstrap,
        "换指纹": _cmd_refresh_fingerprint,
        "套餐": _cmd_products,
        "设置套餐": _cmd_set_product,
        "启动": _cmd_run,
        "二维码": _cmd_qr,
        "定时": _cmd_schedule,
        "取消定时": _cmd_cancel_schedule,
        "暂停": _cmd_pause,
        "状态": _cmd_status,
        "切换出口": _cmd_switch_egress,
        "日志": _cmd_logs,
        "查看全部设置": _cmd_settings,
    }

    handler = handlers.get(action)
    if handler is None:
        await matcher.finish(f"未知命令：{action}\n{_help_text()}")

    try:
        result = await handler(args)
    except FinishedException:
        raise
    except Exception as exc:
        logger.exception("glm command failed: %s", exc)
        await matcher.finish(f"操作失败：{exc}")

    if isinstance(result, Message):
        await matcher.finish(result)
    await matcher.finish(str(result))


def _help_text() -> str:
    return (
        "glm 帮助\n"
        "glm 添加账号 <label> <token>\n"
        "glm 账号列表\n"
        "glm 账号 <id>\n"
        "glm 删除账号 <id>\n"
        "glm 同步 <id>\n"
        "glm 换指纹 <id>\n"
        "glm 套餐 <id>\n"
        "glm 设置套餐 <id> <product_id>\n"
        "glm 启动 <id>\n"
        "glm 二维码 <id>\n"
        "glm 定时 <id> <HH:MM:SS>\n"
        "glm 取消定时 <id>\n"
        "glm 暂停 <id>\n"
        "glm 状态\n"
        "glm 切换出口 <local|proxy_pool>\n"
        "glm 日志\n"
        "glm 查看全部设置"
    )


async def _cmd_help(_: str) -> str:
    return _help_text()


async def _cmd_add_account(args: str) -> str:
    parts = args.split(None, 1)
    if len(parts) < 2:
        return "用法：glm 添加账号 <label> <token>"
    label, token = parts
    request = AccountImportRequest(label=label, token=token)
    account = await run_sync(get_account_state_service().import_account)(request)
    return f"账号已导入：{account.label}\nID: {account.id}\n指纹: {account.browser_impersonate}"


async def _cmd_list_accounts(_: str) -> str:
    accounts = await run_sync(get_account_state_service().list_accounts)()
    if not accounts:
        return "暂无账号"
    return "\n".join(_format_account(a) for a in accounts)


async def _cmd_account_detail(args: str) -> str:
    account_id = args.strip()
    if not account_id:
        return "用法：glm 账号 <id>"
    detail = await run_sync(get_account_state_service().get_account_detail)(account_id)
    account = detail.account
    session = detail.session
    lines = [
        f"账号：{account.label}",
        f"ID: {account.id}",
        f"状态: {account.account_status} {account.account_status_message}",
        f"customer: {session.customer_number} / {session.customer_name}",
        f"org/project: {session.org_id or account.org_id} / {session.project_id or account.project_id}",
        f"指纹: {account.browser_impersonate}",
        f"购买模式: {session.purchase_mode}",
        f"当前套餐: {session.selected_product_id or '未选'}",
        f"定时: {'开' if account.schedule_enabled else '关'} {account.scheduled_start_time or ''}",
        f"ticket池: {account.ticket_pool_size} (间隔 {account.ticket_pool_drain_interval_ms}ms)",
    ]
    return "\n".join(lines)


async def _cmd_delete_account(args: str) -> str:
    account_id = args.strip()
    if not account_id:
        return "用法：glm 删除账号 <id>"
    await run_sync(get_account_state_service().delete_account)(account_id)
    return f"账号 {account_id} 已删除"


async def _cmd_bootstrap(args: str) -> str:
    account_id = args.strip()
    if not account_id:
        return "用法：glm 同步 <id>"
    detail = await run_sync(get_payment_service().bootstrap_account)(account_id)
    return f"同步完成：{detail.account.label}\n套餐数: {len(detail.session.products)}"


async def _cmd_refresh_fingerprint(args: str) -> str:
    account_id = args.strip()
    if not account_id:
        return "用法：glm 换指纹 <id>"
    detail = await run_sync(get_payment_service().bootstrap_account)(account_id, refresh_fingerprint=True)
    return f"已换指纹并同步：{detail.account.browser_impersonate}"


async def _cmd_products(args: str) -> str:
    account_id = args.strip()
    if not account_id:
        return "用法：glm 套餐 <id>"
    products = await run_sync(get_payment_service().load_products)(account_id)
    if not products:
        return "暂无套餐"
    lines = []
    for p in products:
        sold = " [售罄]" if p.sold_out else ""
        lines.append(f"{p.product_id}: {p.product_name} {p.plan_type} ¥{p.sale_price}{sold}")
    return "\n".join(lines)


async def _cmd_set_product(args: str) -> str:
    parts = args.split(None, 1)
    if len(parts) < 2:
        return "用法：glm 设置套餐 <id> <product_id>"
    account_id, product_id = parts
    pref = AccountPreferencesRequest(selected_product_id=product_id)
    detail = await run_sync(get_account_state_service().update_preferences)(account_id, pref)
    return f"已设置套餐：{detail.session.selected_product_id}"


async def _cmd_run(args: str) -> str:
    account_id = args.strip()
    if not account_id:
        return "用法：glm 启动 <id>"
    result = await run_sync(get_scheduler_service().start_account_flow)(account_id, source="manual")
    if not result.get("started"):
        return f"启动失败：{result.get('status')}"
    return f"已提交启动任务：{account_id}\n后台正在执行支付链路，完成后可发送 `glm 二维码 <id>` 查看。"


async def _cmd_qr(args: str) -> Message | str:
    account_id = args.strip()
    if not account_id:
        return "用法：glm 二维码 <id>"
    tasks = await run_sync(get_account_state_service().list_tasks)(account_id)
    if not tasks or not tasks[0].qr_base64:
        return "该账号暂无二维码"
    return Message(
        [
            MessageSegment.text(f"bizId: {tasks[0].biz_id}"),
            qr_base64_to_image_segment(tasks[0].qr_base64),
        ]
    )


async def _cmd_schedule(args: str) -> str:
    parts = args.split(None, 1)
    if len(parts) < 2:
        return "用法：glm 定时 <id> <HH:MM:SS>"
    account_id, time_str = parts
    pref = AccountPreferencesRequest(schedule_enabled=True, scheduled_start_time=time_str)
    await run_sync(get_account_state_service().update_preferences)(account_id, pref)
    return f"已开启定时：{time_str}"


async def _cmd_cancel_schedule(args: str) -> str:
    account_id = args.strip()
    if not account_id:
        return "用法：glm 取消定时 <id>"
    pref = AccountPreferencesRequest(schedule_enabled=False)
    await run_sync(get_account_state_service().update_preferences)(account_id, pref)
    return f"账号 {account_id} 定时已关闭"


async def _cmd_pause(args: str) -> str:
    account_id = args.strip()
    if not account_id:
        return "用法：glm 暂停 <id>"
    result = await run_sync(get_scheduler_service().request_pause)(account_id)
    return f"暂停结果：{result.get('status')}"


async def _cmd_status(_: str) -> str:
    health = get_payment_service().health_payload()
    lines = [
        f"整体状态: {health.get('status')}",
        f"Transport: {health.get('transport')}",
        f"网络出口: {health.get('network', {}).get('mode')}",
    ]
    ocr = health.get("ocr") or {}
    lines.append(f"OCR: {'可用' if ocr.get('available') else '不可用'} (workers={ocr.get('workers')})")
    proxy = health.get("proxy") or {}
    lines.append(f"代理池: {'可用' if proxy.get('available') else '不可用'} ({proxy.get('message', '')})")
    problems = health.get("problems") or []
    if problems:
        lines.append("问题：")
        lines.extend(f"  - {p}" for p in problems)
    return "\n".join(lines)


async def _cmd_switch_egress(args: str) -> str:
    mode = args.strip().lower()
    if mode not in ("local", "proxy_pool"):
        return "用法：glm 切换出口 <local|proxy_pool>"
    result = get_network_mode_service().set_mode(mode)
    return f"出口已切换为：{result.get('mode')}"


async def _cmd_logs(_: str) -> str:
    def _read() -> str:
        settings = get_settings()
        date_part = datetime.now().astimezone().strftime("%Y-%m-%d")
        log_path = settings.runtime_logs_dir / f"events-{date_part}.jsonl"
        if not log_path.exists():
            return "今日暂无日志"
        lines = log_path.read_text(encoding="utf-8").splitlines()
        recent = lines[-30:]
        return "\n".join(recent) or "今日暂无日志"

    return await run_sync(_read)()


async def _cmd_settings(_: str) -> str:
    settings = get_settings()
    lines = [
        "当前生效配置：",
        f"  数据目录: {settings.data_dir}",
        f"  日志目录: {settings.runtime_logs_dir}",
        f"  日志级别: {settings.runtime_log_level}",
        f"  日志保留天数: {settings.runtime_log_retention_days}",
        f"  OCR workers: {settings.tencent_ocr_workers}",
        f"  OCR timeout: {settings.tencent_ocr_timeout_seconds}s",
        f"  OCR min confidence: {settings.tencent_captcha_min_confidence}",
        f"  网络出口模式: {settings.network_egress_mode}",
        f"  fallback proxy: {settings.fallback_proxy_url}",
        f"  fallback ticket-only: {settings.fallback_proxy_ticket_pool_only}",
        f"  proxy pool config: {settings.proxy_pool_config_path}",
        f"  BigModel API: {settings.bigmodel_api_base}",
        f"  Captcha aid: {settings.tencent_captcha_aid}",
        f"  Captcha domain: {settings.tencent_captcha_domain}",
    ]
    return "\n".join(lines)


async def notify_superuser_qr() -> None:
    """Send QR images for completed scheduled flows to all superusers."""
    from nonebot import get_bot, get_driver

    scheduler = get_scheduler_service()
    tasks = scheduler.pop_completed_tasks()
    if not tasks:
        return

    try:
        bot = get_bot()
    except Exception:
        logger.warning("no bot available for superuser notification")
        return

    settings = get_settings()
    if not getattr(settings, "glm_buyer_notify_superuser_on_schedule", True):
        return

    for account_id, biz_id, qr_base64 in tasks:
        if not qr_base64:
            continue
        try:
            account = await run_sync(get_account_state_service().get_account)(account_id)
            label = account.label
        except Exception:
            label = account_id
        message = Message(
            [
                MessageSegment.text(f"定时任务完成\n账号: {label}\nbizId: {biz_id}\n二维码："),
                qr_base64_to_image_segment(qr_base64),
            ]
        )
        for user_id in get_driver().config.superusers:
            try:
                await bot.send_private_msg(user_id=int(user_id), message=message)
            except Exception as exc:
                logger.warning("failed to notify superuser %s: %s", user_id, exc)

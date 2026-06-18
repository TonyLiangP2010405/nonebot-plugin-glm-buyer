<div align="center">

# nonebot-plugin-glm-buyer

通过 NoneBot2 / OneBot v11 私聊控制 GLM Coding 账号抢购与支付二维码。

[![license](https://img.shields.io/github/license/TonyLiangP2010405/nonebot-plugin-glm-buyer.svg)](./LICENSE)
[![pypi](https://img.shields.io/pypi/v/nonebot-plugin-glm-buyer.svg)](https://pypi.org/project/nonebot-plugin-glm-buyer/)
[![python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)

</div>

本插件源自 `glm_buyer/glm-coding`（AegisFlow），移除了 Web 界面，所有交互改为 QQ 私聊指令；定时任务到期后会自动把支付二维码私聊发给 superuser。

## 特性

- 仅支持 **superuser 私聊**，群聊/临时会话均会被拒绝
- 原 GLM 协议默认值已内嵌到插件代码，零配置即可导入
- 账号导入、套餐选择、立即抢购、二维码查看、定时任务、暂停/恢复
- 内置代理池可自动启动（通过 `proxy_pool.yaml` 配置）
- 定时任务触发后自动私聊发送支付二维码

## 安装

```bash
pip install nonebot-plugin-glm-buyer
```

或在 NoneBot 项目目录下：

```bash
nb plugin install nonebot-plugin-glm-buyer
```

然后在 `pyproject.toml` 的 `[tool.nonebot]` 中添加：

```toml
plugins = ["nonebot_plugin_glm_buyer"]
```

## 配置

在 NoneBot 的 `.env` 文件中按需填写：

| 配置项 | 必填 | 默认值 | 说明 |
| :--- | :---: | :--- | :--- |
| `glm_buyer_data_dir` | 否 | 空 | 数据目录；留空使用 nonebot-plugin-localstore 的插件数据目录 |
| `glm_buyer_ocr_workers` | 否 | 4 | OCR 进程数 |
| `glm_buyer_log_level` | 否 | INFO | 运行时日志级别 |
| `glm_buyer_log_retention_days` | 否 | 7 | 运行时日志保留天数 |
| `glm_buyer_network_egress_mode` | 否 | local | 网络出口模式：`local` 或 `proxy_pool` |
| `glm_buyer_fallback_proxy_url` | 否 | `http://127.0.0.1:17286` | 备用代理地址 |
| `glm_buyer_fallback_proxy_ticket_pool_only` | 否 | false | 备用代理是否只用于抢票池 |
| `glm_buyer_proxy_pool_config` | 否 | `proxy_pool.yaml` | 代理池配置文件路径 |
| `glm_buyer_tesseract_ocr_enabled` | 否 | true | 是否启用 Tesseract 类 OCR |
| `glm_buyer_tesseract_ocr_timeout` | 否 | 6 | OCR 超时（秒） |
| `glm_buyer_tesseract_ocr_min_confidence` | 否 | 0.55 | OCR 最低置信度 |
| `glm_buyer_tesseract_captcha_max_retries` | 否 | 3 | 验证码最大重试次数 |
| `glm_buyer_notify_superuser_on_schedule` | 否 | true | 定时任务完成是否通知 superuser |

BigModel 域名、验证码 aid、浏览器指纹等协议参数已硬编码，一般无需修改。

## 使用

私聊机器人并 `@` 它（或按适配器规则视为 `to_me`），发送：

```text
glm 帮助
```

### 指令表

| 指令 | 说明 |
| :--- | :--- |
| `glm 帮助` | 显示帮助 |
| `glm 查看全部设置` | 查看当前生效的核心设置 |
| `glm 添加账号 <json>` | 导入账号（token/cookie/指纹等） |
| `glm 账号列表` | 列出所有账号 |
| `glm 账号 <id>` | 查看账号详情 |
| `glm 删除账号 <id>` | 删除账号 |
| `glm 同步 <id>` | 同步/预热账号状态 |
| `glm 换指纹 <id>` | 刷新浏览器指纹 |
| `glm 套餐 <id>` | 查看可选套餐 |
| `glm 设置套餐 <id> <product_id>` | 设置账号要抢购的套餐 |
| `glm 启动 <id>` | 立即执行一次抢购流程 |
| `glm 二维码 <id>` | 获取当前支付二维码 |
| `glm 定时 <id> <cron>` | 设置定时任务（秒级 cron，如 `0 30 14 * * *`） |
| `glm 取消定时 <id>` | 取消账号定时任务 |
| `glm 暂停 <id>` | 暂停当前运行/定时任务 |
| `glm 状态 <id>` | 查看账号运行状态 |
| `glm 切换出口 <mode>` | 切换网络出口：`local` 或 `proxy_pool` |
| `glm 日志 <id>` | 查看账号最近日志 |

> `<id>` 为账号导入后返回的短 ID。

## 注意事项

- 本插件涉及支付流程，请仅在受信任环境、受信任账号下使用。
- 定时任务使用 `nonebot-plugin-apscheduler` 的调度器，每秒轮询一次。
- 依赖 `node` 用于腾讯验证码 TDC 收集，请确保环境中有可用 Node.js。
- 验证码 OCR 依赖 `rapidocr`、`onnxruntime`、`opencv-python`，已在安装依赖中列出。

## License

MIT

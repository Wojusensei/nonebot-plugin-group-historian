import asyncio
from datetime import datetime, timedelta
from nonebot import on_command, on_message, on_notice, require, get_plugin_config, get_driver
from nonebot.adapters.onebot.v11 import (
    Bot,
    GroupMessageEvent,
    GroupRecallNoticeEvent,
    MessageSegment,
)
from nonebot.plugin import PluginMetadata
from nonebot.log import logger


# ————————————————————————————
# 依赖声明
# ————————————————————————————

require("nonebot_plugin_orm")
require("nonebot_plugin_apscheduler")
require("nonebot_plugin_localstore")


# ————————————————————————————
# 元数据 插件身份证
# ————————————————————————————

__plugin_meta__ = PluginMetadata(
    name="群聊史官",
    description="统计每日群聊发言字数 生成话痨榜图片",
    usage="在群里发送 话痨榜 查看昨日排行\n发送 今日话痨榜 查看今日实时排行\n可加页码 例如 话痨榜 2",
    type="application",
    homepage="https://github.com/Wojusensei/nonebot-plugin-group-historian",
    config=None,
    supported_adapters={"~onebot.v11"},
)


# ————————————————————————————
# 导入插件内部模块 放在元数据之后
# ————————————————————————————

from .config import Config
from .data import add_message, delete_last_message, get_daily_ranking, clean_old_data
from .image import create_ranking_image


# ————————————————————————————
# 加载配置 使用 get_plugin_config
# ————————————————————————————

config = get_plugin_config(Config)


# ————————————————————————————
# 消息缓存 用于撤回时扣除字数
# key 是消息ID value 是 (群号, QQ号, 字数)
# ————————————————————————————

message_cache = {}


# ————————————————————————————
# 监听群消息 记录字数
# ————————————————————————————

msg_handler = on_message(block=False)


@msg_handler.handle()
async def handle_message(event: GroupMessageEvent):
    text = event.get_plaintext()

    # 过滤纯图片表情等无文字消息
    if not text or not text.strip():
        return

    length = len(text.replace(" ", ""))
    group_id = str(event.group_id)
    user_id = str(event.user_id)
    nickname = event.sender.card or event.sender.nickname or user_id

    await add_message(group_id, user_id, nickname, length)

    # 存入缓存 供撤回时扣除
    message_cache[str(event.message_id)] = (group_id, user_id, length)


# ————————————————————————————
# 监听群撤回 扣除字数
# ————————————————————————————

recall_handler = on_notice(block=False)


@recall_handler.handle()
async def handle_recall(event: GroupRecallNoticeEvent):
    msg_id = str(event.message_id)
    if msg_id in message_cache:
        group_id, user_id, length = message_cache[msg_id]
        await delete_last_message(group_id, user_id, length)
        del message_cache[msg_id]


# ————————————————————————————
# 话痨榜命令
# 默认查昨日 加今日查今天
# ————————————————————————————

rank_cmd = on_command("话痨榜", aliases={"今日话痨榜"}, block=True)


@rank_cmd.handle()
async def handle_rank(event: GroupMessageEvent, bot: Bot):
    raw = event.get_plaintext().strip()
    parts = raw.split()

    # 判断查今天还是昨天
    is_today = "今日" in raw

    # 解析页码
    page = 1
    for p in parts:
        if p.isdigit():
            page = int(p)
            if page < 1:
                page = 1
            break

    # 确定日期
    date = datetime.now().date() if is_today else (datetime.now().date() - timedelta(days=1))

    # 获取排行榜
    ranking = await get_daily_ranking(str(event.group_id), date)

    if not ranking:
        day_text = "今天" if is_today else "昨天"
        await rank_cmd.finish(f"{day_text}还没有人说话呢", at_sender=True)
        return

    # 生成图片 放入线程池避免阻塞事件循环
    rank_count = config.historian_rank_count
    img_bytes = await asyncio.to_thread(
        create_ranking_image,
        ranking,
        page=page,
        rank_count=rank_count,
    )

    await rank_cmd.send(MessageSegment.image(img_bytes))


# ————————————————————————————
# 定时任务 每日凌晨清理旧数据
# ————————————————————————————

from nonebot_plugin_apscheduler import scheduler


@scheduler.scheduled_job("cron", hour=0, minute=0, id="clean_old_historian_data")
async def scheduled_clean():
    await clean_old_data(config.historian_data_retention_days)


# ————————————————————————————
# 启动日志
# ————————————————————————————

logger.info("群聊史官 插件已加载")
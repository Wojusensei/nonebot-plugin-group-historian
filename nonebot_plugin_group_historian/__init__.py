import re
from typing import List, Optional, Tuple

from nonebot import on_command, on_message, require, get_plugin_config, get_driver
from nonebot.adapters.onebot.v11 import Bot, Event, GroupMessageEvent, MessageSegment
from nonebot.plugin import PluginMetadata
from nonebot.log import logger

from .config import Config
from .data import add_message, get_daily_ranking, clean_old_data

# ========================
# 依赖声明
# ========================
require("nonebot_plugin_localstore")
require("nonebot_plugin_orm")

# ========================
# 插件元数据
# ========================
__plugin_meta__ = PluginMetadata(
    name="群聊史官",
    description="统计群成员每日发言字数，生成话痨榜图片",
    usage="发送「今日话痨榜」获取排行榜图片",
    type="application",
    homepage="https://github.com/Wojusensei/nonebot-plugin-group-historian",
    config=Config,
    supported_adapters={"~onebot.v11"},
)

# ========================
# 读取配置
# ========================
config = get_plugin_config(Config)

# ========================
# 工具函数
# ========================

def count_words(text: str) -> int:
    """统计中文、字母、数字的字符数"""
    return len(re.findall(r"[\u4e00-\u9fa5a-zA-Z0-9]", text))


def get_user_nickname(event: GroupMessageEvent) -> str:
    """从事件发送者信息获取昵称（优先群名片，其次 QQ 昵称），无需额外 API 调用"""
    sender = event.sender
    return (sender.card or sender.nickname or str(event.user_id)) if sender else str(event.user_id)


# ========================
# 命令注册
# ========================
historian_cmd = on_command("今日话痨榜", aliases={"话痨榜"}, priority=10, block=True)


@historian_cmd.handle()
async def handle_historian(event: Event):
    if not isinstance(event, GroupMessageEvent):
        await historian_cmd.finish("该命令仅支持群聊")

    group_id = event.group_id
    try:
        ranking = await get_daily_ranking(str(group_id))
    except Exception as e:
        logger.error(f"获取话痨榜失败: {e}")
        await historian_cmd.finish("获取话痨榜失败，请稍后再试")

    if not ranking:
        await historian_cmd.finish("今天还没有人发言哦～")

    try:
        from .image import create_ranking_image
        img_bytes = create_ranking_image(ranking, page=1, rank_count=config.historian_rank_count)
        await historian_cmd.send(MessageSegment.image(img_bytes))
    except Exception as e:
        logger.error(f"生成话痨榜图片失败: {e}")
        await historian_cmd.finish("生成话痨榜图片失败，请稍后再试")

    await historian_cmd.finish("以上是今日话痨榜")


# ========================
# 消息监听器
# ========================
msg_recorder = on_message(priority=5, block=False)


@msg_recorder.handle()
async def record_message(event: Event):
    if not isinstance(event, GroupMessageEvent):
        return
    raw = event.get_plaintext().strip()
    # 跳过命令消息本身（含命令前缀 / 等）
    if raw.startswith(("/", "今日话痨榜", "话痨榜")):
        return
    text = raw
    if not text:
        return
    cnt = count_words(text)
    if cnt == 0:
        return
    nickname = get_user_nickname(event)
    await add_message(str(event.group_id), str(event.user_id), nickname, cnt)


# ========================
# 启动时清理旧数据
# ========================
driver = get_driver()


@driver.on_startup
async def startup():
    retention_days = config.historian_data_retention_days
    await clean_old_data(retention_days)
    logger.info(f"群聊史官已启动，数据保留 {retention_days} 天")

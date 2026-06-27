from datetime import date
from pathlib import Path
from typing import List, Tuple

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

import nonebot_plugin_localstore as store

# ========================
# 数据目录
# ========================
DATA_DIR = store.get_plugin_data_dir()
DATA_DIR.mkdir(parents=True, exist_ok=True)

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
async def get_message_text(event: GroupMessageEvent) -> str:
    text = ""
    for seg in event.get_message():
        if seg.type == "text":
            text += str(seg)
    return text

async def count_words(text: str) -> int:
    import re
    return len(re.findall(r'[\u4e00-\u9fa5a-zA-Z0-9]', text))

async def get_user_nickname(event: GroupMessageEvent) -> str:
    """获取发送者昵称（优先群名片，其次 QQ 昵称）"""
    try:
        from nonebot import get_bot
        bot = get_bot()
        info = await bot.get_group_member_info(
            group_id=event.group_id,
            user_id=event.user_id
        )
        return info.get("card") or info.get("nickname") or str(event.user_id)
    except Exception:
        return str(event.user_id)

# ========================
# 图片生成（适配 data.py 返回格式）
# ========================
async def generate_ranking_image(ranking: List[Tuple[str, str, int]], group_id: int) -> Path:
    from PIL import Image, ImageDraw, ImageFont
    import os

    if not ranking:
        return None

    width, height = 600, 100 + len(ranking) * 40
    img = Image.new('RGB', (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    try:
        if os.name == 'nt':
            font = ImageFont.truetype("simhei.ttf", 20)
        else:
            font = ImageFont.load_default()
    except:
        font = ImageFont.load_default()

    y = 10
    draw.text((10, y), f"群 {group_id} 今日话痨榜", fill=(0, 0, 0), font=font)
    y += 30
    for idx, (user_id, nickname, total) in enumerate(ranking[:10], 1):
        display = nickname if nickname else str(user_id)
        draw.text((10, y), f"{idx}. {display}  {total} 字", fill=(0, 0, 0), font=font)
        y += 35

    img_path = DATA_DIR / f"ranking_{group_id}_{date.today()}.png"
    img.save(img_path)
    return img_path

# ========================
# 命令注册
# ========================
historian_cmd = on_command("今日话痨榜", aliases={"话痨榜"}, priority=10, block=True)

@historian_cmd.handle()
async def handle_historian(event: GroupMessageEvent):
    group_id = event.group_id
    ranking = await get_daily_ranking(str(group_id))
    if not ranking:
        await historian_cmd.finish("今天还没有人发言哦～")
    img_path = await generate_ranking_image(ranking, group_id)
    if img_path:
        await historian_cmd.send(MessageSegment.image(img_path))
    await historian_cmd.finish("以上是今日话痨榜")

# ========================
# 消息监听器
# ========================
msg_recorder = on_message(priority=5, block=False)

@msg_recorder.handle()
async def record_message(bot: Bot, event: Event):
    if not isinstance(event, GroupMessageEvent):
        return
    raw = event.get_plaintext().strip()
    if raw.startswith(("今日话痨榜", "话痨榜")):
        return
    text = await get_message_text(event)
    if not text:
        return
    cnt = await count_words(text)
    if cnt == 0:
        return
    nickname = await get_user_nickname(event)
    await add_message(str(event.group_id), str(event.user_id), nickname, cnt)

# ========================
# 启动时清理旧数据
# ========================
driver = get_driver()

@driver.on_startup
async def startup():
    retention_days = getattr(config, "historian_data_retention_days", 30)
    await clean_old_data(retention_days)
    logger.info(f"群聊史官已启动，数据保留 {retention_days} 天")
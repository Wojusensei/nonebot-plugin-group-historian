import asyncio
import sqlite3
import re
from datetime import date, timedelta
from pathlib import Path
from typing import List, Tuple

from nonebot import on_command, on_message, require, get_plugin_config, get_driver
from nonebot.adapters.onebot.v11 import Bot, Event, GroupMessageEvent, MessageSegment
from nonebot.plugin import PluginMetadata
from nonebot.log import logger

from .config import Config

# ========================
# localstore 
# ========================
require("nonebot_plugin_localstore")
import nonebot_plugin_localstore as store

DATA_DIR = store.get_plugin_data_dir()
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "historian.db"

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
#  数据库操作asyncio.to_thread）
# ========================
def init_db():
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS daily_words (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            word_count INTEGER DEFAULT 0,
            UNIQUE(group_id, user_id, date)
        )
    ''')
    # 创建索引
    c.execute('CREATE INDEX IF NOT EXISTS idx_date ON daily_words(date)')
    conn.commit()
    conn.close()

async def async_init_db():
    await asyncio.to_thread(init_db)

async def add_words(group_id: int, user_id: int, date_str: str, count: int):
    def _add():
        conn = sqlite3.connect(str(DB_PATH))
        c = conn.cursor()
        c.execute('''
            INSERT INTO daily_words (group_id, user_id, date, word_count)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(group_id, user_id, date)
            DO UPDATE SET word_count = word_count + excluded.word_count
        ''', (group_id, user_id, date_str, count))
        conn.commit()
        conn.close()
    await asyncio.to_thread(_add)

async def get_today_ranking(group_id: int, date_str: str, limit: int) -> List[Tuple[int, int]]:
    def _get():
        conn = sqlite3.connect(str(DB_PATH))
        c = conn.cursor()
        c.execute('''
            SELECT user_id, word_count FROM daily_words
            WHERE group_id = ? AND date = ?
            ORDER BY word_count DESC
            LIMIT ?
        ''', (group_id, date_str, limit))
        rows = c.fetchall()
        conn.close()
        return rows
    return await asyncio.to_thread(_get)

async def clean_old_data(days: int):
    """清理超过指定天数的数据"""
    def _clean():
        conn = sqlite3.connect(str(DB_PATH))
        c = conn.cursor()
        cutoff_date = (date.today() - timedelta(days=days)).isoformat()
        c.execute('DELETE FROM daily_words WHERE date < ?', (cutoff_date,))
        conn.commit()
        conn.close()
    await asyncio.to_thread(_clean)

# ========================
# 消息文本提取与字数统计
# ========================
async def get_message_text(event: GroupMessageEvent) -> str:
    text = ""
    for seg in event.get_message():
        if seg.type == "text":
            text += str(seg)
    return text

async def count_words(text: str) -> int:
    # 统计中文字符、字母、数字（可根据需要调整）
    return len(re.findall(r'[\u4e00-\u9fa5a-zA-Z0-9]', text))

# ========================
#  图片生成
# ========================
async def generate_ranking_image(ranking: List[Tuple[int, int]], group_id: int, limit: int) -> Path:
    from PIL import Image, ImageDraw, ImageFont
    import os

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
    draw.text((10, y), f"群 {group_id} 今日话痨榜（TOP{limit}）", fill=(0, 0, 0), font=font)
    y += 30
    for idx, (user_id, words) in enumerate(ranking, 1):
        draw.text((10, y), f"{idx}. QQ: {user_id}  {words} 字", fill=(0, 0, 0), font=font)
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
    today_str = date.today().isoformat()
    limit = config.historian_rank_count  # 使用配置的显示人数
    ranking = await get_today_ranking(group_id, today_str, limit)
    if not ranking:
        await historian_cmd.finish("今天还没有人发言哦～")
    img_path = await generate_ranking_image(ranking, group_id, limit)
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
    # 排除命令本身
    if raw.startswith(("今日话痨榜", "话痨榜")):
        return
    text = await get_message_text(event)
    if not text:
        return
    cnt = await count_words(text)
    if cnt == 0:
        return
    await add_words(event.group_id, event.user_id, date.today().isoformat(), cnt)

# ========================
# 启动时初始化数据库，清理旧数据
# ========================
driver = get_driver()
@driver.on_startup
async def startup():
    await async_init_db()
    # 清理超过保留天数的数据
    retention_days = config.historian_data_retention_days
    await clean_old_data(retention_days)
    logger.info(f"群聊史官数据库初始化完成，数据保留 {retention_days} 天")
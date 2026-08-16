"""数据层测试（真实 sqlite via nonebot-plugin-orm）"""
from datetime import datetime, timedelta

from nonebot_plugin_group_historian.data import (
    add_message,
    get_daily_ranking,
    clean_old_data,
)


async def test_add_and_rank(db):
    """回归：函数内重复定义模型曾导致第二条消息即崩溃"""
    await add_message("100", "1", "甲", 10)
    await add_message("100", "1", "甲新名片", 5)
    await add_message("100", "2", "乙", 30)
    await add_message("200", "3", "丙", 99)  # 其他群不应出现

    ranking = await get_daily_ranking("100")
    assert [(r[0], r[2]) for r in ranking] == [("2", 30), ("1", 15)]
    # 昵称取最大值（字典序），同群同日聚合正确
    assert ranking[0][1] == "乙"


async def test_ranking_empty(db):
    assert await get_daily_ranking("999") == []


async def test_ranking_specific_date(db):
    old_date = datetime.now().date() - timedelta(days=3)
    from nonebot_plugin_group_historian.data import DailyMessage
    from nonebot_plugin_orm import get_session

    async with get_session() as session:
        session.add(DailyMessage(group_id="100", user_id="1", nickname="旧",
                                 message_length=77, timestamp=old_date))
        await session.commit()

    assert await get_daily_ranking("100") == []
    assert await get_daily_ranking("100", date=old_date) == [("1", "旧", 77)]


async def test_clean_old_data(db):
    old_date = datetime.now().date() - timedelta(days=40)
    from nonebot_plugin_group_historian.data import DailyMessage
    from nonebot_plugin_orm import get_session

    async with get_session() as session:
        session.add(DailyMessage(group_id="100", user_id="1", nickname="旧",
                                 message_length=50, timestamp=old_date))
        session.add(DailyMessage(group_id="100", user_id="2", nickname="新",
                                 message_length=60, timestamp=datetime.now().date()))
        await session.commit()

    await clean_old_data(30)
    ranking = await get_daily_ranking("100")
    assert [(r[0], r[2]) for r in ranking] == [("2", 60)]

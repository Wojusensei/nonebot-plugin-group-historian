from datetime import date as Date, datetime, timedelta
from typing import List, Optional, Tuple

from sqlalchemy import Date as SaDate, Integer, String, delete, func, select
from sqlalchemy.orm import Mapped, mapped_column

from nonebot import require

# 声明依赖
require("nonebot_plugin_orm")
from nonebot_plugin_orm import Model, get_session


class DailyMessage(Model):
    """每日消息字数记录"""

    __tablename__ = "daily_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    group_id: Mapped[str] = mapped_column(String, nullable=False)
    user_id: Mapped[str] = mapped_column(String, nullable=False)
    nickname: Mapped[Optional[str]] = mapped_column(String)
    message_length: Mapped[int] = mapped_column(Integer, default=0)
    timestamp: Mapped[Date] = mapped_column(SaDate, nullable=False)


async def add_message(group_id: str, user_id: str, nickname: str, length: int):
    """记录一条消息的字数"""
    async with get_session() as session:
        session.add(
            DailyMessage(
                group_id=group_id,
                user_id=user_id,
                nickname=nickname,
                message_length=length,
                timestamp=datetime.now().date(),
            )
        )
        await session.commit()


async def get_daily_ranking(
    group_id: str, date: Optional[Date] = None
) -> List[Tuple[str, Optional[str], int]]:
    """获取某群某日的发言字数排行榜：[(user_id, nickname, total), ...]"""
    if date is None:
        date = datetime.now().date()

    async with get_session() as session:
        result = await session.execute(
            select(
                DailyMessage.user_id,
                func.max(DailyMessage.nickname).label("nickname"),
                func.sum(DailyMessage.message_length).label("total"),
            )
            .where(
                DailyMessage.group_id == group_id,
                DailyMessage.timestamp == date,
            )
            .group_by(DailyMessage.user_id)
            .order_by(func.sum(DailyMessage.message_length).desc())
        )
        return [(row.user_id, row.nickname, row.total) for row in result.fetchall()]


async def clean_old_data(retention_days: int):
    """删除超过保留期的数据"""
    cutoff = datetime.now().date() - timedelta(days=retention_days)
    async with get_session() as session:
        await session.execute(delete(DailyMessage).where(DailyMessage.timestamp < cutoff))
        await session.commit()

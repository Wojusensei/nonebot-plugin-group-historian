from datetime import datetime, timedelta
from sqlalchemy import Column, Integer, String, Date, func
from nonebot import require

# 声明依赖
require("nonebot_plugin_orm")


def _get_model():
    """延迟导入 Model，避免模块加载时触发 get_plugin_data_dir"""
    from nonebot_plugin_orm import Model
    return Model


async def add_message(group_id: str, user_id: str, nickname: str, length: int):
    from nonebot_plugin_orm import get_scoped_session

    class DailyMessage(_get_model()):
        __tablename__ = "daily_messages"

        id = Column(Integer, primary_key=True, autoincrement=True)
        group_id = Column(String, nullable=False)
        user_id = Column(String, nullable=False)
        nickname = Column(String)
        message_length = Column(Integer, default=0)
        timestamp = Column(Date, nullable=False)

    async with get_scoped_session() as session:
        record = DailyMessage(
            group_id=group_id,
            user_id=user_id,
            nickname=nickname,
            message_length=length,
            timestamp=datetime.now().date(),
        )
        session.add(record)
        await session.commit()


async def delete_last_message(group_id: str, user_id: str, length: int):
    from nonebot_plugin_orm import get_scoped_session

    class DailyMessage(_get_model()):
        __tablename__ = "daily_messages"
        id = Column(Integer, primary_key=True, autoincrement=True)
        group_id = Column(String, nullable=False)
        user_id = Column(String, nullable=False)
        nickname = Column(String)
        message_length = Column(Integer, default=0)
        timestamp = Column(Date, nullable=False)

    today = datetime.now().date()
    async with get_scoped_session() as session:
        record = await session.execute(
            DailyMessage.__table__.select()
            .where(
                DailyMessage.group_id == group_id,
                DailyMessage.user_id == user_id,
                DailyMessage.message_length == length,
                DailyMessage.timestamp == today,
            )
            .order_by(DailyMessage.id.desc())
            .limit(1)
        )
        row = record.fetchone()
        if row:
            await session.execute(
                DailyMessage.__table__.delete().where(DailyMessage.id == row.id)
            )
            await session.commit()


async def get_daily_ranking(group_id: str, date=None) -> list:
    from nonebot_plugin_orm import get_scoped_session

    class DailyMessage(_get_model()):
        __tablename__ = "daily_messages"
        id = Column(Integer, primary_key=True, autoincrement=True)
        group_id = Column(String, nullable=False)
        user_id = Column(String, nullable=False)
        nickname = Column(String)
        message_length = Column(Integer, default=0)
        timestamp = Column(Date, nullable=False)

    if date is None:
        date = datetime.now().date()

    async with get_scoped_session() as session:
        result = await session.execute(
            DailyMessage.__table__.select()
            .with_only_columns(
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
        rows = result.fetchall()
        return [(row.user_id, row.nickname, row.total) for row in rows]


async def clean_old_data(retention_days: int):
    from nonebot_plugin_orm import get_scoped_session

    class DailyMessage(_get_model()):
        __tablename__ = "daily_messages"
        id = Column(Integer, primary_key=True, autoincrement=True)
        group_id = Column(String, nullable=False)
        user_id = Column(String, nullable=False)
        nickname = Column(String)
        message_length = Column(Integer, default=0)
        timestamp = Column(Date, nullable=False)

    cutoff = datetime.now().date() - timedelta(days=retention_days)
    async with get_scoped_session() as session:
        await session.execute(
            DailyMessage.__table__.delete().where(DailyMessage.timestamp < cutoff)
        )
        await session.commit()
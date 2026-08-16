import os
import sys
import tempfile
from pathlib import Path

# 插件根目录加入 sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# localstore / orm 会在插件导入时确定数据目录，先重定向到临时目录
_tmp = tempfile.mkdtemp(prefix="group_historian_test_")
os.chdir(_tmp)
os.environ["DRIVER"] = "~none"
os.environ["LOCALSTORE_BASE_DIR"] = _tmp
os.environ["LOCALSTORE_DATA_DIR"] = str(Path(_tmp) / "data")
os.environ["LOCALSTORE_CONFIG_DIR"] = str(Path(_tmp) / "config")
os.environ["LOCALSTORE_CACHE_DIR"] = str(Path(_tmp) / "cache")
# orm 使用临时 sqlite 数据库；测试中由 fixture 手动建表，关闭启动时的交互式迁移检查
os.environ["SQL_DIALECT"] = "sqlite"
os.environ["SQLALCHEMY_DATABASE_URL"] = "sqlite+aiosqlite:///" + str(Path(_tmp) / "test.db")
os.environ["ALEMBIC_STARTUP_CHECK"] = "false"

import nonebot
from nonebot.adapters.onebot.v11 import Adapter as OnebotV11Adapter

nonebot.init()
driver = nonebot.get_driver()
driver.register_adapter(OnebotV11Adapter)
nonebot.load_plugin("nonebot_plugin_group_historian")

import pytest

from nonebot_plugin_group_historian.data import DailyMessage


@pytest.fixture
async def db(app):
    """确保表存在并清空数据（nonebug 不触发 startup 迁移，手动建表）"""
    from sqlalchemy import delete as sa_delete
    from nonebot_plugin_orm import get_scoped_session

    session = get_scoped_session()
    async with session() as s:
        conn = await s.connection()
        await conn.run_sync(DailyMessage.metadata.create_all, checkfirst=True)
        await s.execute(sa_delete(DailyMessage))
        await s.commit()
    yield

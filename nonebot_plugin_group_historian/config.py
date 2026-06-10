from pydantic import BaseModel, Field


class Config(BaseModel):
    """插件配置，用户可在 .env 文件中设置"""

    historian_rank_count: int = Field(
        default=10,
        description="排行榜每页显示的人数"
    )
    historian_data_retention_days: int = Field(
        default=30,
        description="数据保留天数，超过自动清理"
    )
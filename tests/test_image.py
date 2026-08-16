"""图片生成测试"""
from nonebot_plugin_group_historian.image import create_ranking_image, _load_font


def test_font_load_no_crash():
    font = _load_font(20)
    assert font is not None


def test_ranking_image_bytes():
    ranking = [(str(i), f"成员{i}", 100 - i) for i in range(1, 16)]
    data = create_ranking_image(ranking, page=1, rank_count=10)
    assert data[:8] == b"\x89PNG\r\n\x1a\n"  # PNG 魔数
    assert len(data) > 5000


def test_ranking_image_paging():
    ranking = [("1", "甲", 10), ("2", "乙", 5)]
    # 每页 10 人、第 2 页为空数据也不应崩溃
    data = create_ranking_image(ranking, page=2, rank_count=10)
    assert data[:8] == b"\x89PNG\r\n\x1a\n"


def test_ranking_image_nickname_fallback():
    data = create_ranking_image([("10086", None, 3)])
    assert data[:8] == b"\x89PNG\r\n\x1a\n"

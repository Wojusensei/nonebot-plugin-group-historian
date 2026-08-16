import io
from pathlib import Path
from typing import List, Optional, Tuple

from PIL import Image, ImageDraw, ImageFont
from nonebot.log import logger
from nonebot import require

require("nonebot_plugin_localstore")
from nonebot_plugin_localstore import get_plugin_data_dir

# ————————————————————————————
# 资源路径
# 用户可以把自定义字体 font.ttf / 背景图 background.png 放到插件数据目录下
# ————————————————————————————

DATA_DIR = get_plugin_data_dir()
FONT_PATH = DATA_DIR / "font.ttf"
BG_PATH = DATA_DIR / "background.png"

# 系统自带的中文字体（Windows / macOS / Linux），按顺序尝试
_SYSTEM_CJK_FONTS = [
    "C:/Windows/Fonts/msyh.ttc",
    "C:/Windows/Fonts/simhei.ttf",
    "/System/Library/Fonts/PingFang.ttc",
    "/System/Library/Fonts/Hiragino Sans GB.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJKsc-Regular.otf",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
    "/usr/share/fonts/wenquanyi/wqy-microhei/wqy-microhei.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
]

_warned_no_font = False


def _load_font(size: int) -> ImageFont.ImageFont:
    """优先使用用户字体，其次系统中文字体，最后回退默认字体"""
    global _warned_no_font
    if FONT_PATH.exists():
        try:
            return ImageFont.truetype(str(FONT_PATH), size)
        except Exception as e:
            logger.warning(f"自定义字体 {FONT_PATH} 加载失败: {e}")
    for path in _SYSTEM_CJK_FONTS:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    if not _warned_no_font:
        logger.warning("未找到中文字体，话痨榜图片中文可能显示为方框；"
                       "可将字体文件放置到插件数据目录的 font.ttf")
        _warned_no_font = True
    return ImageFont.load_default()


# ————————————————————————————
# 生成排行榜图片
# ranking: [(user_id, nickname, total), ...]
# page: 页码，从 1 开始
# rank_count: 每页人数
# 返回图片的 bytes
# ————————————————————————————

def create_ranking_image(
    ranking: List[Tuple[str, Optional[str], int]],
    page: int = 1,
    rank_count: int = 10,
) -> bytes:
    # ———————— 计算分页 ————————
    start = (page - 1) * rank_count
    end = start + rank_count
    page_data = ranking[start:end]

    # ———————— 画布尺寸 ————————
    width = 800
    header_height = 120
    row_height = 90
    footer_height = 80
    height = header_height + row_height * rank_count + footer_height

    # ———————— 背景图 ————————
    if BG_PATH.exists():
        bg = Image.open(BG_PATH).convert("RGBA")
        bg = bg.resize((width, height), Image.LANCZOS)
        # 蒙灰：降低饱和度并加半透明遮罩，保证文字可读
        bg = bg.convert("L").convert("RGBA")
        overlay = Image.new("RGBA", (width, height), (0, 0, 0, 140))
        bg = Image.alpha_composite(bg, overlay)
    else:
        bg = Image.new("RGBA", (width, height), (30, 30, 50, 255))

    # ———————— 字体 ————————
    font_title = _load_font(36)
    font_name = _load_font(24)
    font_small = _load_font(18)

    # ———————— 创建画布 ————————
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    img.paste(bg, (0, 0))
    draw = ImageDraw.Draw(img)

    # ———————— 标题 ————————
    title = f"话痨榜 第{page}页"
    draw.text((width // 2, 40), title, fill=(255, 215, 0), font=font_title, anchor="ma")

    # ———————— 分割线 ————————
    draw.line(
        (40, header_height - 10, width - 40, header_height - 10),
        fill=(255, 215, 0, 200),
        width=2,
    )

    # ———————— 排行榜条目（前三名金色） ————————
    for i, (user_id, nickname, total) in enumerate(page_data):
        rank = start + i + 1
        y = header_height + i * row_height
        rank_color = (255, 215, 0) if rank <= 3 else (255, 255, 255)

        # 排名
        draw.text((60, y + row_height // 2), str(rank), fill=rank_color,
                  font=font_name, anchor="lm")

        # 昵称
        display = nickname or str(user_id)
        draw.text((140, y + 25), display, fill=(255, 255, 255), font=font_name)

        # QQ号
        draw.text((140, y + 55), user_id, fill=(180, 180, 180), font=font_small)

        # 字数
        count_text = f"{total} 字"
        bbox = draw.textbbox((0, 0), count_text, font=font_name)
        text_w = bbox[2] - bbox[0]
        draw.text(
            (width - 60 - text_w, y + row_height // 2),
            count_text,
            fill=(255, 215, 0),
            font=font_name,
            anchor="lm",
        )

    # ———————— 页脚 ————————
    draw.text(
        (width // 2, height - 50),
        "排行由群聊史官自动生成",
        fill=(150, 150, 150),
        font=font_small,
        anchor="ma",
    )

    # ———————— 输出 ————————
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.read()

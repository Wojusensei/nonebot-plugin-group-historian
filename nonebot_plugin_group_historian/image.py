import io
from PIL import Image, ImageDraw, ImageFont
from nonebot.log import logger
from nonebot_plugin_localstore import get_plugin_data_dir



# ————————————————————————————
# 资源路径
# 字体和背景图放在插件数据目录下
# ————————————————————————————

DATA_DIR = get_plugin_data_dir()
FONT_PATH = DATA_DIR / "font.ttf"
BG_PATH = DATA_DIR / "background.png"


# ————————————————————————————
# 荣誉图标
# ————————————————————————————

ICONS = {
    1: "👑",
    2: "💎",
    3: "⭐",
}


# ————————————————————————————
# 生成排行榜图片
# ranking: [(user_id, nickname, total), ...]
# page: 页码1开始
# rank_count: 每页人数
# 返回图片的 bytes
# ————————————————————————————

def create_ranking_image(ranking, page=1, rank_count=10):
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
        # 蒙灰：降低饱和度并加半透明遮罩
        bg = bg.convert("L").convert("RGBA")
        overlay = Image.new("RGBA", (width, height), (0, 0, 0, 140))
        bg = Image.alpha_composite(bg, overlay)
    else:
        bg = Image.new("RGBA", (width, height), (30, 30, 50, 255))

    # ———————— 字体 ————————
    if FONT_PATH.exists():
        font_title = ImageFont.truetype(str(FONT_PATH), 36)
        font_name = ImageFont.truetype(str(FONT_PATH), 24)
        font_small = ImageFont.truetype(str(FONT_PATH), 18)
    else:
        font_title = ImageFont.load_default()
        font_name = ImageFont.load_default()
        font_small = ImageFont.load_default()

    # ———————— 创建画布 ————————
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    img.paste(bg, (0, 0))
    draw = ImageDraw.Draw(img)

    # ———————— 标题 ————————
    title = f"话痨榜 第{page}页"
    draw.text(
        (width // 2, 40),
        title,
        fill=(255, 215, 0),
        font=font_title,
        anchor="ma",
    )

    # ———————— 分割线 ————————
    draw.line(
        (40, header_height - 10, width - 40, header_height - 10),
        fill=(255, 215, 0, 200),
        width=2,
    )

    # ———————— 排行榜条目 ————————
    for i, (user_id, nickname, total) in enumerate(page_data):
        rank = start + i + 1
        y = header_height + i * row_height

        # 排名
        icon = ICONS.get(rank, "")
        rank_text = f"{icon} {rank}" if icon else str(rank)
        draw.text((60, y + row_height // 2), rank_text, fill=(255, 255, 255), font=font_name, anchor="lm")

        # 昵称
        draw.text((140, y + 25), nickname, fill=(255, 255, 255), font=font_name)

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
        "排行由群聊史官自动生成 | 记录昨日话痨数据",
        fill=(150, 150, 150),
        font=font_small,
        anchor="ma",
    )

    # ———————— 输出 ————————
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.read()

logger.info("群聊史官 图片生成模块已就绪")

#累死了
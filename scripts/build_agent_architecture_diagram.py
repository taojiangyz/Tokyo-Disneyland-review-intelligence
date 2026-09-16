#!/usr/bin/env python3
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


OUT = Path("docs/assets/aladdin-agent-architecture.png")
FONT_PATH = "/System/Library/Fonts/Hiragino Sans GB.ttc"
W, H = 1800, 1220
BG = "#F7F9FC"
NAVY = "#163A5F"
BLUE = "#2E74B5"
LIGHT = "#EAF3FA"
GREEN = "#E7F4EC"
GOLD = "#FFF4D6"
GRAY = "#667085"
BORDER = "#AFC4D6"


def font(size, bold=False):
    return ImageFont.truetype(FONT_PATH, size=size, index=1 if bold else 0)


def box(draw, xy, title, subtitle="", fill=LIGHT, width=3):
    draw.rounded_rectangle(xy, radius=22, fill=fill, outline=BORDER, width=width)
    x1, y1, x2, y2 = xy
    draw.text(((x1+x2)//2, y1+25), title, anchor="ma", font=font(31, True), fill=NAVY)
    if subtitle:
        draw.multiline_text(((x1+x2)//2, y1+72), subtitle, anchor="ma", align="center", spacing=7, font=font(22), fill=GRAY)


def arrow(draw, start, end, label=""):
    draw.line([start, end], fill=BLUE, width=6)
    x2, y2 = end
    x1, y1 = start
    import math
    angle = math.atan2(y2-y1, x2-x1)
    for delta in (2.55, -2.55):
        p = (x2 + 20*math.cos(angle+delta), y2 + 20*math.sin(angle+delta))
        draw.line([end, p], fill=BLUE, width=6)
    if label:
        draw.text(((x1+x2)//2, (y1+y2)//2-14), label, anchor="ms", font=font(19), fill=GRAY)


def main():
    image = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(image)
    draw.text((90, 45), "Aladdin AI Agent 架构", font=font(48, True), fill=NAVY)
    draw.text((90, 108), "多语言评论分析 · 确定性统计 · 可追溯证据 · 受约束生成", font=font(26), fill=GRAY)

    # Offline lane
    draw.rounded_rectangle((65, 185, 1735, 445), radius=28, fill="#FFFFFF", outline="#D9E2EC", width=3)
    draw.text((95, 205), "离线数据管道", font=font(27, True), fill=BLUE)
    box(draw, (110, 265, 390, 395), "原始评论", "CN / HK / KR\n2,049条", fill=GOLD)
    box(draw, (500, 265, 800, 395), "清洗与标准化", "格式、评分、日期、ID校验")
    box(draw, (910, 265, 1210, 395), "BGE-M3", "多语言Embedding")
    box(draw, (1320, 265, 1660, 395), "Qdrant索引", "向量＋市场/评分/日期元数据", fill=GREEN)
    arrow(draw, (390, 330), (500, 330))
    arrow(draw, (800, 330), (910, 330))
    arrow(draw, (1210, 330), (1320, 330))

    # Online lane
    draw.rounded_rectangle((65, 485, 1735, 1175), radius=28, fill="#FFFFFF", outline="#D9E2EC", width=3)
    draw.text((95, 505), "在线Agent分析", font=font(27, True), fill=BLUE)
    box(draw, (100, 585, 345, 725), "用户问题", "英 / 日 / 中\n可选动态筛选", fill=GOLD)
    box(draw, (450, 585, 700, 725), "Streamlit", "管理界面")
    box(draw, (805, 585, 1055, 725), "FastAPI", "校验与编排")
    box(draw, (1160, 565, 1485, 745), "Agent Router", "4种任务分类\n受控工具计划", fill=GREEN)
    arrow(draw, (345, 655), (450, 655))
    arrow(draw, (700, 655), (805, 655))
    arrow(draw, (1055, 655), (1160, 655))

    box(draw, (150, 805, 470, 935), "确定性分析", "全量匹配统计\nTopic / Sentiment")
    box(draw, (620, 805, 940, 935), "Dense Retrieval", "Qdrant过滤\nBGE-M3 Top 5")
    box(draw, (1090, 805, 1410, 935), "证据验证", "ID完整性\n筛选与引用范围")
    box(draw, (650, 990, 1110, 1120), "Gemini受约束生成", "只读取确定性统计＋少量证据", fill=GREEN)
    arrow(draw, (1240, 745), (310, 805), "按任务调用")
    arrow(draw, (1335, 745), (780, 805))
    arrow(draw, (940, 870), (1090, 870), "候选证据")
    arrow(draw, (310, 935), (760, 990), "统计")
    arrow(draw, (1250, 935), (1000, 990), "已验证证据")
    draw.text((880, 1143), "回答＋证据＋筛选条件＋工具Trace＋耗时  →  FastAPI  →  Streamlit", anchor="ma", font=font(21), fill=GRAY)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    image.save(OUT, quality=95)
    print(OUT)


if __name__ == "__main__":
    main()

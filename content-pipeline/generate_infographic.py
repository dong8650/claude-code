"""
generate_infographic.py
=======================
데이터형 인포그래픽 이미지 생성기 (PIL 기반)
지원 타입: ranking (순위형), table (표형)

사용법:
  python generate_infographic.py --data sample_ranking.json
  python generate_infographic.py --data sample_table.json --output my_infographic.jpg

ranking JSON:
{
  "type": "ranking",
  "title": "한국인이 이민 가서 가장 후회한 나라 1위는?",
  "subtitle": "한국인 이민 후회 나라 TOP9",
  "highlight_top": 3,
  "items": [
    {"rank": 1, "label": "캐나다", "desc": "의료 대기 6개월, 혹한 우울증"},
    ...
  ],
  "channel": "@life-architecture"
}

table JSON:
{
  "type": "table",
  "title": "노후 생활비 얼마나 쓸 수 있나?",
  "subtitle": "내 돈 3억의 유통기한",
  "note": "예금 금리 2.5%, 이자소득세 15.4%, 연금 제외",
  "columns": ["월 생활비", "3억 기준", "6억 기준"],
  "rows": [["100만 원", "30년 4개월", "무한대"], ...],
  "footer": "든든한 노후는 내 형편에 맞는 지혜에서 시작됩니다",
  "channel": "@life-architecture"
}
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

from PIL import Image, ImageDraw, ImageFont

# ─────────────────────────────────────────────
# 캔버스
# ─────────────────────────────────────────────
W, H = 1080, 1920
PAD  = 64

# ─────────────────────────────────────────────
# 색상 — ranking (크림 베이지 계열)
# ─────────────────────────────────────────────
R_BG        = (245, 238, 216)
R_TITLE     = (35,  25,  15)
R_SUBTITLE  = (110, 85,  50)
R_TOP_COLS  = [
    (160, 115, 40),   # 1위 — 진한 골드
    (140, 100, 45),   # 2위 — 미디엄 골드
    (120, 90,  50),   # 3위 — 연한 골드
]
R_TOP_TXT   = (255, 250, 235)
R_ROW_A     = (225, 208, 168)
R_ROW_B     = (238, 224, 190)
R_ROW_TXT   = (40,  28,  12)
R_LINE      = (160, 130, 80)
R_MARK      = (130, 100, 55)

# ─────────────────────────────────────────────
# 색상 — table (다크 그린 계열)
# ─────────────────────────────────────────────
T_BG        = (18,  48,  28)
T_TITLE     = (255, 255, 255)
T_SUBTITLE  = (190, 240, 120)
T_NOTE_BG   = (55,  45,  5)
T_NOTE_TXT  = (230, 200, 60)
T_HDR_BG    = (35,  85,  45)
T_HDR_TXT   = (200, 255, 180)
T_ROW_A     = (25,  62,  35)
T_ROW_B     = (35,  82,  48)
T_ROW_TXT   = (215, 255, 215)
T_ACCENT    = (170, 235, 90)
T_FOOTER    = (160, 210, 140)
T_MARK      = (120, 180, 100)


# ─────────────────────────────────────────────
# 유틸리티
# ─────────────────────────────────────────────

def _font(size: int) -> ImageFont.FreeTypeFont:
    candidates = [
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJKkr-Bold.otf",
        "/System/Library/Fonts/AppleSDGothicNeo.ttc",
        "/Library/Fonts/AppleGothic.ttf",
    ]
    for p in candidates:
        if Path(p).exists():
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    return ImageFont.load_default()


def _tw(draw: ImageDraw.Draw, text: str, font) -> int:
    return draw.textbbox((0, 0), text, font=font)[2]


def _center(draw: ImageDraw.Draw, y: int, text: str, font, color, canvas_w: int = W):
    x = (canvas_w - _tw(draw, text, font)) // 2
    draw.text((x, y), text, font=font, fill=color)


def _wrap(draw: ImageDraw.Draw, text: str, font, max_w: int) -> list[str]:
    """한국어/영어 혼합 텍스트를 max_w에 맞게 줄바꿈."""
    lines, line = [], ""
    # 스페이스로 먼저 단어 분리 시도, 없으면 글자 단위
    tokens = text.split(" ") if " " in text else list(text)
    sep    = " " if " " in text else ""
    for tok in tokens:
        test = (line + sep + tok).lstrip()
        if _tw(draw, test, font) <= max_w:
            line = test
        else:
            if line:
                lines.append(line)
            line = tok
    if line:
        lines.append(line)
    return lines or [""]


def _rounded_rect(draw: ImageDraw.Draw, xy, fill, radius: int = 14):
    x0, y0, x1, y1 = xy
    draw.rounded_rectangle([x0, y0, x1, y1], radius=radius, fill=fill)


# ─────────────────────────────────────────────
# RANKING 스타일
# ─────────────────────────────────────────────

def _draw_ranking(data: dict) -> Image.Image:
    img  = Image.new("RGB", (W, H), R_BG)
    draw = ImageDraw.Draw(img)

    title     = data.get("title", "")
    subtitle  = data.get("subtitle", "")
    items     = data.get("items", [])
    hi_top    = data.get("highlight_top", 3)
    channel   = data.get("channel", "@life-architecture")

    f_title = _font(60)
    f_sub   = _font(36)
    f_rank  = _font(42)
    f_label = _font(40)
    f_desc  = _font(30)
    f_mark  = _font(27)

    y = 72

    # 제목
    for line in _wrap(draw, title, f_title, W - PAD * 2):
        _center(draw, y, line, f_title, R_TITLE)
        y += 76
    y += 8

    # 부제목
    _center(draw, y, subtitle, f_sub, R_SUBTITLE)
    y += 52

    # 구분선
    draw.line([(PAD, y), (W - PAD, y)], fill=R_LINE, width=2)
    y += 18

    # 아이템 영역 계산
    n       = len(items)
    avail   = H - y - 90
    row_h   = max(78, min(160, avail // max(n, 1)))

    for item in items:
        rank  = item.get("rank", 0)
        label = str(item.get("label", ""))
        desc  = str(item.get("desc", item.get("description", "")))
        is_hi = isinstance(rank, int) and rank <= hi_top

        # 배경
        if is_hi:
            idx    = min(rank - 1, len(R_TOP_COLS) - 1)
            bg     = R_TOP_COLS[idx]
            txt_c  = R_TOP_TXT
        else:
            bg    = R_ROW_A if rank % 2 == 0 else R_ROW_B
            txt_c = R_ROW_TXT

        _rounded_rect(draw, (PAD, y, W - PAD, y + row_h - 4), fill=bg)

        # 순위 번호
        rank_str = f"{rank}위"
        rank_f   = _font(44 if is_hi else 38)
        ry = y + (row_h - 50) // 2
        draw.text((PAD + 18, ry), rank_str, font=rank_f, fill=txt_c)
        rank_end = PAD + 18 + _tw(draw, "99위", rank_f) + 16

        # 레이블
        lbl_f = _font(42 if is_hi else 38)
        draw.text((rank_end, y + 10), label, font=lbl_f, fill=txt_c)

        # 설명 (두 줄까지)
        desc_lines = _wrap(draw, desc, f_desc, W - PAD - rank_end - PAD)
        dy = y + 10 + (50 if is_hi else 44)
        for dl in desc_lines[:2]:
            draw.text((rank_end, dy), dl, font=f_desc, fill=txt_c)
            dy += 33

        y += row_h

    # 하단 채널명
    _center(draw, H - 68, channel, f_mark, R_MARK)

    return img


# ─────────────────────────────────────────────
# TABLE 스타일
# ─────────────────────────────────────────────

def _draw_table(data: dict) -> Image.Image:
    img  = Image.new("RGB", (W, H), T_BG)
    draw = ImageDraw.Draw(img)

    title   = data.get("title", "")
    subtitle= data.get("subtitle", "")
    note    = data.get("note", "")
    columns = data.get("columns", [])
    rows    = data.get("rows", [])
    footer  = data.get("footer", "")
    channel = data.get("channel", "@life-architecture")

    f_title = _font(56)
    f_sub   = _font(42)
    f_note  = _font(27)
    f_hdr   = _font(36)
    f_cell  = _font(34)
    f_foot  = _font(28)
    f_mark  = _font(26)

    y = 68

    # 제목
    for line in _wrap(draw, title, f_title, W - PAD * 2):
        _center(draw, y, line, f_title, T_TITLE)
        y += 70
    y += 4

    # 부제목
    _center(draw, y, subtitle, f_sub, T_SUBTITLE)
    y += 60

    # 노트 박스
    if note:
        nw = _tw(draw, note, f_note) + 30
        nx = (W - nw) // 2
        _rounded_rect(draw, (nx, y, nx + nw, y + 42), fill=T_NOTE_BG, radius=10)
        _center(draw, y + 8, note, f_note, T_NOTE_TXT)
        y += 58

    y += 8

    # 테이블 레이아웃
    n_col  = len(columns)
    avail  = H - y - 150
    n_rows = len(rows)
    hdr_h  = 56
    row_h  = max(52, min(110, (avail - hdr_h) // max(n_rows, 1)))
    col_w  = (W - PAD * 2) // n_col
    tx     = PAD

    # 컬럼 헤더
    for ci, col in enumerate(columns):
        cx = tx + ci * col_w
        _rounded_rect(draw, (cx, y, cx + col_w - 3, y + hdr_h), fill=T_HDR_BG, radius=6)
        cw = _tw(draw, col, f_hdr)
        draw.text((cx + (col_w - cw) // 2, y + (hdr_h - 38) // 2), col, font=f_hdr, fill=T_HDR_TXT)
    y += hdr_h + 3

    # 데이터 행
    for ri, row in enumerate(rows):
        bg = T_ROW_A if ri % 2 == 0 else T_ROW_B
        for ci, cell in enumerate(row[:n_col]):
            cx  = tx + ci * col_w
            _rounded_rect(draw, (cx, y, cx + col_w - 3, y + row_h - 2), fill=bg, radius=4)
            txt = str(cell)
            tc  = T_ACCENT if ci == 0 else T_ROW_TXT
            cw  = _tw(draw, txt, f_cell)
            draw.text((cx + (col_w - cw) // 2, y + (row_h - 36) // 2), txt, font=f_cell, fill=tc)
        y += row_h

    # 푸터
    y += 16
    if footer:
        for line in _wrap(draw, footer, f_foot, W - PAD * 2):
            _center(draw, y, line, f_foot, T_FOOTER)
            y += 36

    _center(draw, H - 58, channel, f_mark, T_MARK)

    return img


# ─────────────────────────────────────────────
# PUBLIC API
# ─────────────────────────────────────────────

def generate_infographic(data: dict, output_path: str) -> str:
    """data dict에서 인포그래픽 이미지를 생성하고 저장한다."""
    style = data.get("type", "ranking")
    img   = _draw_table(data) if style == "table" else _draw_ranking(data)

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(out), quality=95)
    print(f"✅ 저장: {out}  ({img.width}×{img.height})")
    return str(out)


# ─────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(description="인포그래픽 이미지 생성기")
    p.add_argument("--data",   required=True, help="JSON 데이터 파일 경로")
    p.add_argument("--output", default=None,  help="출력 이미지 경로 (기본: 데이터파일명.jpg)")
    args = p.parse_args()

    src = Path(args.data)
    if not src.exists():
        print(f"❌ 파일 없음: {src}", file=sys.stderr)
        sys.exit(1)

    data   = json.loads(src.read_text(encoding="utf-8"))
    output = args.output or str(src.with_suffix(".jpg"))
    generate_infographic(data, output)


if __name__ == "__main__":
    main()

"""
generate_infographic.py
=======================
데이터형 인포그래픽 이미지 생성기 (PIL 기반) — 다크 오렌지 스타일
지원 타입: ranking (순위형), table (표형)

사용법:
  python generate_infographic.py --data sample_ranking.json
  python generate_infographic.py --data sample_table.json --output my_infographic.jpg
  python generate_infographic.py --data sample_ranking.json --video --bgm bgm/bgm_philosophy.mp3

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
import subprocess
import sys
from pathlib import Path
from typing import Optional

from PIL import Image, ImageDraw, ImageFont

# ─────────────────────────────────────────────
# 캔버스
# ─────────────────────────────────────────────
W, H = 1080, 1920
PAD  = 60

# ─────────────────────────────────────────────
# 다크 오렌지 팔레트 (@매일의설계 채널 통일)
# ─────────────────────────────────────────────
D_BG           = (17,  17,  17)    # #111111 — 배경
D_BG_ALT       = (26,  26,  26)    # #1A1A1A — 행 교대
D_BG_ALT2      = (34,  34,  34)    # #222222 — 행 교대2
D_WHITE        = (255, 255, 255)
D_ORANGE       = (255, 140,   0)   # #FF8C00 — 주 강조색
D_ORANGE_MID   = (220, 110,   0)   # #DC6E00 — 2위
D_ORANGE_DARK  = (180,  85,   0)   # #B45500 — 3위
D_TITLE        = (255, 255, 255)
D_SUBTITLE     = (255, 140,   0)   # 오렌지
D_DESC         = (153, 153, 153)   # #999999
D_DIVIDER      = (42,  42,  42)    # #2A2A2A
D_NOTE_BG      = (30,  20,   0)    # 아주 어두운 앰버
D_NOTE_TXT     = (255, 140,   0)
D_CHANNEL      = (80,  80,  80)    # #505050


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


def _th(draw: ImageDraw.Draw, text: str, font) -> int:
    bb = draw.textbbox((0, 0), text, font=font)
    return bb[3] - bb[1]


def _center(draw: ImageDraw.Draw, y: int, text: str, font, color, canvas_w: int = W):
    x = (canvas_w - _tw(draw, text, font)) // 2
    draw.text((x, y), text, font=font, fill=color)


def _wrap(draw: ImageDraw.Draw, text: str, font, max_w: int) -> list[str]:
    lines, line = [], ""
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


def _rounded_rect(draw: ImageDraw.Draw, xy, fill, radius: int = 16, outline=None, outline_width: int = 2):
    x0, y0, x1, y1 = xy
    draw.rounded_rectangle([x0, y0, x1, y1], radius=radius, fill=fill,
                           outline=outline, width=outline_width)


# ─────────────────────────────────────────────
# RANKING — 다크 오렌지 스타일
# ─────────────────────────────────────────────

def _draw_ranking(data: dict) -> Image.Image:
    img  = Image.new("RGB", (W, H), D_BG)
    draw = ImageDraw.Draw(img)

    title    = data.get("title", "")
    subtitle = data.get("subtitle", "")
    items    = data.get("items", [])
    hi_top   = data.get("highlight_top", 3)
    channel  = data.get("channel", "@life-architecture")

    f_title   = _font(58)
    f_sub     = _font(34)
    f_rank    = _font(38)
    f_rank_hi = _font(44)
    f_label   = _font(38)
    f_label_hi= _font(42)
    f_desc    = _font(28)
    f_mark    = _font(26)

    y = 80

    # 상단 오렌지 액센트 바
    draw.rectangle([(PAD, y), (PAD + 6, y + 80)], fill=D_ORANGE)

    # 제목
    tx = PAD + 22
    for line in _wrap(draw, title, f_title, W - tx - PAD):
        draw.text((tx, y), line, font=f_title, fill=D_TITLE)
        y += 72
    y += 6

    # 부제목
    draw.text((tx, y), subtitle, font=f_sub, fill=D_SUBTITLE)
    y += 50

    # 구분선
    draw.line([(PAD, y), (W - PAD, y)], fill=D_DIVIDER, width=2)
    y += 20

    # 아이템 영역
    n     = len(items)
    avail = H - y - 80
    row_h = max(80, min(220, avail // max(n, 1)))

    for item in items:
        rank  = item.get("rank", 0)
        label = str(item.get("label", ""))
        desc  = str(item.get("desc", item.get("description", "")))
        is_hi = isinstance(rank, int) and rank <= hi_top

        # 카드 배경
        if is_hi:
            idx    = min(rank - 1, 2)
            bg     = [D_ORANGE, D_ORANGE_MID, D_ORANGE_DARK][idx]
            txt_c  = D_WHITE
            desc_c = (255, 220, 170)
        else:
            bg     = D_BG_ALT if rank % 2 == 1 else D_BG_ALT2
            txt_c  = D_WHITE
            desc_c = D_DESC

        _rounded_rect(draw, (PAD, y + 3, W - PAD, y + row_h - 3), fill=bg, radius=14)

        # 순위 번호
        rf   = f_rank_hi if is_hi else f_rank
        rstr = str(rank)
        ry   = y + (row_h - _th(draw, rstr, rf)) // 2
        draw.text((PAD + 20, ry), rstr, font=rf, fill=txt_c if is_hi else D_ORANGE)
        rank_end = PAD + 20 + _tw(draw, "10", f_rank_hi) + 20

        # 레이블
        lf  = f_label_hi if is_hi else f_label
        lh  = _th(draw, label, lf)
        if desc:
            label_y = y + (row_h // 2) - lh - 4
        else:
            label_y = y + (row_h - lh) // 2
        draw.text((rank_end, label_y), label, font=lf, fill=txt_c)

        # 설명
        if desc:
            desc_lines = _wrap(draw, desc, f_desc, W - PAD - rank_end - PAD)
            dy = label_y + lh + 6
            for dl in desc_lines[:2]:
                draw.text((rank_end, dy), dl, font=f_desc, fill=desc_c)
                dy += 34

        y += row_h

    # 채널명
    _center(draw, H - 58, channel, f_mark, D_CHANNEL)

    return img


# ─────────────────────────────────────────────
# TABLE — 다크 오렌지 스타일
# ─────────────────────────────────────────────

def _draw_table(data: dict) -> Image.Image:
    img  = Image.new("RGB", (W, H), D_BG)
    draw = ImageDraw.Draw(img)

    title   = data.get("title", "")
    subtitle= data.get("subtitle", "")
    note    = data.get("note", "")
    columns = data.get("columns", [])
    rows    = data.get("rows", [])
    footer  = data.get("footer", "")
    channel = data.get("channel", "@life-architecture")

    f_title = _font(54)
    f_sub   = _font(38)
    f_note  = _font(26)
    f_hdr   = _font(34)
    f_cell  = _font(32)
    f_foot  = _font(27)
    f_mark  = _font(25)

    y = 72

    # 상단 오렌지 액센트 바
    draw.rectangle([(PAD, y), (PAD + 6, y + 72)], fill=D_ORANGE)
    tx = PAD + 22

    # 제목
    for line in _wrap(draw, title, f_title, W - tx - PAD):
        draw.text((tx, y), line, font=f_title, fill=D_TITLE)
        y += 66
    y += 4

    # 부제목
    draw.text((tx, y), subtitle, font=f_sub, fill=D_SUBTITLE)
    y += 54

    # 노트 박스
    if note:
        nw = _tw(draw, note, f_note) + 32
        nx = PAD
        _rounded_rect(draw, (nx, y, nx + nw, y + 44), fill=D_NOTE_BG, radius=10)
        draw.text((nx + 16, y + 10), note, font=f_note, fill=D_NOTE_TXT)
        y += 58

    y += 10

    # 테이블 레이아웃
    n_col  = len(columns)
    avail  = H - y - 130
    n_rows = len(rows)
    hdr_h  = 58
    row_h  = max(54, min(160, (avail - hdr_h) // max(n_rows, 1)))
    col_w  = (W - PAD * 2) // n_col
    tx     = PAD

    # 컬럼 헤더 (오렌지)
    for ci, col in enumerate(columns):
        cx = tx + ci * col_w
        r  = 12 if ci == 0 else (12 if ci == n_col - 1 else 0)
        _rounded_rect(draw, (cx, y, cx + col_w - 2, y + hdr_h), fill=D_ORANGE, radius=r)
        cw = _tw(draw, col, f_hdr)
        draw.text((cx + (col_w - cw) // 2, y + (hdr_h - 36) // 2), col, font=f_hdr, fill=D_WHITE)
    y += hdr_h + 2

    # 데이터 행
    for ri, row in enumerate(rows):
        bg = D_BG_ALT if ri % 2 == 0 else D_BG_ALT2
        for ci, cell in enumerate(row[:n_col]):
            cx  = tx + ci * col_w
            _rounded_rect(draw, (cx, y, cx + col_w - 2, y + row_h - 2), fill=bg, radius=4)
            txt = str(cell)
            tc  = D_ORANGE if ci == 0 else D_WHITE
            fw  = _font(32) if ci == 0 else f_cell
            cw  = _tw(draw, txt, fw)
            draw.text((cx + (col_w - cw) // 2, y + (row_h - 34) // 2), txt, font=fw, fill=tc)
        # 행 구분선
        draw.line([(PAD, y + row_h - 1), (W - PAD, y + row_h - 1)], fill=D_DIVIDER, width=1)
        y += row_h

    # 푸터
    y += 18
    if footer:
        for line in _wrap(draw, footer, f_foot, W - PAD * 2):
            _center(draw, y, line, f_foot, D_DESC)
            y += 36

    _center(draw, H - 52, channel, f_mark, D_CHANNEL)

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


def generate_video(image_path: str, output_path: str, duration: int = 7,
                   bgm_path: Optional[str] = None) -> str:
    """JPG 인포그래픽을 FFmpeg으로 쇼츠 MP4 영상으로 변환한다."""
    if bgm_path and Path(bgm_path).exists():
        fade_start = max(0, duration - 1.5)
        cmd = [
            "ffmpeg", "-y",
            "-loop", "1", "-framerate", "30", "-i", image_path,
            "-stream_loop", "-1", "-i", bgm_path,
            "-c:v", "libx264",
            "-c:a", "aac", "-b:a", "128k",
            "-af", f"volume=0.25,afade=t=in:st=0:d=0.5,afade=t=out:st={fade_start}:d=1.5",
            "-t", str(duration),
            "-pix_fmt", "yuv420p",
            "-vf", "scale=1080:1920",
            "-map", "0:v", "-map", "1:a",
            output_path,
        ]
    else:
        cmd = [
            "ffmpeg", "-y",
            "-loop", "1", "-framerate", "30",
            "-i", image_path,
            "-c:v", "libx264",
            "-t", str(duration),
            "-pix_fmt", "yuv420p",
            "-vf", "scale=1080:1920",
            output_path,
        ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg 실패:\n{result.stderr}")
    bgm_tag = " (BGM 포함)" if bgm_path and Path(bgm_path).exists() else ""
    print(f"✅ 영상 저장: {output_path}  ({duration}초){bgm_tag}")
    return output_path


# ─────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(description="인포그래픽 이미지/영상 생성기 (다크 오렌지 스타일)")
    p.add_argument("--data",     required=True,       help="JSON 데이터 파일 경로")
    p.add_argument("--output",   default=None,        help="출력 경로 (기본: 데이터파일명.jpg/.mp4)")
    p.add_argument("--video",    action="store_true", help="MP4 쇼츠 영상으로 변환")
    p.add_argument("--duration", type=int, default=7, help="영상 길이 초 (기본 7)")
    p.add_argument("--bgm",      default=None,        help="배경음악 경로 (mp3)")
    args = p.parse_args()

    src = Path(args.data)
    if not src.exists():
        print(f"❌ 파일 없음: {src}", file=sys.stderr)
        sys.exit(1)

    data = json.loads(src.read_text(encoding="utf-8"))

    if args.video:
        jpg_path = args.output.replace(".mp4", ".jpg") if args.output and args.output.endswith(".mp4") \
                   else str(src.with_suffix(".jpg"))
        mp4_path = args.output or str(src.with_suffix(".mp4"))
        generate_infographic(data, jpg_path)
        generate_video(jpg_path, mp4_path, args.duration, bgm_path=args.bgm)
    else:
        output = args.output or str(src.with_suffix(".jpg"))
        generate_infographic(data, output)


if __name__ == "__main__":
    main()

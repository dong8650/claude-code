"""
make_video.py
=============
철학자 사진(공개 도메인) + Ken Burns + 명언 자막 + BGM
3클립: intro / quote / echo
해상도: 1080×1920 (9:16 Shorts)
"""
import json
import os
import random
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, "/root/content/runtime/saying")
from config import RUNTIME_DIR, BGM_PATH, FONT_PATH, WATERMARK

W, H = 1080, 1920
FPS  = 25
CRF  = 18

IMAGE_DIR = Path(RUNTIME_DIR) / "images"

# ── 비주얼 상수 ──────────────────────────────────────────────
TOP_BAR_H    = int(H * 0.14)   # 14% — 책 이름
BOT_BAR_H    = int(H * 0.10)   # 10% — 워터마크
VIGNETTE_OPT = "vignette=PI/4"

# 자막 영역: 화면 하단 40% 중앙
SUB_Y        = int(H * 0.62)
SUB_FONT_SIZE = 52
ECHO_FONT_SIZE = 46

# 색상
COL_WHITE  = "white"
COL_ORANGE = "#FF8C00"
COL_CREAM  = "#F5E6C8"
COL_BLACK  = "black"

# 어두운 오버레이 — 사진 위에 반투명 검정
DARK_OVERLAY = "colorize=hue=0:saturation=0:lightness=-0.35"


def _get_images(image_set: str, n: int = 3) -> list:
    folder = IMAGE_DIR / image_set
    imgs   = sorted(folder.glob("*.jpg"))
    if not imgs:
        raise FileNotFoundError(f"이미지 없음: {folder}. setup_images.py 먼저 실행하세요.")
    # 3장 랜덤 선택 (중복 없이, 가능하면)
    if len(imgs) >= n:
        return random.sample(imgs, n)
    return [random.choice(imgs) for _ in range(n)]


def _ken_burns(img: str, duration: float, zoom_in: bool = True) -> str:
    """Ken Burns 필터 문자열 반환 (zoompan + crop → vignette + 다크 오버레이)."""
    frames   = int(duration * FPS)
    z_start  = 1.05 if zoom_in else 1.15
    z_end    = 1.15 if zoom_in else 1.05
    z_step   = (z_end - z_start) / max(frames - 1, 1)

    return (
        f"scale={W*2}:{H*2}:force_original_aspect_ratio=increase,"
        f"crop={W*2}:{H*2},"
        f"zoompan=z='if(lte(on,1),{z_start},min(zoom+{z_step:.6f},{z_end}))':"
        f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s={W}x{H}:fps={FPS},"
        f"eq=brightness=-0.25:saturation=0.8,"
        f"{VIGNETTE_OPT}"
    )


def _make_clip(img: str, duration: float, out: str, zoom_in: bool = True):
    vf = _ken_burns(img, duration, zoom_in)
    subprocess.run([
        "ffmpeg", "-y", "-loop", "1", "-i", img,
        "-vf", vf,
        "-t", str(duration), "-r", str(FPS),
        "-pix_fmt", "yuv420p", "-c:v", "libx264",
        "-preset", "fast", "-crf", str(CRF), "-an", out
    ], capture_output=True, check=True)


def _build_ass(script: dict, durations: dict) -> str:
    """ASS 자막 파일 생성 — 파일 경로 반환."""
    intro_dur = durations["intro_dur"] + 0.5  # 무음 포함
    quote_dur = durations["quote_dur"]
    echo_dur  = durations["echo_dur"]

    def ts(sec: float) -> str:
        h  = int(sec // 3600)
        m  = int((sec % 3600) // 60)
        s  = sec % 60
        return f"{h}:{m:02d}:{s:05.2f}"

    t0_intro = 0.0
    t1_intro = intro_dur
    t0_quote = t1_intro
    t1_quote = t0_quote + quote_dur
    t0_echo  = t1_quote
    t1_echo  = t0_echo + echo_dur

    lines = [
        "[Script Info]",
        "ScriptType: v4.00+",
        "PlayResX: 1080",
        "PlayResY: 1920",
        "WrapStyle: 1",
        "",
        "[V4+ Styles]",
        "Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,"
        "Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,"
        "Alignment,MarginL,MarginR,MarginV,Encoding",
        # intro: 철학자 이름 — 중앙 하단
        f"Style: Intro,{FONT_PATH},{ECHO_FONT_SIZE},&H00F5E6C8,&H000000FF,&H00000000,&H80000000,"
        f"-1,0,0,0,100,100,2,0,1,2,1,2,60,60,200,1",
        # quote: 명언 본문 — 중앙
        f"Style: Quote,{FONT_PATH},{SUB_FONT_SIZE},&H00FFFFFF,&H000000FF,&H00000000,&H80000000,"
        f"-1,0,0,0,100,100,1,0,1,2,1,5,80,80,{H//3},1",
        # echo: 여운 — 중앙 하단
        f"Style: Echo,{FONT_PATH},{ECHO_FONT_SIZE},&H00FF8C00,&H000000FF,&H00000000,&H80000000,"
        f"-1,0,0,0,100,100,2,0,1,2,1,2,60,60,220,1",
        "",
        "[Events]",
        "Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text",
        f"Dialogue: 0,{ts(t0_intro)},{ts(t1_intro)},Intro,,0,0,0,,{script['intro_ko']}",
        f"Dialogue: 0,{ts(t0_quote)},{ts(t1_quote)},Quote,,0,0,0,,{script['quote_ko']}",
        f"Dialogue: 0,{ts(t0_echo)},{ts(t1_echo)},Echo,,0,0,0,,{script['echo_ko']}",
    ]
    return "\n".join(lines)


def make_video(script: dict, ep_dir: str, durations: dict):
    ep   = Path(ep_dir)
    imgs = _get_images(script["image_set"])

    intro_dur  = durations["intro_dur"] + 0.5
    quote_dur  = durations["quote_dur"]
    echo_dur   = durations["echo_dur"]
    total_dur  = intro_dur + quote_dur + echo_dur

    print(f"나레이션: {total_dur:.2f}초")

    # ── 클립 생성 ──────────────────────────────────────────────
    print("[1/5] 이미지 클립 생성...")
    clips = []
    for i, (img, dur, zoom_in) in enumerate(zip(
        imgs, [intro_dur, quote_dur, echo_dur], [True, False, True]
    )):
        out = str(ep / f"clip{i+1}.mp4")
        _make_clip(str(img), dur, out, zoom_in)
        print(f"  ✅ clip{i+1}.mp4 ({dur:.1f}초)")
        clips.append(out)

    # ── 클립 연결 ──────────────────────────────────────────────
    print("[2/5] 클립 연결...")
    list_file = str(ep / "clips.txt")
    with open(list_file, "w") as f:
        for c in clips:
            f.write(f"file '{c}'\n")
    video_only = str(ep / "video_only.mp4")
    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", list_file, "-c", "copy", video_only
    ], capture_output=True, check=True)
    print("  ✅ 클립 연결 완료")

    # ── BGM 믹싱 ──────────────────────────────────────────────
    print("[3/5] BGM 믹싱...")
    voice_path = str(ep / "voice_ko.mp3")
    bgm_mixed  = str(ep / "voice_with_bgm.mp3")
    subprocess.run([
        "ffmpeg", "-y",
        "-i", voice_path,
        "-i", BGM_PATH,
        "-filter_complex",
        f"[0:a]volume=1.0[v];[1:a]volume=0.10,afade=t=out:st={total_dur-2}:d=2[b];[v][b]amix=inputs=2:duration=first[out]",
        "-map", "[out]", "-acodec", "libmp3lame", bgm_mixed
    ], capture_output=True, check=True)
    print("  ✅ BGM 완료")

    # ── 자막 생성 ──────────────────────────────────────────────
    print("[4/5] 자막 생성...")
    ass_content = _build_ass(script, durations)
    ass_path    = str(ep / "subtitles.ass")
    Path(ass_path).write_text(ass_content, encoding="utf-8")

    # 상단 바 텍스트: 철학자 이름 | 책 이름
    top_text   = f"{script['philosopher']}  |  {script['book']}"
    # 하단 워터마크
    watermark  = WATERMARK

    # ── 최종 합성 ──────────────────────────────────────────────
    print("[5/5] 최종 출력...")
    output = str(ep / "output_final.mp4")

    drawtext_top = (
        f"drawtext=fontfile={FONT_PATH}:text='{top_text}':"
        f"fontcolor=white:fontsize=34:x=(w-text_w)/2:y={TOP_BAR_H//2 - 17}:"
        f"box=1:boxcolor=black@0.7:boxborderw=12"
    )
    drawtext_wm = (
        f"drawtext=fontfile={FONT_PATH}:text='{watermark}':"
        f"fontcolor=white@0.6:fontsize=26:x=(w-text_w)/2:y={H - BOT_BAR_H//2 - 13}"
    )

    vf_final = (
        f"drawbox=x=0:y=0:w={W}:h={TOP_BAR_H}:color=black@0.75:t=fill,"
        f"drawbox=x=0:y={H - BOT_BAR_H}:w={W}:h={BOT_BAR_H}:color=black@0.75:t=fill,"
        f"subtitles='{ass_path}',"
        f"{drawtext_top},"
        f"{drawtext_wm}"
    )

    subprocess.run([
        "ffmpeg", "-y",
        "-i", video_only,
        "-i", bgm_mixed,
        "-vf", vf_final,
        "-c:v", "libx264", "-preset", "fast", "-crf", str(CRF),
        "-c:a", "aac", "-b:a", "128k",
        "-shortest", "-pix_fmt", "yuv420p",
        output
    ], check=True, capture_output=True)

    size_mb = Path(output).stat().st_size / 1024 / 1024
    print(f"✅ 완성: {output} ({size_mb:.1f}MB, {total_dur:.1f}초)")
    return output

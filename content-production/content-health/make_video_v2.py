"""
make_video_v2.py — 건강편 영상 합성
=====================================
content-pipeline-core 공통 모듈 사용:
  - make_ken_burns_clip  (portrait_safe 포함)
  - concat_clips
  - mix_bgm              (-stream_loop -1 + -t 하드컷)
  - assemble_video       (2단계 mux+overlay, -c:a aac, -t 하드컷)

채널 고유 로직만 이 파일에 유지:
  - generate_scene_tts   (장면별 TTS + 속도 차별화)
  - build_ass            (장면별 ASS 자막)
  - make_video           (오케스트레이션)
"""
import asyncio
import json
import shutil
import subprocess
import sys
from pathlib import Path

# pipeline-core 공통 모듈 로드
_CORE = Path(__file__).parent.parent / "content-pipeline-core"
sys.path.insert(0, str(_CORE))
from ffmpeg_utils import get_duration, make_silence
from video_core import make_ken_burns_clip, concat_clips, assemble_video
from audio_core import mix_bgm

FONT_PATH     = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
FONT_FALLBACK = "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc"
SLOGAN        = "매일 하나씩, 건강 상식을 쌓자"

from channel_branding import CHANNEL_NAME, WATERMARK
TOP_BAR_RATIO = 0.20
BOT_BAR_RATIO = 0.18

# 장면별 TTS 속도: Hook 느리게(강조), 감정충격 느리게(여운), 루프트리거 빠르게(긴박감)
SCENE_TTS_RATES = ["-5%", "+8%", "+5%", "+0%", "-8%", "+5%", "+12%"]


def get_font() -> str:
    for p in [FONT_PATH, FONT_FALLBACK]:
        if Path(p).exists():
            return p
    return "NotoSansCJK-Bold"


async def _tts_async(text: str, voice: str, out_path: str, rate: str = "+0%"):
    import edge_tts
    communicate = edge_tts.Communicate(text, voice, rate=rate)
    await communicate.save(out_path)


import re as _re

def _strip_emoji(text: str) -> str:
    """이모지 제거 — 한글/영문/숫자/기본 기호/화살표 유지."""
    return _re.sub(
        r'[^가-힣ᄀ-ᇿ㄰-㆏'
        r'a-zA-Z0-9'
        r'\s\n'
        r'←-⇿'
        r'!?.,\'\"·/():~%\+\-\*\^]',
        '', text
    )


def _caption_to_tts(caption: str) -> str:
    """캡션 → TTS용 텍스트 (이모지·특수문자 제거)."""
    text = caption.replace("\\N", " ").replace("\n", " ")
    return _re.sub(r'[^\w\s가-힣,.!?]', '', text).strip()


def generate_scene_tts(scenes: list, ep_dir: Path, voice: str = "ko-KR-SunHiNeural") -> tuple:
    """장면별 TTS 생성.
    narration 없으면 caption 텍스트로 대체 (이모지 제거).
    Returns: (voice_file, actual_durations)
    """
    print("  🎙️ 장면별 TTS 생성 중...")
    scene_audio_files = []
    actual_durations  = []

    for i, scene in enumerate(scenes):
        narration = scene.get("narration", "").strip()
        caption   = scene.get("caption", "").strip()
        scene_audio = ep_dir / f"tts_scene{i+1}.mp3"

        tts_text = narration or _caption_to_tts(caption)
        rate     = SCENE_TTS_RATES[i] if i < len(SCENE_TTS_RATES) else "+0%"

        if tts_text:
            asyncio.run(_tts_async(tts_text, voice, str(scene_audio), rate))
            dur = get_duration(str(scene_audio))
            src = "나레이션" if narration else "캡션TTS"
            print(f"    scene{i+1}: {dur:.2f}초 ({src}, rate={rate})")
        else:
            dur = float(scene["duration"])
            make_silence(str(scene_audio), dur)
            print(f"    scene{i+1}: {dur:.2f}초 (silence)")

        scene_audio_files.append(str(scene_audio))
        actual_durations.append(dur)

    voice_file  = ep_dir / "voice_ko.mp3"
    concat_list = ep_dir / "tts_full_concat.txt"
    concat_list.write_text("\n".join(f"file '{f}'" for f in scene_audio_files), encoding="utf-8")
    subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0",
         "-i", str(concat_list), "-c", "copy", str(voice_file)],
        capture_output=True
    )

    total = get_duration(str(voice_file))
    print(f"  ✅ TTS 완료: {voice_file.name} ({total:.2f}초, {len(scenes)}장면)")
    return voice_file, actual_durations


def _ts(sec: float) -> str:
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = sec % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def build_ass(scenes: list, ep_dir: Path, font_path: str, durations: list, landscape: bool = False) -> Path:
    """장면별 ASS 자막 생성.
    durations: 실제 클립 길이 목록 (ffprobe 측정값) — 프레임 정렬 오차 없음.
    """
    if landscape:
        VW, VH         = 1920, 1080
        top_bar_h      = int(VH * 0.14)
        bot_bar_h      = int(VH * 0.10)
        fs_hook, fs_main, fs_save, fs_loop = 56, 46, 44, 42
    else:
        VW, VH         = 1080, 1920
        top_bar_h      = int(VH * TOP_BAR_RATIO)
        bot_bar_h      = int(VH * BOT_BAR_RATIO)
        fs_hook, fs_main, fs_save, fs_loop = 80, 68, 64, 60

    content_h      = VH - top_bar_h - bot_bar_h
    content_center = top_bar_h + content_h // 2

    lines = [
        "[Script Info]", "ScriptType: v4.00+", f"PlayResX: {VW}", f"PlayResY: {VH}",
        "Collisions: Normal", "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, "
        "BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, "
        "BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        f"Style: Hook,NotoSansCJK-Bold,{fs_hook},&H0000AAFF,&H000000FF,&H00000000,&HAA000000,"
        f"-1,0,0,0,100,100,2,0,3,4,2,5,60,60,{content_center - fs_hook},1",
        f"Style: Main,NotoSansCJK-Bold,{fs_main},&H00FFFFFF,&H000000FF,&H00000000,&HAA000000,"
        f"-1,0,0,0,100,100,2,0,3,3,2,5,60,60,{content_center - fs_main},1",
        f"Style: Save,NotoSansCJK-Bold,{fs_save},&H0000FFFF,&H000000FF,&H00000000,&HAA000000,"
        f"-1,0,0,0,100,100,2,0,3,3,2,5,60,60,{content_center - fs_save},1",
        f"Style: Loop,NotoSansCJK-Bold,{fs_loop},&H00FFFF00,&H000000FF,&H00000000,&HAA000000,"
        f"-1,0,0,0,100,100,2,0,3,3,2,2,60,60,80,1",
        "", "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]

    current = 0.0
    for i, (scene, dur) in enumerate(zip(scenes, durations)):
        start   = _ts(current)
        end     = _ts(current + dur - 0.05)
        caption = _strip_emoji(scene.get("caption", "")).replace("\n", "\\N")

        if i == 0:
            style = "Hook"
        elif i == len(scenes) - 1:
            style = "Loop"
        elif "저장" in scene.get("caption", "") or "💾" in scene.get("caption", ""):
            style = "Save"
        else:
            style = "Main"

        lines.append(f"Dialogue: 0,{start},{end},{style},,0,0,0,,{caption}")
        current += dur

    ass_file = ep_dir / "subtitles_v2.ass"
    ass_file.write_text("\n".join(lines), encoding="utf-8")
    return ass_file


def make_video(ep_dir: Path, script: dict, bgm_path: str = None, generate_tts: bool = True, landscape: bool = False) -> Path:
    scenes    = script["scenes"]
    font_path = get_font()
    hook      = _strip_emoji(script.get("hook", script.get("title", "")))

    # 제목 2줄 분리 (중간 공백 기준)
    mid = len(hook) // 2
    for i in range(mid, len(hook)):
        if hook[i] == " ":
            mid = i
            break
    t1 = hook[:mid].strip()
    t2 = hook[mid:].strip() if mid < len(hook) else ""

    # ── [1/6] TTS ─────────────────────────────────────────────────────────
    print(f"\n[1/6] 🎙️ TTS 생성...")
    voice_file = ep_dir / "voice_ko.mp3"
    if generate_tts and not voice_file.exists():
        voice_file, actual_durations = generate_scene_tts(scenes, ep_dir)
    elif voice_file.exists():
        actual_durations = []
        for i, scene in enumerate(scenes):
            tts_file = ep_dir / f"tts_scene{i+1}.mp3"
            actual_durations.append(
                get_duration(str(tts_file)) if tts_file.exists() else float(scene["duration"])
            )
    else:
        actual_durations = [float(s["duration"]) for s in scenes]
        make_silence(str(voice_file), sum(actual_durations))

    voice_dur  = get_duration(str(voice_file))
    total_dur  = sum(actual_durations)
    print(f"  음성 길이: {voice_dur:.2f}초")
    if not landscape:
        if total_dur > 55:
            print(f"  ⚠️ {total_dur:.1f}초 — 55초 초과, 완시율 하락 위험")
        elif total_dur < 30:
            print(f"  ⚠️ {total_dur:.1f}초 — 30초 미만, 정보량 부족")

    clip_size = "1920x1080" if landscape else "1080x1920"

    # ── [2/6] Ken Burns ───────────────────────────────────────────────────
    print(f"\n[2/6] 🎨 Ken Burns 이미지 클립 생성...")
    clip_files           = []
    actual_clip_durations = []
    for i, (scene, dur) in enumerate(zip(scenes, actual_durations)):
        img      = ep_dir / f"bg{i+1}.jpg"
        if not img.exists():
            img  = ep_dir / "bg1.jpg"
        clip_out = ep_dir / f"clip{i+1}.mp4"
        clip_dur = make_ken_burns_clip(img, dur, i, clip_out, portrait_safe=True, size=clip_size)
        if clip_dur > 0:
            clip_files.append(clip_out)
            actual_clip_durations.append(clip_dur)
            print(f"  ✅ clip{i+1} ({clip_dur:.2f}초, {'줌인' if i%2==0 else '줌아웃'})")

    # ── [3/6] Concat ──────────────────────────────────────────────────────
    print(f"\n[3/6] 🔗 클립 연결...")
    concat_out = ep_dir / "video_only.mp4"
    concat_clips(clip_files, concat_out)

    # ── [4/6] BGM 믹싱 ────────────────────────────────────────────────────
    print(f"\n[4/6] 🎵 BGM 믹싱...")
    voice_bgm = ep_dir / "voice_bgm.mp3"
    if bgm_path and Path(bgm_path).exists():
        mix_bgm(voice_file, Path(bgm_path), voice_bgm, voice_dur)
        print("  ✅ BGM 믹싱 완료")
    else:
        shutil.copy(str(voice_file), str(voice_bgm))

    # ── [5/6] 자막 ────────────────────────────────────────────────────────
    print(f"\n[5/6] 📝 자막 생성...")
    ass_file = build_ass(scenes, ep_dir, font_path, actual_clip_durations, landscape=landscape)
    print(f"  ✅ 자막 완료: {ass_file.name}")

    # ── [6/6] 최종 출력 ───────────────────────────────────────────────────
    print(f"\n[6/6] 🎬 최종 출력 (상하 바 + 브랜딩 + 자막)...")
    if landscape:
        VH          = 1080
        top_bar_h   = int(VH * 0.14)       # 151px
        bot_bar_h   = int(VH * 0.10)       # 108px
        title_y1    = int(VH * 0.025)      # 27px
        title_y2    = title_y1 + 44        # 71px
        title_fs1, title_fs2 = 36, 48
        wm_fs, sl_fs = 18, 16
        cta_fs      = 24
    else:
        VH          = 1920
        top_bar_h   = int(VH * TOP_BAR_RATIO)
        bot_bar_h   = int(VH * BOT_BAR_RATIO)
        title_y1    = int(VH * 0.115)
        title_y2    = title_y1 + 78
        title_fs1, title_fs2 = 56, 68
        wm_fs, sl_fs = 26, 24
        cta_fs      = 36

    watermark_y = int(VH - bot_bar_h + bot_bar_h * 0.20)
    slogan_y    = watermark_y + (30 if landscape else 45)
    cta_y       = int(VH - bot_bar_h - (30 if landscape else 50))
    cta_start   = round(voice_dur - 1.2, 1)

    vf = (
        f"drawbox=x=0:y=0:w=iw:h={top_bar_h}:color=black@1.0:t=fill,"
        f"drawbox=x=0:y=ih-{bot_bar_h}:w=iw:h={bot_bar_h}:color=black@1.0:t=fill,"
        f"ass={ass_file},"
        f"drawtext=fontfile={font_path}:text='{t1}':fontsize={title_fs1}:fontcolor=white@0.95:"
        f"x=(w-text_w)/2:y={title_y1}:borderw=3:bordercolor=black@0.8,"
        f"drawtext=fontfile={font_path}:text='{t2}':fontsize={title_fs2}:fontcolor=#FF8C00:"
        f"x=(w-text_w)/2:y={title_y2}:borderw=3:bordercolor=black@0.8,"
        f"drawtext=fontfile={font_path}:text='{WATERMARK}':fontsize={wm_fs}:fontcolor=white@0.45:"
        f"x=(w-text_w)/2:y={watermark_y}:borderw=1:bordercolor=black@0.3,"
        f"drawtext=fontfile={font_path}:text='{SLOGAN}':fontsize={sl_fs}:fontcolor=white@0.7:"
        f"x=(w-text_w)/2:y={slogan_y}:borderw=1:bordercolor=black@0.3,"
        f"drawtext=fontfile={font_path}:text='공감됐으면 좋아요  저장해두세요':fontsize={cta_fs}:fontcolor=#FFD700:"
        f"x=(w-text_w)/2:y={cta_y}:borderw=2:bordercolor=black@0.8:"
        f"enable='gte(t,{cta_start})'"
    )

    output = ep_dir / "output_final.mp4"
    assemble_video(concat_out, voice_bgm, vf, output, voice_dur)
    return output


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--ep",     required=True)
    parser.add_argument("--script", required=True)
    parser.add_argument("--bgm",    default="/root/content/runtime/health/bgm/bgm_dramatic_ambient.mp3")
    args = parser.parse_args()

    ep_dir = Path(args.ep)
    script = json.loads(Path(args.script).read_text(encoding="utf-8"))
    make_video(ep_dir, script, args.bgm)

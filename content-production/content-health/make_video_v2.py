"""
make_video_v2.py
================
S급 쇼츠 영상 합성 — v1 효과 완전 이식
- Ken Burns zoompan (짝수=줌인, 홀수=줌아웃)
- 상단/하단 검은 바 + 채널 브랜딩
- 장면별 자막 (ASS, 크고 임팩트 있는 스타일)
- BGM 믹싱 (voice 1.0 + bgm 0.18)
- TTS 실제 길이 기준으로 클립·자막 타이밍 결정 (싱크 보장)
"""
import asyncio
import json
import subprocess
import sys
from pathlib import Path

FONT_PATH = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
FONT_FALLBACK = "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc"
CHANNEL_NAME = "매일의 설계"
SLOGAN = "매일 하나씩, 건강 상식을 쌓자"
WATERMARK = "© 2026 매일의 설계"
TOP_BAR_RATIO = 0.20
BOT_BAR_RATIO = 0.18


def get_font() -> str:
    for p in [FONT_PATH, FONT_FALLBACK]:
        if Path(p).exists():
            return p
    return "NotoSansCJK-Bold"


def get_duration(path: str) -> float:
    r = subprocess.run([
        "ffprobe", "-i", path,
        "-show_entries", "format=duration",
        "-v", "quiet", "-of", "csv=p=0"
    ], capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except:
        return 0.0


def make_silence(path: str, duration: float):
    subprocess.run([
        "ffmpeg", "-y", "-f", "lavfi",
        "-i", "anullsrc=r=44100:cl=stereo",
        "-t", str(duration), "-q:a", "9",
        "-acodec", "libmp3lame", path
    ], capture_output=True)


def run_cmd(cmd: list, label: str = "") -> bool:
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"  ❌ FFmpeg 오류 [{label}]: {r.stderr[-200:]}")
        return False
    return True


# 장면 인덱스별 TTS 속도: Hook 느리게(강조), 과학설명 빠르게(압축감), 감정충격 느리게(여운)
SCENE_TTS_RATES = [
    "-5%",   # 0: Hook        — 느리고 강하게
    "+8%",   # 1: 과학설명1   — 빠르게, 정보 압축감
    "+5%",   # 2: 과학설명2   — 약간 빠르게
    "+0%",   # 3: 잘못된상식  — 보통 속도, 공감 유발
    "-8%",   # 4: 감정충격    — 매우 느리게, 여운
    "+5%",   # 5: 저장유도    — 약간 빠르게
    "+12%",  # 6: 루프트리거  — 매우 빠르게, 긴박감
]


async def _tts_async(text: str, voice: str, out_path: str, rate: str = "+0%"):
    import edge_tts
    communicate = edge_tts.Communicate(text, voice, rate=rate)
    await communicate.save(out_path)


def generate_scene_tts(scenes: list, ep_dir: Path, voice: str = "ko-KR-SunHiNeural") -> tuple:
    """장면별 TTS 생성. 실제 TTS 길이를 그대로 사용 (padding/trim 없음).
    Returns: (voice_file, actual_durations)
    """
    print("  🎙️ 장면별 TTS 생성 중...")
    scene_audio_files = []
    actual_durations = []

    for i, scene in enumerate(scenes):
        narration = scene.get("narration", "").strip()
        scene_audio = ep_dir / f"tts_scene{i+1}.mp3"

        if narration:
            rate = SCENE_TTS_RATES[i] if i < len(SCENE_TTS_RATES) else "+0%"
            asyncio.run(_tts_async(narration, voice, str(scene_audio), rate))
            tts_dur = get_duration(str(scene_audio))
            scene_audio_files.append(str(scene_audio))
            actual_durations.append(tts_dur)
            print(f"    scene{i+1}: {tts_dur:.2f}초 (나레이션, rate={rate})")
        else:
            # 나레이션 없는 장면 → 원본 duration 유지
            dur = float(scene["duration"])
            make_silence(str(scene_audio), dur)
            scene_audio_files.append(str(scene_audio))
            actual_durations.append(dur)
            print(f"    scene{i+1}: {dur:.2f}초 (silence)")

    # 전체 concat
    voice_file = ep_dir / "voice_ko.mp3"
    concat_list = ep_dir / "tts_full_concat.txt"
    concat_list.write_text(
        "\n".join(f"file '{f}'" for f in scene_audio_files), encoding="utf-8"
    )
    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", str(concat_list), "-c", "copy", str(voice_file)
    ], capture_output=True)

    total = get_duration(str(voice_file))
    print(f"  ✅ TTS 완료: {voice_file} ({total:.2f}초, {len(scenes)}장면)")
    return voice_file, actual_durations


def build_ass(scenes: list, ep_dir: Path, font_path: str, durations: list) -> Path:
    """장면별 자막 ASS 생성. durations = TTS 실제 길이 리스트."""
    top_bar_h = int(1920 * TOP_BAR_RATIO)
    bot_bar_h = int(1920 * BOT_BAR_RATIO)
    content_h = 1920 - top_bar_h - bot_bar_h
    content_center_y = top_bar_h + content_h // 2

    lines = [
        "[Script Info]",
        "ScriptType: v4.00+",
        "PlayResX: 1080",
        "PlayResY: 1920",
        "Collisions: Normal",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        f"Style: Hook,NotoSansCJK-Bold,80,&H0000AAFF,&H000000FF,&H00000000,&HAA000000,-1,0,0,0,100,100,2,0,3,4,2,5,60,60,{content_center_y - 80},1",
        f"Style: Main,NotoSansCJK-Bold,68,&H00FFFFFF,&H000000FF,&H00000000,&HAA000000,-1,0,0,0,100,100,2,0,3,3,2,5,60,60,{content_center_y - 68},1",
        f"Style: Save,NotoSansCJK-Bold,64,&H0000FFFF,&H000000FF,&H00000000,&HAA000000,-1,0,0,0,100,100,2,0,3,3,2,5,60,60,{content_center_y - 64},1",
        f"Style: Loop,NotoSansCJK-Bold,60,&H00FFFF00,&H000000FF,&H00000000,&HAA000000,-1,0,0,0,100,100,2,0,3,3,2,2,60,60,80,1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]

    current = 0.0
    for i, (scene, dur) in enumerate(zip(scenes, durations)):
        start = _ts(current)
        end = _ts(current + dur - 0.05)
        caption = scene.get("caption", "").replace("\n", "\\N")

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


def _ts(sec: float) -> str:
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = sec % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def make_ken_burns_clip(img_path: Path, duration: float, index: int, out_path: Path) -> bool:
    """v1 동일 Ken Burns: 짝수=줌인, 홀수=줌아웃"""
    frames = int(duration * 25)
    if index % 2 == 0:
        zoom_expr = "min(zoom+0.0008,1.3)"
    else:
        zoom_expr = "if(eq(on,1),1.3,max(zoom-0.0008,1.0))"

    return run_cmd([
        "ffmpeg", "-y",
        "-loop", "1", "-i", str(img_path),
        "-t", str(duration),
        "-vf",
        f"scale=8000:-1,"
        f"zoompan=z='{zoom_expr}':d={frames}:"
        f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920,"
        f"eq=contrast=1.05:saturation=1.0:brightness=-0.02,fps=25",
        "-c:v", "libx264", "-crf", "18", "-preset", "medium",
        "-pix_fmt", "yuv420p", str(out_path)
    ], f"ken_burns_{index}")


def make_video(ep_dir: Path, script: dict, bgm_path: str = None, generate_tts: bool = True) -> Path:
    scenes = script["scenes"]
    font_path = get_font()
    hook = script.get("hook", script.get("title", ""))

    mid = len(hook) // 2
    for i in range(mid, len(hook)):
        if hook[i] == " ":
            mid = i
            break
    t1 = hook[:mid].strip()
    t2 = hook[mid:].strip() if mid < len(hook) else ""

    print(f"\n[1/6] 🎙️ TTS 생성...")
    voice_file = ep_dir / "voice_ko.mp3"
    if generate_tts and not voice_file.exists():
        voice_file, actual_durations = generate_scene_tts(scenes, ep_dir)
    elif voice_file.exists():
        # 이미 생성된 경우 — scene별 파일에서 실제 길이 복원
        actual_durations = []
        for i, scene in enumerate(scenes):
            tts_file = ep_dir / f"tts_scene{i+1}.mp3"
            if tts_file.exists():
                actual_durations.append(get_duration(str(tts_file)))
            else:
                actual_durations.append(float(scene["duration"]))
    else:
        actual_durations = [float(s["duration"]) for s in scenes]
        make_silence(str(voice_file), sum(actual_durations))

    total_dur = sum(actual_durations)
    print(f"  총 길이: {total_dur:.2f}초")
    if total_dur > 30:
        print(f"  ⚠️ 영상 {total_dur:.1f}초 — 30초 초과, 완시율 하락 위험. 나레이션 단축 권장")
    elif total_dur < 18:
        print(f"  ⚠️ 영상 {total_dur:.1f}초 — 18초 미만, 정보량 부족 위험")

    print(f"\n[2/6] 🎨 Ken Burns 이미지 클립 생성...")
    clip_files = []
    for i, (scene, dur) in enumerate(zip(scenes, actual_durations)):
        img = ep_dir / f"bg{i+1}.jpg"
        if not img.exists():
            img = ep_dir / "bg1.jpg"
        clip_out = ep_dir / f"clip{i+1}.mp4"
        ok = make_ken_burns_clip(img, dur, i, clip_out)
        if ok:
            clip_files.append(clip_out)
            print(f"  ✅ clip{i+1} ({dur:.2f}초, {'줌인' if i%2==0 else '줌아웃'})")

    print(f"\n[3/6] 🔗 클립 연결...")
    concat_list = ep_dir / "concat.txt"
    concat_list.write_text("\n".join(f"file '{c}'" for c in clip_files), encoding="utf-8")
    concat_out = ep_dir / "video_only.mp4"
    run_cmd(["ffmpeg", "-y", "-f", "concat", "-safe", "0",
             "-i", str(concat_list), "-c", "copy", str(concat_out)], "concat")

    print(f"\n[4/6] 🎵 BGM 믹싱...")
    base_mp4 = ep_dir / "base.mp4"
    if bgm_path and Path(bgm_path).exists():
        run_cmd([
            "ffmpeg", "-y",
            "-i", str(concat_out), "-i", str(voice_file), "-i", bgm_path,
            "-filter_complex",
            "[1:a]volume=1.0[v];[2:a]volume=0.18[b];[v][b]amix=inputs=2:duration=first[aout]",
            "-map", "0:v", "-map", "[aout]",
            "-c:v", "copy", "-c:a", "aac", "-ar", "44100", "-ac", "2",
            str(base_mp4)
        ], "bgm_mix")
        print("  ✅ BGM 믹싱 완료")
    else:
        run_cmd([
            "ffmpeg", "-y",
            "-i", str(concat_out), "-i", str(voice_file),
            "-map", "0:v", "-map", "1:a",
            "-c:v", "copy", "-c:a", "aac",
            str(base_mp4)
        ], "audio_mix")

    print(f"\n[5/6] 📝 자막 생성...")
    ass_file = build_ass(scenes, ep_dir, font_path, actual_durations)
    print(f"  ✅ 자막 완료: {ass_file}")

    print(f"\n[6/6] 🎬 최종 출력 (상하 바 + 브랜딩 + 자막)...")
    top_bar_h = int(1920 * TOP_BAR_RATIO)
    bot_bar_h = int(1920 * BOT_BAR_RATIO)
    title_y1 = int(1920 * 0.07)
    title_y2 = title_y1 + 85
    watermark_y = int(1920 - bot_bar_h + bot_bar_h * 0.20)
    slogan_y = watermark_y + 45

    vf = (
        f"drawbox=x=0:y=0:w=iw:h={top_bar_h}:color=black@1.0:t=fill,"
        f"drawbox=x=0:y=ih-{bot_bar_h}:w=iw:h={bot_bar_h}:color=black@1.0:t=fill,"
        f"ass={ass_file},"
        f"drawtext=fontfile={font_path}:text='{t1}':fontsize=56:fontcolor=white@0.95:"
        f"x=(w-text_w)/2:y={title_y1}:borderw=3:bordercolor=black@0.8,"
        f"drawtext=fontfile={font_path}:text='{t2}':fontsize=68:fontcolor=#FF8C00:"
        f"x=(w-text_w)/2:y={title_y2}:borderw=3:bordercolor=black@0.8,"
        f"drawtext=fontfile={font_path}:text='{WATERMARK}':fontsize=26:fontcolor=white@0.45:"
        f"x=(w-text_w)/2:y={watermark_y}:borderw=1:bordercolor=black@0.3,"
        f"drawtext=fontfile={font_path}:text='{SLOGAN}':fontsize=24:fontcolor=white@0.7:"
        f"x=(w-text_w)/2:y={slogan_y}:borderw=1:bordercolor=black@0.3"
    )

    output = ep_dir / "output_final.mp4"
    ok = run_cmd([
        "ffmpeg", "-y", "-i", str(base_mp4),
        "-vf", vf,
        "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-pix_fmt", "yuv420p", "-c:a", "copy",
        str(output)
    ], "final")

    if ok:
        print(f"\n✅ 완성: {output}")
        print(f"   총 길이: {total_dur:.1f}초")
    else:
        print("❌ 최종 출력 실패")
    return output


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--ep", required=True)
    parser.add_argument("--script", required=True)
    parser.add_argument("--bgm", default="/root/content/runtime/health/bgm/bgm_dramatic_ambient.mp3")
    args = parser.parse_args()

    ep_dir = Path(args.ep)
    script = json.loads(Path(args.script).read_text(encoding="utf-8"))
    make_video(ep_dir, script, args.bgm)

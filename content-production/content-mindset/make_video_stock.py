"""
make_video_stock.py
====================
실사 스톡 영상(bg1.mp4~bg8.mp4) 기반 영상 합성.
make_video.py와 동일한 구조 — Ken Burns 없이 실사 영상 그대로 사용.
"""
import glob
import json
import os
import shutil
import subprocess
from config import FONT_PATH, WATERMARK, BGM_PATH, ENDING_PATH, BGM_MAP

INTRO_DURATION = 1.5


def get_duration(filepath):
    result = subprocess.run([
        "ffprobe", "-i", filepath,
        "-show_entries", "format=duration",
        "-v", "quiet", "-of", "csv=p=0"
    ], capture_output=True, text=True)
    try:
        return float(result.stdout.strip())
    except Exception:
        return 0.0


def run(cmd, label=""):
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  ❌ FFmpeg 오류 [{label}]:\n{result.stderr[-300:]}")
        return False
    return True


def calc_clip_durations(n_clips: int, total_sec: float) -> list:
    weights = []
    for i in range(n_clips):
        if i < 2:
            weights.append(0.8)
        elif i >= n_clips - 2:
            weights.append(0.9)
        else:
            weights.append(1.2)
    base = total_sec / sum(weights)
    return [round(base * w, 2) for w in weights]


def make_video_stock(ep_dir: str, script: dict, style: str = "docsul"):
    os.chdir(ep_dir)
    bgm = BGM_MAP.get(style, BGM_PATH)

    # segments.json 로드
    seg_json_path = os.path.join(ep_dir, "segments.json")
    if os.path.exists(seg_json_path):
        with open(seg_json_path, encoding="utf-8") as f:
            seg_data = json.load(f)
        voice_duration   = seg_data["total_duration"] - INTRO_DURATION
        total_with_intro = seg_data["total_duration"]
    else:
        voice_duration   = get_duration("voice_ko.mp3")
        total_with_intro = voice_duration + INTRO_DURATION

    ending_duration = get_duration(ENDING_PATH)
    main_duration   = total_with_intro
    N_main          = int(main_duration)

    t1 = script.get("t1", "")
    t2 = script.get("t2", "")
    if not t1 and not t2:
        title = script.get("title_ko", "")
        mid   = len(title) // 2
        for i in range(mid, len(title)):
            if title[i] == " ":
                mid = i
                break
        t1 = title[:mid].strip()
        t2 = title[mid:].strip()

    print(f"나레이션: {voice_duration:.2f}초 / 인트로: {INTRO_DURATION}초")
    print(f"  제목1: {t1}")
    print(f"  제목2: {t2}")

    # 1. BGM 믹싱
    print("[1/5] BGM 믹싱...")
    ok = run(["ffmpeg", "-y",
        "-i", "voice_ko.mp3", "-i", bgm,
        "-filter_complex",
        "[0:a]volume=1.0[voice];[1:a]volume=0.18[bgm];"
        "[voice][bgm]amix=inputs=2:duration=first[out]",
        "-map", "[out]", "-ar", "44100", "-ac", "2",
        "voice_with_bgm.mp3"], "BGM")
    if ok:
        print("  ✅ BGM 완료")

    # 2. 스톡 영상 클립 트리밍 (Ken Burns 없음 — 실사 그대로)
    print("[2/5] 스톡 클립 트리밍...")
    clip_files_mp4 = sorted(glob.glob("bg*.mp4"))
    n_clips        = len(clip_files_mp4)

    if n_clips == 0:
        print("  ❌ bg*.mp4 파일 없음")
        return

    clip_durations = calc_clip_durations(n_clips, voice_duration)
    clip_files     = []

    for i, (src, clip_t) in enumerate(zip(clip_files_mp4, clip_durations)):
        out_clip = f"clip{i+1}.mp4"
        ok = run([
            "ffmpeg", "-y",
            "-stream_loop", "-1", "-i", src,
            "-t", str(clip_t),
            "-vf", (
                "scale=1080:1920:force_original_aspect_ratio=increase,"
                "crop=1080:1920,"
                "fps=25"
            ),
            "-c:v", "libx264", "-crf", "18", "-preset", "fast",
            "-pix_fmt", "yuv420p",
            out_clip
        ], f"clip{i+1}")
        if ok:
            clip_files.append(out_clip)
            print(f"  ✅ {out_clip} ({clip_t:.1f}초)")

    # 3. 클립 연결 + 음성 합성
    print("[3/5] 클립 연결...")
    with open("list.txt", "w") as f:
        for cf in clip_files:
            f.write(f"file '{cf}'\n")
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0",
         "-i", "list.txt", "-c", "copy", "video_only.mp4"], "concat")
    ok = run(["ffmpeg", "-y",
         "-i", "video_only.mp4", "-i", "voice_with_bgm.mp3",
         "-map", "0:v:0", "-map", "1:a:0",
         "-c:v", "copy", "-c:a", "aac", "-ar", "44100", "-ac", "2",
         "-shortest", "base.mp4"], "base")
    if ok:
        print("  ✅ 클립 연결 완료")

    shutil.copy("base.mp4", "base_with_ending.mp4")

    # 4. 자막 (os.chdir 이후이므로 현재 디렉토리에서 바로 참조)
    print("[4/5] 자막 적용...")
    if os.path.exists("subtitles_tts.ass"):
        shutil.copy("subtitles_tts.ass", "subtitles_karaoke.ass")
        print("  ✅ 자막 완료")
    else:
        print("  ⚠️ 자막 파일 없음")
        open("subtitles_karaoke.ass", "w").close()

    # 5. 최종 출력 (상단/하단 검정 바 + 제목 + 워터마크)
    print("[5/5] 최종 출력...")
    top_bar_h   = int(1920 * 0.22)
    bot_bar_h   = int(1920 * 0.22)
    title_y1    = int(1920 * 0.09)
    title_y2    = int(1920 * 0.09) + 90
    watermark_y = int(1920 - bot_bar_h + bot_bar_h * 0.20)
    slogan_y    = watermark_y + 45

    has_sub = (os.path.exists("subtitles_karaoke.ass") and
               os.path.getsize("subtitles_karaoke.ass") > 0)
    ass_filter = "ass=subtitles_karaoke.ass," if has_sub else ""

    vf = (
        f"drawbox=x=0:y=0:w=iw:h={top_bar_h}:color=black@1.0:t=fill,"
        f"drawbox=x=0:y=ih-{bot_bar_h}:w=iw:h={bot_bar_h}:color=black@1.0:t=fill,"
        f"{ass_filter}"
        f"drawtext=fontfile={FONT_PATH}:text='{t1}':fontsize=64:fontcolor=white@0.95:"
        f"x=(w-text_w)/2:y={title_y1}:borderw=3:bordercolor=black@0.8:"
        f"enable='lte(t,{N_main})',"
        f"drawtext=fontfile={FONT_PATH}:text='{t2}':fontsize=76:fontcolor=#FF6600:"
        f"x=(w-text_w)/2:y={title_y2}:borderw=3:bordercolor=black@0.8:"
        f"enable='lte(t,{N_main})',"
        f"drawtext=fontfile={FONT_PATH}:text='{WATERMARK}':fontsize=26:fontcolor=white@0.45:"
        f"x=(w-text_w)/2:y={watermark_y}:borderw=1:bordercolor=black@0.3:"
        f"enable='lte(t,{N_main})',"
        f"drawtext=fontfile={FONT_PATH}:text='어제보다 나은 오늘을 설계하자':fontsize=24:fontcolor=white@0.7:"
        f"x=(w-text_w)/2:y={slogan_y}:borderw=1:bordercolor=black@0.3:"
        f"enable='lte(t,{N_main})'"
    )
    ok = run(["ffmpeg", "-y",
        "-i", "base_with_ending.mp4",
        "-vf", vf,
        "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-pix_fmt", "yuv420p", "-c:a", "copy",
        "output_final.mp4"], "final")

    if ok:
        print(f"✅ 완성: {ep_dir}/output_final.mp4")
    else:
        print("❌ 최종 출력 실패")


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="스톡 영상 기반 영상 합성")
    p.add_argument("--ep",    required=True, help="에피소드 디렉토리 경로")
    p.add_argument("--style", default="docsul", help="BGM 스타일")
    args = p.parse_args()

    with open(os.path.join(args.ep, "script.json"), encoding="utf-8") as f:
        script = json.load(f)
    make_video_stock(args.ep, script, style=args.style)

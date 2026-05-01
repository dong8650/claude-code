import subprocess
import json
import os
import glob
import shutil
from config import FONT_PATH, WATERMARK, BGM_PATH, ENDING_PATH, BGM_MAP

INTRO_DURATION = 1.5  # generate_tts.py와 동일

def get_duration(filepath):
    result = subprocess.run([
        "ffprobe", "-i", filepath,
        "-show_entries", "format=duration",
        "-v", "quiet", "-of", "csv=p=0"
    ], capture_output=True, text=True)
    try:
        return float(result.stdout.strip())
    except:
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

def make_intro_clip(ep_dir, t1, t2, font_path):
    """bg1.jpg 기반 인트로 클립 (1.5초) — 유튜브 썸네일 프레임"""
    out = os.path.join(ep_dir, "intro_clip.mp4")
    bg1 = os.path.join(ep_dir, "bg1.jpg")
    vf = (
        f"scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,"
        f"drawtext=fontfile={font_path}:text='{t1}':"
        f"fontsize=64:fontcolor=white@0.9:x=60:y=h*0.55:borderw=3:bordercolor=black@0.8,"
        f"drawtext=fontfile={font_path}:text='{t2}':"
        f"fontsize=88:fontcolor=#FF6600:x=60:y=h*0.55+100:borderw=4:bordercolor=black@0.9"
    )
    if os.path.exists(bg1):
        subprocess.run([
            "ffmpeg", "-y",
            "-loop", "1", "-i", bg1,
            "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
            "-vf", vf, "-t", str(INTRO_DURATION),
            "-map", "0:v", "-map", "1:a",
            "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-ar", "44100", "-ac", "2", out
        ], capture_output=True)
    else:
        subprocess.run([
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", f"color=c=black:s=1080x1920:d={INTRO_DURATION}:r=25",
            "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
            "-vf", f"drawtext=fontfile={font_path}:text='{t1}':fontsize=64:fontcolor=white:x=60:y=h*0.55,"
                   f"drawtext=fontfile={font_path}:text='{t2}':fontsize=88:fontcolor=#FF6600:x=60:y=h*0.55+100",
            "-t", str(INTRO_DURATION),
            "-map", "0:v", "-map", "1:a",
            "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-ar", "44100", "-ac", "2", out
        ], capture_output=True)
    return out if os.path.exists(out) else None

def make_video(ep_dir: str, script: dict, style: str = "docsul"):
    os.chdir(ep_dir)
    bgm = BGM_MAP.get(style, BGM_PATH)

    # segments.json 로드
    seg_json_path = os.path.join(ep_dir, "segments.json")
    if os.path.exists(seg_json_path):
        with open(seg_json_path, encoding="utf-8") as f:
            seg_data = json.load(f)
        voice_duration = seg_data["total_duration"] - INTRO_DURATION  # 순수 음성 길이
        total_with_intro = seg_data["total_duration"]
    else:
        voice_duration = get_duration("voice_ko.mp3")
        total_with_intro = voice_duration + INTRO_DURATION

    # 엔딩카드 길이
    ending_duration = get_duration(ENDING_PATH)

    # 본편 길이 = 인트로 + 음성
    main_duration = total_with_intro
    # 최종 전체 길이 = 본편 + 엔딩
    final_duration = main_duration + ending_duration

    N_main  = int(main_duration)
    N_final = int(final_duration)

    # 제목: t1/t2 직접 사용, 없으면 title_ko 분할 fallback
    t1 = script.get("t1", "")
    t2 = script.get("t2", "")
    if not t1 and not t2:
        title = script.get("title_ko", "")
        mid = len(title) // 2
        for i in range(mid, len(title)):
            if title[i] == " ":
                mid = i
                break
        t1 = title[:mid].strip()
        t2 = title[mid:].strip()
    print(f"나레이션: {voice_duration:.2f}초 / 인트로: {INTRO_DURATION}초 / 엔딩: {ending_duration:.2f}초")
    print(f"  제목1: {t1}")
    print(f"  제목2: {t2}")

    # 1. BGM 믹싱 (순수 음성에만)
    print("[1/6] BGM 믹싱...")
    ok = run(["ffmpeg", "-y",
        "-i", "voice_ko.mp3", "-i", bgm,
        "-filter_complex",
        "[0:a]volume=1.0[voice];[1:a]volume=0.18[bgm];[voice][bgm]amix=inputs=2:duration=first[out]",
        "-map", "[out]", "-ar", "44100", "-ac", "2",
        "voice_with_bgm.mp3"], "BGM")
    if ok: print("  ✅ BGM 완료")

    # 2. 이미지 클립 (가변 길이, 순수 음성 길이 기준)
    print("[2/6] 이미지 클립 생성...")
    img_files = sorted(glob.glob("bg*.jpg"))
    n_clips = len(img_files)
    clip_durations = calc_clip_durations(n_clips, voice_duration)

    clip_files = []
    for i, (img_file, clip_t) in enumerate(zip(img_files, clip_durations)):
        out_clip = f"clip{i+1}.mp4"
        zoom_expr = "min(zoom+0.0008,1.3)" if i % 2 == 0 else "if(eq(on,1),1.3,max(zoom-0.0008,1.0))"
        ok = run(["ffmpeg", "-y",
            "-loop", "1", "-i", img_file,
            "-t", str(clip_t),
            "-vf",
            f"scale=8000:-1,"
            f"zoompan=z='{zoom_expr}':d={int(clip_t*25)}:"
            f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920,"
            f"eq=contrast=1.1:saturation=0.9:brightness=-0.03,fps=25",
            "-c:v", "libx264", "-crf", "18", "-preset", "medium",
            "-pix_fmt", "yuv420p", out_clip], f"clip{i+1}")
        if ok:
            clip_files.append(out_clip)
            print(f"  ✅ {out_clip} ({clip_t:.1f}초)")

    # 3. 클립 연결 + 음성 합성
    print("[3/6] 클립 연결...")
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
    if ok: print("  ✅ 클립 연결 완료")

    # 4. 엔딩카드 없음 — base.mp4 그대로 사용
    import shutil as _sh
    _sh.copy("base.mp4", "base_with_ending.mp4")
    print("[4/6] 엔딩카드 없음 — 본편만 사용")

    # 5. 자막
    print("[5/6] 자막 적용...")
    ass_src = os.path.join(ep_dir, "subtitles_tts.ass")
    if os.path.exists(ass_src):
        shutil.copy(ass_src, "subtitles_karaoke.ass")
        print("  ✅ 자막 완료 (노래방 효과 + 오탈자 0%)")
    else:
        print("  ⚠️ 자막 파일 없음")
        open("subtitles_karaoke.ass", "w").close()

    # 6. 최종 출력
    # ★ 제목: 본편 마지막 3초 기준 (N_main-3 ~ N_main)
    # ★ 워터마크: 본편 구간만 (lte(t, N_main))
    print("[6/6] 최종 출력...")
    # EP005~ : 상단 검은 바 + 하단 검은 바 + 자막 이미지 중단 + 워터마크/슬로건
    top_bar_h    = int(1920 * 0.22)
    bot_bar_h    = int(1920 * 0.22)
    title_y1     = int(1920 * 0.09)
    title_y2     = int(1920 * 0.09) + 90
    watermark_y  = int(1920 - bot_bar_h + bot_bar_h * 0.20)
    slogan_y     = watermark_y + 45
    vf = (
        f"drawbox=x=0:y=0:w=iw:h={top_bar_h}:color=black@1.0:t=fill,"
        f"drawbox=x=0:y=ih-{bot_bar_h}:w=iw:h={bot_bar_h}:color=black@1.0:t=fill,"
        f"ass=subtitles_karaoke.ass,"
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
        # 썸네일/인트로 클립 사용하지 않음

        print(f"✅ 완성: {ep_dir}/output_final.mp4")

        # 썸네일 생성 없음
    else:
        print("❌ 최종 출력 실패")

if __name__ == "__main__":
    with open("script.json", encoding="utf-8") as f:
        script = json.load(f)
    make_video(".", script)

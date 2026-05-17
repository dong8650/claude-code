"""
test_run_stock.py
=================
[테스트] Pexels 실사 스톡 영상 스타일 — 달리기 후 뇌 변화

달리기/뇌 관련 Pexels 영상 클립을 씬별로 다운로드하고
health 채널 포맷(TTS + ASS 자막 + 브랜딩 + CTA)으로 합성.
DALL-E 이미지 없음, Ken Burns 없음.
기존 make_video_v2.py / generate_image_v2.py 코드 변경 없음.

실행: python3 test_run_stock.py
출력: /root/content/runtime/health/episodes/test_stock_YYYYMMDD_001/output_final.mp4

사전 조건:
  pip install requests
  PEXELS_API_KEY: /root/content/runtime/health/config.py 또는
                  /root/content/runtime/mindset/config.py 에 존재해야 함
"""
import importlib.util
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path
from datetime import datetime

BASE_DIR    = Path(__file__).parent
RUNTIME_DIR = Path("/root/content/runtime/health")
_CORE       = BASE_DIR.parent / "content-pipeline-core"
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(_CORE))

# ── Pexels API 키 로드 (health → mindset 순 fallback) ─────────────────────
def _get_pexels_key() -> str:
    for cfg_dir in [RUNTIME_DIR, Path("/root/content/runtime/mindset")]:
        try:
            spec = importlib.util.spec_from_file_location("_cfg", cfg_dir / "config.py")
            m = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(m)
            key = getattr(m, "PEXELS_API_KEY", None)
            if key:
                return key
        except Exception:
            continue
    raise RuntimeError("PEXELS_API_KEY 없음 — health 또는 mindset config.py 확인 필요")

# ── 씬별 Pexels 검색 키워드 (7씬 고정) ─────────────────────────────────────
SCENE_KEYWORDS = [
    "person running morning park",       # scene1 hook
    "runner happy motivation training",  # scene2 dopamine
    "brain neuron science glowing",      # scene3 BDNF
    "tired person lying couch rest",     # scene4 잘못된상식
    "person sitting inactive sedentary", # scene5 감정충격
    "running shoes sport motivation",    # scene6 저장유도
    "runner starting trail run",         # scene7 루프트리거
]

FALLBACK_KEYWORDS = [
    "running exercise outdoor",
    "fitness workout sport",
    "person active healthy",
]

# ── 스크립트 ────────────────────────────────────────────────────────────────
SCRIPT = {
    "title": "달리기 후 뇌 변화",
    "content_type": "건강상식",
    "hook": "달리기 20분 후 뇌에서 일어나는 일",
    "scenes": [
        {
            "duration": 3,
            "caption": "달리기 20분 후\n뇌에서 일어나는 일",
            "narration": "달리기 20분 후 뇌에서 일어나는 일",
        },
        {
            "duration": 5,
            "caption": "도파민 + 세로토닌 동시 분비\n→ 항우울제와 동일한 효과\n→ 지속 시간 최대 2~3시간 🧠",
            "narration": "도파민, 세로토닌 동시 분비. 항우울제와 동일한 효과, 2~3시간 지속",
        },
        {
            "duration": 6,
            "caption": "BDNF(뇌유래신경영양인자) 분비\n→ 뇌세포 새로 생성\n→ 기억력·집중력 즉시 향상 💡",
            "narration": "BDNF 분비로 뇌세포가 새로 생성됩니다. 기억력, 집중력 즉시 향상",
        },
        {
            "duration": 5,
            "caption": "근데 대부분이\n'운동 후에 머리 아프다'\n그냥 쉬어버림 ⚠️",
            "narration": "근데 대부분은 운동 후 머리 아프다며 그냥 쉬어버림",
        },
        {
            "duration": 3,
            "caption": "매일 쉬기만 했던 당신\n뇌가 굶고 있었음 😱",
            "narration": "매일 쉬기만 했던 당신, 뇌가 굶고 있었음",
        },
        {
            "duration": 2,
            "caption": "저장해두고 운동 하기 싫을 때\n꺼내봐 💾",
            "narration": "저장해두고 꺼내봐",
        },
        {
            "duration": 1,
            "caption": "처음부터 보면 복선 있음 👀",
            "narration": "",
        },
    ],
    "total_duration": 25,
    "tags_ko": ["건강상식연구소", "달리기", "뇌과학", "운동효과", "쇼츠"],
}


# ── Pexels 다운로드 ──────────────────────────────────────────────────────────

def _best_video_file(video_files: list) -> dict | None:
    """4K(uhd) → FHD(hd/1080) → HD(720) 순으로 최고 화질 파일 선택."""
    sorted_files = sorted(video_files, key=lambda x: -(x.get("height", 0)))
    # 1순위: 4K
    for f in sorted_files:
        if f.get("quality") == "uhd" and f.get("height", 0) >= 2160:
            return f
    # 2순위: FHD (1080p 이상)
    for f in sorted_files:
        if f.get("quality") in ("uhd", "hd") and f.get("height", 0) >= 1080:
            return f
    # 3순위: HD (720p 이상) — 최후 수단
    for f in sorted_files:
        if f.get("height", 0) >= 720:
            return f
    return None


def _search_pexels(keyword: str, headers: dict) -> tuple[str | None, str]:
    """최고 화질 Pexels 영상 URL 반환. portrait 우선 → landscape fallback.
    Returns: (url, resolution_info)
    """
    import requests
    for orient in ("portrait", "landscape"):
        try:
            r = requests.get(
                "https://api.pexels.com/videos/search",
                headers=headers,
                params={
                    "query": keyword, "per_page": 15,
                    "orientation": orient,
                    "size": "large",   # width >= 1920 보장
                },
                timeout=15,
            )
            if r.status_code != 200:
                continue
            for v in r.json().get("videos", []):
                f = _best_video_file(v.get("video_files", []))
                if f:
                    info = f"{orient} {f.get('width')}×{f.get('height')} [{f.get('quality')}]"
                    return f["link"], info
        except Exception:
            continue
    return None, ""


def _download_raw(url: str, tmp_path: str) -> bool:
    import requests
    try:
        r = requests.get(url, stream=True, timeout=60)
        if r.status_code != 200:
            return False
        with open(tmp_path, "wb") as f:
            for chunk in r.iter_content(8192):
                f.write(chunk)
        return True
    except Exception as e:
        print(f"    ⚠️ 다운로드 실패: {e}")
        return False


def download_scene_clips(scenes: list, ep_dir: Path) -> None:
    """씬별 Pexels 클립 다운로드 → bg1~7.mp4 (raw, 길이는 TTS 후 트리밍)."""
    import requests
    headers = {"Authorization": _get_pexels_key()}

    print(f"📹 Pexels 스톡 클립 다운로드 ({len(scenes)}씬)...")
    for i, (scene, keyword) in enumerate(zip(scenes, SCENE_KEYWORDS), start=1):
        out_path = ep_dir / f"bg{i}.mp4"
        if out_path.exists():
            print(f"  ⏭️  bg{i}.mp4 이미 존재, 스킵")
            continue

        print(f"  [{i}/{len(scenes)}] '{keyword}'")
        url, info = _search_pexels(keyword, headers)
        if not url:
            for fb in FALLBACK_KEYWORDS:
                url, info = _search_pexels(fb, headers)
                if url:
                    print(f"    → fallback: {fb}")
                    break

        if not url:
            print(f"    ❌ 클립 없음")
            continue
        print(f"    📐 {info}")

        tmp = str(out_path).replace(".mp4", "_raw.mp4")
        if not _download_raw(url, tmp):
            continue

        # portrait 1080×1920 로 크롭만 (길이는 TTS 측정 후 별도 트리밍)
        result = subprocess.run([
            "ffmpeg", "-y", "-i", tmp,
            "-vf", (
                "scale=1080:1920:force_original_aspect_ratio=increase,"
                "crop=1080:1920,"
                "eq=contrast=1.05:saturation=0.9:brightness=-0.02,"
                "fps=25"
            ),
            "-c:v", "libx264", "-crf", "18", "-preset", "fast",
            "-pix_fmt", "yuv420p", "-an",
            str(out_path),
        ], capture_output=True)

        Path(tmp).unlink(missing_ok=True)
        print(f"    {'✅' if result.returncode == 0 else '❌'} bg{i}.mp4")
        time.sleep(0.3)


# ── 영상 합성 (health 포맷, Ken Burns 없음) ──────────────────────────────────

def make_stock_video_health(ep_dir: Path, script: dict, bgm_path: str = None) -> Path:
    """Pexels 클립 기반 health 채널 영상 합성.

    make_video_v2.py 와 동일한 브랜딩·자막·CTA 적용.
    Ken Burns(zoompan) 없이 실사 클립을 TTS 길이에 맞게 트리밍.
    """
    from make_video_v2 import (
        generate_scene_tts, build_ass, get_font,
        SLOGAN, TOP_BAR_RATIO, BOT_BAR_RATIO,
    )
    from ffmpeg_utils import get_duration
    from audio_core import mix_bgm
    from channel_branding import WATERMARK
    from video_core import assemble_video

    scenes    = script["scenes"]
    font_path = get_font()
    hook      = script.get("hook", script.get("title", ""))

    mid = len(hook) // 2
    for i in range(mid, len(hook)):
        if hook[i] == " ":
            mid = i
            break
    t1 = hook[:mid].strip()
    t2 = hook[mid:].strip() if mid < len(hook) else ""

    # ── [1/5] TTS ─────────────────────────────────────────────────────────
    print(f"\n[1/5] 🎙️ TTS 생성...")
    voice_file = ep_dir / "voice_ko.mp3"
    if not voice_file.exists():
        voice_file, actual_durations = generate_scene_tts(scenes, ep_dir)
    else:
        actual_durations = []
        for i, scene in enumerate(scenes):
            tts_file = ep_dir / f"tts_scene{i+1}.mp3"
            actual_durations.append(
                get_duration(str(tts_file)) if tts_file.exists() else float(scene["duration"])
            )
    voice_dur = get_duration(str(voice_file))
    print(f"  음성 길이: {voice_dur:.2f}초")

    # ── [2/5] 스톡 클립 → TTS 길이로 트리밍 ──────────────────────────────
    print(f"\n[2/5] ✂️  스톡 클립 트리밍 (TTS 실제 길이 기준)...")
    clip_files = []
    actual_clip_durations = []

    for i, dur in enumerate(actual_durations):
        src = ep_dir / f"bg{i+1}.mp4"
        out = ep_dir / f"clip{i+1}.mp4"

        if not src.exists():
            print(f"  ⚠️ bg{i+1}.mp4 없음 — 씬 스킵")
            continue

        result = subprocess.run([
            "ffmpeg", "-y",
            "-stream_loop", "-1", "-i", str(src),
            "-t", f"{dur:.3f}",
            "-vf", "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=25",
            "-c:v", "libx264", "-crf", "18", "-preset", "fast",
            "-pix_fmt", "yuv420p",
            str(out),
        ], capture_output=True)

        if result.returncode == 0:
            clipped = get_duration(str(out))
            clip_files.append(out)
            actual_clip_durations.append(clipped)
            print(f"  ✅ clip{i+1} ({clipped:.2f}초)")
        else:
            print(f"  ❌ clip{i+1} 실패: {result.stderr[-200:].decode(errors='ignore')}")

    if not clip_files:
        raise RuntimeError("유효한 클립 없음 — Pexels 다운로드 결과 확인 필요")

    # ── [3/5] Concat ──────────────────────────────────────────────────────
    print(f"\n[3/5] 🔗 클립 연결...")
    concat_list = ep_dir / "clip_list.txt"
    concat_list.write_text("\n".join(f"file '{f}'" for f in clip_files), encoding="utf-8")
    concat_out = ep_dir / "video_only.mp4"
    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", str(concat_list), "-c", "copy", str(concat_out),
    ], capture_output=True)
    print(f"  ✅ concat 완료")

    # ── [4/5] BGM 믹싱 ────────────────────────────────────────────────────
    print(f"\n[4/5] 🎵 BGM 믹싱...")
    voice_bgm = ep_dir / "voice_bgm.mp3"
    if bgm_path and Path(bgm_path).exists():
        mix_bgm(voice_file, Path(bgm_path), voice_bgm, voice_dur)
        print("  ✅ BGM 믹싱 완료")
    else:
        shutil.copy(str(voice_file), str(voice_bgm))
        print("  ⚠️ BGM 파일 없음 — 음성만 사용")

    # ── [5/5] 자막 + 브랜딩 + CTA ────────────────────────────────────────
    print(f"\n[5/5] 📝 자막 + 브랜딩 + CTA...")
    ass_file = build_ass(scenes, ep_dir, font_path, actual_clip_durations)

    top_bar_h   = int(1920 * TOP_BAR_RATIO)
    bot_bar_h   = int(1920 * BOT_BAR_RATIO)
    title_y1    = int(1920 * 0.07)
    title_y2    = title_y1 + 85
    watermark_y = int(1920 - bot_bar_h + bot_bar_h * 0.20)
    slogan_y    = watermark_y + 45

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
    assemble_video(concat_out, voice_bgm, vf, output, voice_dur)
    return output


# ── main ────────────────────────────────────────────────────────────────────

def main():
    ep_dir = RUNTIME_DIR / "episodes" / f"test_stock_{datetime.now().strftime('%Y%m%d')}_001"
    ep_dir.mkdir(parents=True, exist_ok=True)
    print(f"\n📁 테스트 디렉토리: {ep_dir}")
    print("🎬 스타일: Pexels 실사 스톡 영상 (Ken Burns 없음)\n")

    (ep_dir / "script_v2.json").write_text(
        json.dumps(SCRIPT, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("✅ 스크립트 저장 완료\n")

    # Pexels 클립 다운로드
    download_scene_clips(SCRIPT["scenes"], ep_dir)
    print()

    # 영상 합성
    print("🎬 영상 합성 중 (TTS + 스톡 영상 + BGM)...")
    bgm_path = str(RUNTIME_DIR / "bgm/bgm_dramatic_ambient.mp3")
    output = make_stock_video_health(ep_dir, SCRIPT, bgm_path)
    print(f"\n✅ 완성: {output}")


if __name__ == "__main__":
    start = time.time()
    main()
    print(f"⏱️  총 소요: {time.time()-start:.1f}초")

"""
generate_stock_clips.py
========================
Pexels API로 스톡 영상 다운로드 → bg1.mp4 ~ bg8.mp4
script.json의 scenes 필드(영어)를 검색 키워드로 사용.

사용법:
  python generate_stock_clips.py --ep episodes/20260501_010
  python generate_stock_clips.py --ep episodes/20260501_010 --duration 4.5
"""
import argparse
import json
import subprocess
import time
from pathlib import Path

import requests

from config import PEXELS_API_KEY

HEADERS     = {"Authorization": PEXELS_API_KEY}
SEARCH_URL  = "https://api.pexels.com/videos/search"

FALLBACK_KEYWORDS = [
    "person walking city street",
    "office worker desk thinking",
    "calm water nature morning",
    "sunset silhouette person",
    "hands holding coffee cup",
    "city lights night bokeh",
    "person looking out window",
    "empty road sunrise fog",
]


def _search_pexels(keyword: str) -> str | None:
    """portrait 우선, landscape fallback으로 Pexels 영상 URL 반환."""
    for orient in ("portrait", "landscape"):
        try:
            r = requests.get(SEARCH_URL, headers=HEADERS, params={
                "query": keyword, "per_page": 10,
                "orientation": orient, "size": "medium",
            }, timeout=15)
            if r.status_code != 200:
                continue
            for v in r.json().get("videos", []):
                for f in sorted(v.get("video_files", []),
                                key=lambda x: -(x.get("height", 0))):
                    if f.get("quality") in ("hd", "sd") and f.get("height", 0) >= 720:
                        return f["link"]
        except Exception:
            continue
    return None


def _download_and_trim(url: str, out_path: str, duration: float) -> bool:
    """다운로드 → 1080×1920 크롭 → duration 트리밍 → 저장."""
    tmp = out_path.replace(".mp4", "_raw.mp4")
    try:
        r = requests.get(url, stream=True, timeout=60)
        if r.status_code != 200:
            return False
        with open(tmp, "wb") as f:
            for chunk in r.iter_content(8192):
                f.write(chunk)
    except Exception as e:
        print(f"    ⚠️ 다운로드 실패: {e}")
        return False

    result = subprocess.run([
        "ffmpeg", "-y",
        "-stream_loop", "-1", "-i", tmp,
        "-t", str(duration),
        "-vf", (
            "scale=1080:1920:force_original_aspect_ratio=increase,"
            "crop=1080:1920,"
            "eq=contrast=1.05:saturation=0.85:brightness=-0.02,"
            "fps=25"
        ),
        "-c:v", "libx264", "-crf", "18", "-preset", "fast",
        "-pix_fmt", "yuv420p", "-an",
        out_path,
    ], capture_output=True)

    Path(tmp).unlink(missing_ok=True)
    return result.returncode == 0


def generate_stock_clips(ep_dir: str, clip_duration: float = 5.0) -> int:
    """script.json scenes → Pexels 다운로드 → bg1.mp4~bg8.mp4."""
    script_path = Path(ep_dir) / "script.json"
    with open(script_path, encoding="utf-8") as f:
        script = json.load(f)

    scenes = list(script.get("scenes", []))
    while len(scenes) < 8:
        scenes.append(FALLBACK_KEYWORDS[len(scenes) % len(FALLBACK_KEYWORDS)])

    print(f"🎬 스톡 영상 다운로드 ({ep_dir})")
    success = 0
    for i, scene in enumerate(scenes[:8], start=1):
        keyword  = " ".join(scene.split()[:5])
        out_path = str(Path(ep_dir) / f"bg{i}.mp4")
        print(f"  [{i}/8] {keyword}")

        url = _search_pexels(keyword)
        if not url:
            fb = FALLBACK_KEYWORDS[(i - 1) % len(FALLBACK_KEYWORDS)]
            print(f"    → fallback: {fb}")
            url = _search_pexels(fb)

        if not url:
            print(f"    ❌ 영상 없음")
            continue

        ok = _download_and_trim(url, out_path, clip_duration)
        print(f"    {'✅' if ok else '❌'} bg{i}.mp4")
        if ok:
            success += 1
        time.sleep(0.3)

    print(f"\n완료: {success}/8 다운로드 성공")
    return success


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Pexels 스톡 영상 다운로드")
    p.add_argument("--ep",       required=True,      help="에피소드 디렉토리 경로")
    p.add_argument("--duration", type=float, default=5.0, help="클립당 길이 초 (기본 5)")
    args = p.parse_args()
    generate_stock_clips(args.ep, args.duration)

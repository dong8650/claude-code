"""
get_episode_info.py
===================
오늘 날짜 에피소드 정보를 JSON으로 stdout 출력. n8n SSH 노드 전용.

사용법:
  python3 /root/auto_pipeline/get_episode_info.py
"""
import json
import sys
from datetime import datetime
from pathlib import Path

BASE_DIR = Path("/root/auto_pipeline")
DEFAULT_TAGS = ["매일의설계", "직장인", "쇼츠", "자기계발", "동기부여"]


def main():
    today = datetime.now().strftime("%Y%m%d")
    episodes_dir = BASE_DIR / "episodes"

    dirs = sorted([
        d for d in episodes_dir.iterdir()
        if d.is_dir() and d.name.startswith(today)
    ])

    if not dirs:
        print(json.dumps({"error": "no_episode_dir", "today": today}, ensure_ascii=False))
        return

    ep_dir = dirs[-1]
    mp4 = ep_dir / "output_final.mp4"

    if not mp4.exists():
        print(json.dumps({"error": "no_mp4", "ep_dir": str(ep_dir)}, ensure_ascii=False))
        return

    script_path = ep_dir / "script.json"
    if not script_path.exists():
        print(json.dumps({"error": "no_script", "ep_dir": str(ep_dir)}, ensure_ascii=False))
        return

    script = json.loads(script_path.read_text(encoding="utf-8"))
    t1 = script.get("t1", "")
    t2 = script.get("t2", "")
    title = f"{t1} {t2}".strip() or script.get("title_ko", "")

    print(json.dumps({
        "ep_dir":     str(ep_dir),
        "ep_name":    ep_dir.name,
        "video_path": str(mp4),
        "title":      title,
        "script_ko":  script.get("script_ko", ""),
        "closing_ko": script.get("closing_ko", ""),
        "tags_ko":    script.get("tags_ko") or DEFAULT_TAGS,
        "style":      script.get("style", "docsul"),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()

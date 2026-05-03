"""
get_episode_info_v2.py
======================
n8n SSH 노드 전용 — 오늘 생성된 v2 에피소드 메타데이터 JSON 출력
"""
import json
import sys
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).parent
EPISODES_DIR = BASE_DIR / "episodes_v2"


def main():
    today = datetime.now().strftime("%Y%m%d")
    if not EPISODES_DIR.exists():
        print(json.dumps({"error": "no_episodes_dir"}, ensure_ascii=False))
        sys.exit(0)

    today_eps = sorted(EPISODES_DIR.glob(f"{today}_*"), reverse=True)
    if not today_eps:
        print(json.dumps({"error": "no_episode_today", "date": today}, ensure_ascii=False))
        sys.exit(0)

    ep_dir = today_eps[0]
    script_file = ep_dir / "script_v2.json"
    video_file = ep_dir / "output_final.mp4"

    if not video_file.exists():
        print(json.dumps({"error": "video_not_ready", "ep_dir": str(ep_dir)}, ensure_ascii=False))
        sys.exit(0)

    if not script_file.exists():
        print(json.dumps({"error": "script_not_found", "ep_dir": str(ep_dir)}, ensure_ascii=False))
        sys.exit(0)

    script = json.loads(script_file.read_text(encoding="utf-8"))
    drama = script.get("drama", "")
    content_type = script.get("content_type", "")
    hook = script.get("hook", "")
    save_trigger = script.get("save_trigger", "")
    loop_trigger = script.get("loop_trigger", "")
    tags_ko = script.get("tags_ko", ["매일의설계", "드라마", "쇼츠"])
    total_duration = script.get("total_duration", 10)

    title = f"{drama} | {hook}"
    tags_line = " ".join(f"#{t}" for t in tags_ko)
    desc_lines = [
        f"🎬 {drama} — {content_type}",
        "",
        save_trigger,
        "",
        "─────────────────────────",
        "📌 매일의설계 | 어제보다 나은 오늘을 설계하자",
        "구독 · 좋아요 · 알림 설정으로 매일 인사이트를 받아보세요.",
        "",
        tags_line,
    ]

    print(json.dumps({
        "ep_dir": str(ep_dir),
        "title": title,
        "drama": drama,
        "content_type": content_type,
        "hook": hook,
        "description_full": "\n".join(desc_lines),
        "tags_ko": tags_ko,
        "video_path": str(video_file),
        "total_duration": total_duration,
        "privacy": "private",
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()

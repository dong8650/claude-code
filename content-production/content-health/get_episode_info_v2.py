"""
get_episode_info_v2.py
======================
n8n SSH 노드 전용 — 오늘 생성된 에피소드 메타데이터 JSON 출력

출력 형식:
  --mode both  → {"mode": "both", "longform": {...}, "shortform": {...}}
  --mode shorts → {"mode": "shorts", "shortform": {...}}
"""
import json
import sys
from datetime import datetime
from pathlib import Path

EPISODES_DIR = Path("/root/content/runtime/health/episodes")


def _build_info(ep_dir: Path, video_type: str) -> dict:
    script_file = ep_dir / ("script_longform.json" if video_type == "longform" else "script_v2.json")
    video_file  = ep_dir / "output_final.mp4"

    script       = json.loads(script_file.read_text(encoding="utf-8"))
    title_topic  = script.get("title", "")
    hook         = script.get("hook", "")
    save_trigger = script.get("save_trigger", "")
    tags_ko      = script.get("tags_ko", ["건강상식연구소", "건강상식"])

    title = f"[상세] {title_topic} | {hook}" if video_type == "longform" else f"{title_topic} | {hook}"

    tags_line = " ".join(f"#{t}" for t in tags_ko)
    desc_lines = [
        f"🔬 {title_topic}",
        "",
        save_trigger,
        "",
        "─────────────────────────",
        "📌 건강 상식 연구소 | 매일 하나씩, 건강 상식을 쌓자",
        "구독 · 좋아요 · 알림 설정으로 매일 건강 정보를 받아보세요.",
        "",
        tags_line,
    ]

    return {
        "ep_dir":           str(ep_dir),
        "title":            title,
        "description_full": "\n".join(desc_lines),
        "tags_ko":          tags_ko,
        "video_path":       str(video_file),
        "total_duration":   script.get("total_duration", 0),
        "video_type":       video_type,
        "privacy":          "private",
    }


def main():
    today = datetime.now().strftime("%Y%m%d")

    if not EPISODES_DIR.exists():
        print(json.dumps({"error": "no_episodes_dir"}, ensure_ascii=False))
        sys.exit(0)

    today_eps = sorted(EPISODES_DIR.glob(f"{today}_*"))
    if not today_eps:
        print(json.dumps({"error": "no_episode_today", "date": today}, ensure_ascii=False))
        sys.exit(0)

    longform_ep  = None
    shortform_ep = None

    for ep_dir in today_eps:
        lf_script = ep_dir / "script_longform.json"
        sf_script = ep_dir / "script_v2.json"
        video     = ep_dir / "output_final.mp4"

        if lf_script.exists() and video.exists() and not longform_ep:
            longform_ep = ep_dir
        elif sf_script.exists() and video.exists() and not lf_script.exists() and not shortform_ep:
            shortform_ep = ep_dir

    # both 모드
    if longform_ep and shortform_ep:
        print(json.dumps({
            "mode":      "both",
            "longform":  _build_info(longform_ep, "longform"),
            "shortform": _build_info(shortform_ep, "shortform"),
        }, ensure_ascii=False))
        return

    # shorts 모드 (하위 호환 — 기존 n8n 워크플로우도 동작)
    ep_dir = shortform_ep or (today_eps[-1] if today_eps else None)
    if not ep_dir:
        print(json.dumps({"error": "no_episode_today", "date": today}, ensure_ascii=False))
        return

    script_file = ep_dir / "script_v2.json"
    video_file  = ep_dir / "output_final.mp4"

    if not video_file.exists():
        print(json.dumps({"error": "video_not_ready", "ep_dir": str(ep_dir)}, ensure_ascii=False))
        return
    if not script_file.exists():
        print(json.dumps({"error": "script_not_found", "ep_dir": str(ep_dir)}, ensure_ascii=False))
        return

    info = _build_info(ep_dir, "shortform")
    # 기존 워크플로우 하위 호환: 플랫 필드도 함께 출력
    print(json.dumps({
        "mode":             "shorts",
        "shortform":        info,
        # flat (기존 n8n Code 노드 호환)
        "ep_dir":           info["ep_dir"],
        "title":            info["title"],
        "description_full": info["description_full"],
        "tags_ko":          info["tags_ko"],
        "video_path":       info["video_path"],
        "total_duration":   info["total_duration"],
        "privacy":          info["privacy"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()

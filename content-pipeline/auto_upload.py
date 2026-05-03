"""
auto_upload.py
===============
영상 완성 후 n8n 웹훅 호출 → YouTube 자동 업로드.

서버 (/root/auto_pipeline) 에서 실행:
  python3 auto_upload.py --ep episodes/20260501_004
  python3 auto_upload.py --ep episodes/20260501_004 --style docsul --privacy public
"""
import argparse
import json
from pathlib import Path

import requests

from config import N8N_WEBHOOK_URL

DEFAULT_TAGS = ["매일의설계", "직장인", "쇼츠", "자기계발", "동기부여"]


def build_title(script: dict) -> str:
    t1 = script.get("t1", "")
    t2 = script.get("t2", "")
    if t1 or t2:
        return f"{t1} {t2}".strip()
    return script.get("title_ko", "")


def upload(ep_dir: str, style: str = "docsul", privacy: str = "private"):
    ep_path = Path(ep_dir)
    video_path = ep_path / "output_final.mp4"
    script_path = ep_path / "script.json"

    if not video_path.exists():
        print(f"❌ output_final.mp4 없음: {ep_path}")
        return False

    with open(script_path, encoding="utf-8") as f:
        script = json.load(f)

    title = build_title(script)
    tags_ko = script.get("tags_ko", []) or DEFAULT_TAGS
    closing_ko = script.get("closing_ko", "")
    script_ko = script.get("script_ko", "")

    size_mb = video_path.stat().st_size / 1024 / 1024
    print(f"📤 업로드 요청: {title}")
    print(f"   파일: {video_path} ({size_mb:.1f}MB)")
    print(f"   공개: {privacy}  |  스타일: {style}")

    payload = {
        "ep_dir": ep_path.name,
        "title": title,
        "script_ko": script_ko,
        "closing_ko": closing_ko,
        "tags_ko": tags_ko,
        "style": style,
        "privacy": privacy,
    }

    try:
        r = requests.post(N8N_WEBHOOK_URL, json=payload, timeout=120)
    except requests.exceptions.ConnectionError:
        print(f"❌ n8n 연결 실패. 웹훅 URL 확인: {N8N_WEBHOOK_URL}")
        return False

    if r.status_code == 200:
        try:
            data = r.json()
            video_id = data.get("videoId", "")
            print(f"✅ 완료: https://youtube.com/watch?v={video_id}")
            print(f"   ⚠️  YouTube Studio에서 최상단 댓글 고정 필요")
        except Exception:
            print(f"✅ 완료 (응답: {r.text[:100]})")
        return True
    else:
        print(f"❌ 실패: HTTP {r.status_code}")
        print(f"   {r.text[:300]}")
        return False


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="n8n 웹훅으로 YouTube 자동 업로드")
    p.add_argument("--ep",      required=True,  help="에피소드 디렉토리 (episodes/YYYYMMDD_NNN)")
    p.add_argument("--style",   default="docsul", choices=["docsul", "janas", "list", "seulki", "infographic"])
    p.add_argument("--privacy", default="private", choices=["private", "unlisted", "public"])
    args = p.parse_args()
    upload(args.ep, args.style, args.privacy)

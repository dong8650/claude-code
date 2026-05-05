"""
infographic_upload.py
=====================
인포그래픽 영상을 n8n 웹훅 → YouTube 자동 업로드.

사용법:
  python3 infographic_upload.py --data data_burnout.json
  python3 infographic_upload.py --data data_burnout.json --privacy private
"""
import argparse
import json
import sys
from pathlib import Path

import requests

sys.path.insert(0, "/root/content/runtime/mindset")
from config import N8N_WEBHOOK_URL

DEFAULT_TAGS = ["매일의설계", "직장인", "쇼츠", "인포그래픽", "데이터", "현실", "직장생활"]


def upload(data_file: str, privacy: str = "private") -> bool:
    base_dir  = Path(__file__).parent
    data_path = base_dir / data_file

    if not data_path.exists():
        print(f"❌ 데이터 파일 없음: {data_path}")
        return False

    with open(data_path, encoding="utf-8") as f:
        data = json.load(f)

    stem       = Path(data_file).stem          # data_burnout
    video_path = str(base_dir / f"{stem}.mp4") # /root/auto_pipeline/data_burnout.mp4

    if not Path(video_path).exists():
        print(f"❌ 영상 없음: {video_path}  (먼저 generate_infographic.py --video 실행)")
        return False

    title    = data.get("title", "")
    subtitle = data.get("subtitle", "")
    tags     = data.get("tags_ko", DEFAULT_TAGS)

    size_mb = Path(video_path).stat().st_size / 1024 / 1024
    print(f"📤 인포그래픽 업로드 요청: {title}")
    print(f"   파일: {video_path} ({size_mb:.1f}MB)")
    print(f"   공개: {privacy}")

    payload = {
        "video_path": video_path,
        "title":      title,
        "script_ko":  subtitle,
        "closing_ko": "",
        "tags_ko":    tags,
        "style":      "infographic",
        "privacy":    privacy,
        "ep_dir":     "",
    }

    try:
        r = requests.post(N8N_WEBHOOK_URL, json=payload, timeout=120)
    except requests.exceptions.ConnectionError:
        print(f"❌ n8n 연결 실패. 웹훅 URL: {N8N_WEBHOOK_URL}")
        return False

    if r.status_code == 200:
        try:
            resp    = r.json()
            vid_id  = resp.get("videoId", "")
            print(f"✅ 완료: https://youtube.com/watch?v={vid_id}")
        except Exception:
            print(f"✅ 완료 (응답: {r.text[:100]})")
        return True

    print(f"❌ 실패: HTTP {r.status_code}")
    print(f"   {r.text[:300]}")
    return False


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="인포그래픽 영상 YouTube 자동 업로드")
    p.add_argument("--data",    required=True,
                   help="data_*.json 파일명 (예: data_burnout.json)")
    p.add_argument("--privacy", default="private",
                   choices=["private", "unlisted", "public"])
    args = p.parse_args()
    sys.exit(0 if upload(args.data, args.privacy) else 1)

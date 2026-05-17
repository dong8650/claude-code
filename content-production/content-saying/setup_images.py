"""
setup_images.py
===============
공개 도메인 철학자 사진 다운로드 (Wikimedia Commons)
서버 최초 1회 실행: python3 setup_images.py
"""
import os
import sys
import time
import requests
from pathlib import Path

sys.path.insert(0, "/root/content/runtime/saying")
from config import RUNTIME_DIR

IMAGE_DIR = Path(RUNTIME_DIR) / "images"

PHILOSOPHER_IMAGES = {
    "nietzsche": [
        {
            "filename": "nietzsche_01.jpg",
            "url": "https://upload.wikimedia.org/wikipedia/commons/1/1b/Nietzsche187a.jpg",
            "desc": "Friedrich Nietzsche, 1869"
        },
        {
            "filename": "nietzsche_02.jpg",
            "url": "https://upload.wikimedia.org/wikipedia/commons/1/1d/Friedrich_Nietzsche-1872.jpg",
            "desc": "Friedrich Nietzsche, 1872"
        },
        {
            "filename": "nietzsche_03.jpg",
            "url": "https://upload.wikimedia.org/wikipedia/commons/0/07/Nietzsche1882.jpg",
            "desc": "Friedrich Nietzsche, 1882"
        },
    ],
    "schopenhauer": [
        {
            "filename": "schopenhauer_01.jpg",
            "url": "https://upload.wikimedia.org/wikipedia/commons/7/7d/Schopenhauer.jpg",
            "desc": "Arthur Schopenhauer portrait"
        },
        {
            "filename": "schopenhauer_02.jpg",
            "url": "https://upload.wikimedia.org/wikipedia/commons/b/b6/Arthur_Schopenhauer_by_J_Schäfer%2C_1859b.jpg",
            "desc": "Arthur Schopenhauer, 1859"
        },
        {
            "filename": "schopenhauer_03.jpg",
            "url": "https://upload.wikimedia.org/wikipedia/commons/9/9d/Schopenhauer_1852.jpg",
            "desc": "Arthur Schopenhauer, 1852"
        },
    ],
}

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; content-saying-bot/1.0)"}


def download_images():
    for philosopher, images in PHILOSOPHER_IMAGES.items():
        folder = IMAGE_DIR / philosopher
        folder.mkdir(parents=True, exist_ok=True)
        print(f"\n📥 {philosopher} 이미지 다운로드...")
        for img in images:
            out = folder / img["filename"]
            if out.exists():
                print(f"  ✅ {img['filename']} (기존)")
                continue
            for attempt in range(3):
                try:
                    time.sleep(2)   # Wikimedia 속도 제한 방지
                    resp = requests.get(img["url"], headers=HEADERS, timeout=20)
                    resp.raise_for_status()
                    out.write_bytes(resp.content)
                    print(f"  ✅ {img['filename']} ({len(resp.content)//1024}KB) — {img['desc']}")
                    break
                except Exception as e:
                    if attempt < 2:
                        print(f"  ⚠️ 재시도 {attempt+1}/3: {e}")
                        time.sleep(5 * (attempt + 1))
                    else:
                        print(f"  ❌ {img['filename']} 실패: {e}")

    print("\n🎉 이미지 설정 완료")
    print(f"📂 저장 위치: {IMAGE_DIR}")


if __name__ == "__main__":
    download_images()

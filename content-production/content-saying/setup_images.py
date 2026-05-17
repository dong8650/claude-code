"""
setup_images.py
===============
공개 도메인 철학자 사진 다운로드 (Wikimedia Commons API)
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

# Wikimedia Commons 파일명 (API로 URL을 동적으로 조회)
PHILOSOPHER_IMAGES = {
    "nietzsche": [
        {"filename": "nietzsche_01.jpg", "wiki": "Nietzsche187a.jpg",            "desc": "Nietzsche, 1869"},
        {"filename": "nietzsche_02.jpg", "wiki": "Friedrich_Nietzsche-1872.jpg", "desc": "Nietzsche, 1872"},
        {"filename": "nietzsche_03.jpg", "wiki": "Nietzsche1882.jpg",            "desc": "Nietzsche, 1882"},
    ],
    "schopenhauer": [
        {"filename": "schopenhauer_01.jpg", "wiki": "Schopenhauer.jpg",                              "desc": "Schopenhauer portrait"},
        {"filename": "schopenhauer_02.jpg", "wiki": "Arthur_Schopenhauer_by_J_Schäfer,_1859b.jpg",  "desc": "Schopenhauer, 1859"},
        {"filename": "schopenhauer_03.jpg", "wiki": "Schopenhauer_1852.jpg",                         "desc": "Schopenhauer, 1852"},
    ],
}

API_URL = "https://commons.wikimedia.org/w/api.php"
HEADERS = {
    "User-Agent": "content-saying-bot/1.0 (educational; https://github.com/dong8650/claude-code)"
}


def _get_image_url(wiki_filename: str, width: int = 1200) -> str:
    """Wikimedia Commons API로 공식 썸네일 URL 조회."""
    params = {
        "action":    "query",
        "titles":    f"File:{wiki_filename}",
        "prop":      "imageinfo",
        "iiprop":    "url",
        "iiurlwidth": width,
        "format":    "json",
    }
    resp = requests.get(API_URL, params=params, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    pages = resp.json().get("query", {}).get("pages", {})
    for page in pages.values():
        info = page.get("imageinfo", [{}])[0]
        return info.get("thumburl") or info.get("url")
    return None


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
            try:
                time.sleep(1)
                url = _get_image_url(img["wiki"])
                if not url:
                    print(f"  ❌ {img['filename']} — URL 조회 실패")
                    continue
                time.sleep(1)
                resp = requests.get(url, headers=HEADERS, timeout=20)
                resp.raise_for_status()
                out.write_bytes(resp.content)
                print(f"  ✅ {img['filename']} ({len(resp.content)//1024}KB) — {img['desc']}")
            except Exception as e:
                print(f"  ❌ {img['filename']} 실패: {e}")

    print("\n🎉 이미지 설정 완료")
    print(f"📂 저장 위치: {IMAGE_DIR}")


if __name__ == "__main__":
    download_images()

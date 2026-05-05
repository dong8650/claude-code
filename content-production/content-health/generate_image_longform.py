"""
generate_image_longform.py
==========================
롱폼 전용 이미지 생성 — Pexels 무료 사진 API (DALL-E 비용 없음)
씬별 pexels_query 키워드로 portrait 사진 검색 후 다운로드
config.py에 PEXELS_API_KEY 필요
"""
import shutil
import sys
import time
from pathlib import Path

RUNTIME_DIR = Path("/root/content/runtime/health")


def _fetch_photo_url(query: str, api_key: str) -> str:
    import requests
    headers = {"Authorization": api_key}
    for q in [query, "health wellness"]:
        params = {"query": q, "orientation": "portrait", "size": "large", "per_page": 10}
        resp = requests.get(
            "https://api.pexels.com/v1/search",
            headers=headers, params=params, timeout=10
        )
        resp.raise_for_status()
        photos = resp.json().get("photos", [])
        if photos:
            return photos[0]["src"]["large"]
    raise RuntimeError(f"Pexels 검색 결과 없음: {query}")


def generate_all_images_pexels(scenes: list, ep_dir: Path) -> list:
    """씬별 Pexels 사진 다운로드. 기존 파일은 스킵."""
    import requests
    sys.path.insert(0, str(RUNTIME_DIR))
    from config import PEXELS_API_KEY

    image_paths = []
    fallback_img = None

    for i, scene in enumerate(scenes):
        out_path = ep_dir / f"bg{i+1}.jpg"

        if out_path.exists():
            image_paths.append(str(out_path))
            if fallback_img is None:
                fallback_img = out_path
            continue

        query = scene.get("pexels_query", "health wellness")
        print(f"    🖼️  bg{i+1}.jpg [pexels: {query}]")

        try:
            url = _fetch_photo_url(query, PEXELS_API_KEY)
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()
            out_path.write_bytes(resp.content)
            if fallback_img is None:
                fallback_img = out_path
        except Exception as e:
            print(f"    ⚠️  bg{i+1}.jpg 실패 ({e})")
            if fallback_img and fallback_img.exists():
                shutil.copy(str(fallback_img), str(out_path))
                print(f"    ↩️  bg1.jpg로 대체")
            else:
                raise

        image_paths.append(str(out_path))
        time.sleep(0.3)  # Pexels API: 200 req/hour

    return image_paths

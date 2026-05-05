"""
generate_image_v2.py
====================
건강 상식 DALL-E 3 이미지 생성 (귀여운 장기/캐릭터 스타일)
9:16 세로형, 1024x1792
"""
import base64
import sys
import time
from pathlib import Path


def generate_health_image(image_prompt: str, out_path: Path, retry: int = 3) -> Path:
    from openai import OpenAI
    sys.path.insert(0, "/root/content/runtime/health")
    from config import OPENAI_API_KEY

    client = OpenAI(api_key=OPENAI_API_KEY)

    safe_prompt = (
        f"{image_prompt}, "
        "vertical 9:16 composition, cute cartoon style, kawaii health infographic, "
        "adorable organ characters, no real people faces, educational illustration, "
        "bright cheerful colors, clean background, 4K quality"
    )

    for attempt in range(retry):
        try:
            resp = client.images.generate(
                model="dall-e-3",
                prompt=safe_prompt,
                size="1024x1792",
                quality="standard",
                n=1,
                response_format="b64_json",
            )
            img_data = base64.b64decode(resp.data[0].b64_json)
            out_path.write_bytes(img_data)
            return out_path
        except Exception as e:
            if attempt < retry - 1:
                time.sleep(2 ** attempt)
            else:
                raise e


def generate_all_images(scenes: list, ep_dir: Path) -> list:
    image_paths = []
    for i, scene in enumerate(scenes):
        prompt = scene.get("image_prompt", "cute cartoon health illustration, educational, kawaii organ characters")
        out_path = ep_dir / f"bg{i+1}.jpg"
        if out_path.exists():
            image_paths.append(str(out_path))
            continue
        generate_health_image(prompt, out_path)
        image_paths.append(str(out_path))
        time.sleep(1)
    return image_paths

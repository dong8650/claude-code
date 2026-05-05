"""
generate_image_v2.py
====================
건강 상식 DALL-E 3 이미지 생성 — 씬별 3가지 스타일 자동 선택
  photo   : 스포츠/실사 사진 (Hook, 잘못된상식, 루프트리거)
  digital : sci-fi 개념 시각화 (과학설명1/2)
  object  : 오브젝트 전용, 사람 없음 (감정충격, 저장유도) — content_policy 방지
9:16 세로형, 1024x1792
content_policy_violation 발생 시 object safe_fallback으로 자동 전환.
"""
import base64
import sys
import time
from pathlib import Path

_SUFFIX = {
    "photo": (
        ", TALL VERTICAL 9:16 PORTRAIT composition, single main subject centered vertically, "
        "NO horizontal layout, NO text in image, NO real human faces, "
        "cinematic sports photography, photorealistic, dramatic golden hour or studio lighting, "
        "person shown from behind or as silhouette only if present"
    ),
    "digital": (
        ", TALL VERTICAL 9:16 PORTRAIT composition, single main subject centered vertically, "
        "NO horizontal layout, NO text in image, NO real human faces, "
        "cinematic sci-fi digital art, glowing neon energy particles, dark background, "
        "dramatic volumetric lighting, hyperrealistic 3D render style"
    ),
    "object": (
        ", TALL VERTICAL 9:16 PORTRAIT composition, single main subject centered vertically, "
        "NO horizontal layout, NO text in image, absolutely NO people, "
        "cinematic still life photography, dramatic spotlight, dark moody atmosphere"
    ),
}

_SAFE_FALLBACK = (
    "cinematic still life of health and fitness objects on a dark surface, "
    "dramatic spotlight, no people, no text, 9:16 vertical portrait"
)


def generate_health_image(
    image_prompt: str, out_path: Path, image_style: str = "photo", retry: int = 3
) -> Path:
    from openai import OpenAI
    sys.path.insert(0, "/root/content/runtime/health")
    from config import OPENAI_API_KEY

    client = OpenAI(api_key=OPENAI_API_KEY)

    suffix = _SUFFIX.get(image_style, _SUFFIX["photo"])
    prompts_to_try = [
        image_prompt + suffix,
        _SAFE_FALLBACK + _SUFFIX["object"],
    ]

    for prompt in prompts_to_try:
        for attempt in range(retry):
            try:
                resp = client.images.generate(
                    model="dall-e-3",
                    prompt=prompt,
                    size="1024x1792",
                    quality="standard",
                    n=1,
                    response_format="b64_json",
                )
                img_data = base64.b64decode(resp.data[0].b64_json)
                out_path.write_bytes(img_data)
                return out_path
            except Exception as e:
                if "content_policy_violation" in str(e):
                    break  # 즉시 safe_fallback으로 전환
                if attempt < retry - 1:
                    time.sleep(2 ** attempt)
                else:
                    raise e

    raise RuntimeError(f"이미지 생성 실패 (content_policy + fallback 모두 차단): {out_path.name}")


def generate_all_images(scenes: list, ep_dir: Path) -> list:
    image_paths = []
    for i, scene in enumerate(scenes):
        prompt = scene.get(
            "image_prompt",
            "cinematic health concept, dramatic lighting, 9:16 vertical portrait",
        )
        style = scene.get("image_style", "photo")
        out_path = ep_dir / f"bg{i+1}.jpg"
        if out_path.exists():
            image_paths.append(str(out_path))
            continue
        print(f"    🎨 bg{i+1}.jpg [{style}]")
        generate_health_image(prompt, out_path, image_style=style)
        image_paths.append(str(out_path))
        time.sleep(1)
    return image_paths

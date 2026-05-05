"""
generate_image_v2.py
====================
건강 상식 연구소 — 숏폼 이미지 생성
fal.ai Flux.1 Dev (DALL-E 3 대비 69% 비용 절감: $0.08 → $0.025/장)
씬별 3가지 스타일: photo / digital / object
9:16 세로형 portrait_16_9 (576×1024 → ffmpeg에서 1080×1920 upscale)
content_policy 차단 시 object safe_fallback 자동 전환
"""
import os
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


def _call_flux(prompt: str, api_key: str) -> bytes:
    """fal.ai Flux.1 Dev 호출 → 이미지 bytes 반환."""
    import fal_client
    import requests

    os.environ["FAL_KEY"] = api_key

    result = fal_client.subscribe(
        "fal-ai/flux/dev",
        arguments={
            "prompt":                prompt,
            "image_size":            "portrait_16_9",
            "num_inference_steps":   28,
            "guidance_scale":        3.5,
            "num_images":            1,
            "enable_safety_checker": True,
            "output_format":         "jpeg",
        },
    )
    image_url = result["images"][0]["url"]
    resp = requests.get(image_url, timeout=30)
    resp.raise_for_status()
    return resp.content


def generate_health_image(
    image_prompt: str, out_path: Path, image_style: str = "photo", retry: int = 3
) -> Path:
    sys.path.insert(0, "/root/content/runtime/health")
    from config import FAL_API_KEY

    suffix = _SUFFIX.get(image_style, _SUFFIX["photo"])
    prompts_to_try = [
        image_prompt + suffix,
        _SAFE_FALLBACK + _SUFFIX["object"],
    ]

    for prompt in prompts_to_try:
        for attempt in range(retry):
            try:
                img_bytes = _call_flux(prompt, FAL_API_KEY)
                out_path.write_bytes(img_bytes)
                return out_path
            except Exception as e:
                err = str(e).lower()
                if any(k in err for k in ("safety", "content", "blocked", "policy")):
                    break  # 즉시 safe_fallback으로 전환
                if attempt < retry - 1:
                    time.sleep(2 ** attempt)
                else:
                    raise

    raise RuntimeError(f"이미지 생성 실패 (safety + fallback 모두 차단): {out_path.name}")


def generate_all_images(scenes: list, ep_dir: Path) -> list:
    image_paths = []
    for i, scene in enumerate(scenes):
        prompt = scene.get(
            "image_prompt",
            "cinematic health concept, dramatic lighting, 9:16 vertical portrait",
        )
        style   = scene.get("image_style", "photo")
        out_path = ep_dir / f"bg{i+1}.jpg"
        if out_path.exists():
            image_paths.append(str(out_path))
            continue
        print(f"    🎨 bg{i+1}.jpg [{style}]")
        generate_health_image(prompt, out_path, image_style=style)
        image_paths.append(str(out_path))
        time.sleep(0.5)
    return image_paths

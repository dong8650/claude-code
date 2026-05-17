"""
generate_image.py
=================
매일의 설계 (일/돈 설계편) — 숏폼 이미지 생성
fal.ai Flux.1 Dev ($0.025/장, 9:16 portrait_16_9)
editorial intent 필드를 Flux 프롬프트에 직접 주입
"""
import os
import sys
import time
import requests

sys.path.insert(0, "/root/content/runtime/mindset")
from config import FAL_API_KEY

BANNED_WORDS = [
    "self-harm", "suicide", "manipulation", "abuse", "violence",
    "death", "corpse", "blood", "weapon", "kill", "dead body",
    "자해", "파괴", "학대", "폭력", "죽음", "시체", "살인"
]

FALLBACK_PROMPTS = [
    "close-up shot of old pocket watch on wooden desk, warm side lighting, melancholy, rule of thirds, cinematic, ultra detailed",
    "wide shot of foggy empty road at dawn, soft diffused light, solitude, rule of thirds, cinematic, ultra detailed",
    "close-up shot of cracked dry earth, harsh sunlight, desolation, rule of thirds, cinematic, ultra detailed",
    "low angle shot of single streetlamp in rain, cold blue light, loneliness, rule of thirds, cinematic, ultra detailed",
    "wide shot of abandoned stone corridor, dim end light, silence, rule of thirds, cinematic, ultra detailed",
]

_PHOTO_SUFFIX = (
    ", TALL VERTICAL 9:16 PORTRAIT composition, single main subject centered vertically, "
    "NO horizontal layout, NO text in image, NO real human faces, "
    "cinematic photography, photorealistic, dramatic professional lighting, "
    "person shown from behind or as silhouette only if present"
)

_OBJECT_SUFFIX = (
    ", TALL VERTICAL 9:16 PORTRAIT composition, single main subject centered vertically, "
    "NO horizontal layout, NO text in image, absolutely NO people, "
    "cinematic still life photography, dramatic spotlight, dark moody atmosphere"
)

EDITORIAL_SUFFIX = (
    " Editorially selected everyday scene, not a generic stock illustration. "
    "Show the concrete situation and the reason this scene matters. "
    "Korean 30s or 40s work-life context, lived-in details, no text in image."
)


def sanitize_prompt(prompt: str) -> str:
    p = prompt
    for word in BANNED_WORDS:
        p = p.replace(word, "")
    p += " Safe content. No violence. No people. No faces. Cinematic art."
    return p.strip()


def _editorial_context(script_or_scenes) -> dict:
    if isinstance(script_or_scenes, dict):
        return {
            "scenes": script_or_scenes.get("scenes", []),
            "real_scene": script_or_scenes.get("real_scene", ""),
            "visual_intention": script_or_scenes.get("visual_intention", ""),
            "one_argument": script_or_scenes.get("one_argument", ""),
        }
    return {"scenes": script_or_scenes, "real_scene": "", "visual_intention": "", "one_argument": ""}


def _with_editorial_intent(raw_prompt: str, context: dict, scene_index: int) -> str:
    real_scene = context.get("real_scene", "")
    visual_intention = context.get("visual_intention", "")
    one_argument = context.get("one_argument", "")

    additions = [raw_prompt]
    if scene_index in (0, 1, 2) and real_scene:
        additions.append(f"Concrete real scene to reflect: {real_scene}.")
    if visual_intention:
        additions.append(f"Visual intention: {visual_intention}.")
    if one_argument:
        additions.append(f"Single editorial argument: {one_argument}.")
    additions.append(EDITORIAL_SUFFIX)
    return " ".join(additions)


def _call_flux(prompt: str) -> bytes:
    """fal.ai Flux.1 Dev 호출 → 이미지 bytes 반환."""
    import fal_client

    os.environ["FAL_KEY"] = FAL_API_KEY

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


def generate_images(script_or_scenes, output_dir: str):
    os.makedirs(output_dir, exist_ok=True)
    context = _editorial_context(script_or_scenes)
    scenes = context["scenes"]

    for i, scene in enumerate(scenes):
        raw_prompt = scene.get("image_prompt", "dark cinematic moody atmosphere, no humans, vertical portrait")
        raw_prompt = _with_editorial_intent(raw_prompt, context, i)
        prompt = sanitize_prompt(raw_prompt) + _PHOTO_SUFFIX
        out_path = os.path.join(output_dir, f"bg{i+1}.jpg")

        print(f"  🎨 Flux 이미지 생성 중 ({i+1}/{len(scenes)})...")
        success = False

        for attempt in range(3):
            try:
                img_data = _call_flux(prompt)
                with open(out_path, "wb") as f:
                    f.write(img_data)
                print(f"  ✅ bg{i+1}.jpg 완료")
                success = True
                break
            except Exception as e:
                err = str(e).lower()
                if any(k in err for k in ("safety", "content", "blocked", "policy")):
                    print(f"  ⚠️ content policy — object fallback 전환")
                    break
                if attempt < 2:
                    time.sleep(2 ** attempt)
                else:
                    print(f"  ⚠️ 실패: {e}")

        if not success:
            fallback = FALLBACK_PROMPTS[i % len(FALLBACK_PROMPTS)] + _OBJECT_SUFFIX
            print(f"  🔄 object fallback 재시도...")
            try:
                img_data = _call_flux(fallback)
                with open(out_path, "wb") as f:
                    f.write(img_data)
                print(f"  ✅ bg{i+1}.jpg fallback 완료")
            except Exception as e2:
                print(f"  ❌ fallback도 실패: {e2}")

        time.sleep(0.5)

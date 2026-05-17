import os
import sys
import base64
import requests
from openai import OpenAI
sys.path.insert(0, "/root/content/runtime/mindset")
from config import OPENAI_API_KEY

client = OpenAI(api_key=OPENAI_API_KEY)
IMAGE_MODEL = os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-1")
IMAGE_SIZE = os.getenv("OPENAI_IMAGE_SIZE", "1024x1536")
IMAGE_QUALITY = os.getenv("OPENAI_IMAGE_QUALITY", "medium")

BANNED_WORDS = [
    "self-harm", "suicide", "manipulation", "abuse", "violence",
    "death", "corpse", "blood", "weapon", "kill", "dead body",
    "자해", "파괴", "학대", "폭력", "죽음", "시체", "살인"
]

FALLBACK_PROMPTS = [
    "close-up shot of old pocket watch on wooden desk, warm side lighting, melancholy, rule of thirds, cinematic, ultra detailed, 9:16",
    "wide shot of foggy empty road at dawn, soft diffused light, solitude, rule of thirds, cinematic, ultra detailed, 9:16",
    "close-up shot of cracked dry earth, harsh sunlight, desolation, rule of thirds, cinematic, ultra detailed, 9:16",
    "low angle shot of single streetlamp in rain, cold blue light, loneliness, rule of thirds, cinematic, ultra detailed, 9:16",
    "wide shot of abandoned stone corridor, dim end light, silence, rule of thirds, cinematic, ultra detailed, 9:16",
]

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


def _generate_image_bytes(prompt: str) -> bytes:
    response = client.images.generate(
        model=IMAGE_MODEL,
        prompt=prompt,
        size=IMAGE_SIZE,
        quality=IMAGE_QUALITY,
        n=1,
    )
    item = response.data[0]
    if getattr(item, "b64_json", None):
        return base64.b64decode(item.b64_json)
    if getattr(item, "url", None):
        return requests.get(item.url, timeout=30).content
    raise RuntimeError("이미지 응답에 b64_json/url 없음")


def generate_images(script_or_scenes, output_dir: str):
    os.makedirs(output_dir, exist_ok=True)
    context = _editorial_context(script_or_scenes)
    scenes = context["scenes"]
    for i, scene in enumerate(scenes):
        raw_prompt = scene.get("image_prompt", "dark cinematic moody atmosphere, no humans, vertical portrait")
        raw_prompt = _with_editorial_intent(raw_prompt, context, i)
        prompt = sanitize_prompt(raw_prompt)
        print(f"  🎨 DALL-E 이미지 생성 중 ({i+1}/{len(scenes)})...")
        success = False

        try:
            img_data = _generate_image_bytes(prompt)
            with open(os.path.join(output_dir, f"bg{i+1}.jpg"), "wb") as f:
                f.write(img_data)
            print(f"  ✅ bg{i+1}.jpg 완료")
            success = True
        except Exception as e:
            print(f"  ⚠️ 1차 실패: {e}")

        if not success:
            print(f"  🔄 fallback 재시도...")
            try:
                fallback = FALLBACK_PROMPTS[i % len(FALLBACK_PROMPTS)]
                img_data = _generate_image_bytes(fallback)
                with open(os.path.join(output_dir, f"bg{i+1}.jpg"), "wb") as f:
                    f.write(img_data)
                print(f"  ✅ bg{i+1}.jpg fallback 완료")
            except Exception as e2:
                print(f"  ❌ fallback도 실패: {e2}")

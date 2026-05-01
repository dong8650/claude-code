import os
import requests
from openai import OpenAI
from config import OPENAI_API_KEY

client = OpenAI(api_key=OPENAI_API_KEY)

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

def sanitize_prompt(prompt: str) -> str:
    p = prompt
    for word in BANNED_WORDS:
        p = p.replace(word, "")
    p += " Safe content. No violence. No people. No faces. Cinematic art."
    return p.strip()

def generate_images(scenes: list, output_dir: str):
    os.makedirs(output_dir, exist_ok=True)
    for i, scene in enumerate(scenes):
        raw_prompt = scene.get("image_prompt", "dark cinematic moody atmosphere, no humans, vertical portrait")
        prompt = sanitize_prompt(raw_prompt)
        print(f"  🎨 DALL-E 이미지 생성 중 ({i+1}/{len(scenes)})...")
        success = False

        try:
            response = client.images.generate(
                model="dall-e-3", prompt=prompt,
                size="1024x1792", quality="hd", n=1,
            )
            img_data = requests.get(response.data[0].url, timeout=30).content
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
                response = client.images.generate(
                    model="dall-e-3", prompt=fallback,
                    size="1024x1792", quality="hd", n=1,
                )
                img_data = requests.get(response.data[0].url, timeout=30).content
                with open(os.path.join(output_dir, f"bg{i+1}.jpg"), "wb") as f:
                    f.write(img_data)
                print(f"  ✅ bg{i+1}.jpg fallback 완료")
            except Exception as e2:
                print(f"  ❌ fallback도 실패: {e2}")

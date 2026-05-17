"""
generate_image.py
=================
fal.ai Flux.1 Dev — 철학자 분위기 이미지 3장 생성
에피소드별 철학자 + 테마 기반 프롬프트
"""
import os
import sys
import time
import requests
from pathlib import Path

sys.path.insert(0, "/root/content/runtime/saying")
from config import FAL_API_KEY

_PHILOSOPHER_ATMOS = {
    "nietzsche": (
        "Friedrich Nietzsche's 1880s study, dark dramatic atmosphere, "
        "German philosopher's workspace, quill pen and manuscripts, "
        "dramatic candlelight, moody deep shadows"
    ),
    "schopenhauer": (
        "Arthur Schopenhauer's 19th century European study, candlelit darkness, "
        "melancholy philosopher's workspace, old leather-bound books stacked high, "
        "contemplative heavy atmosphere, dim gaslight"
    ),
}

_THEME_VISUAL = {
    "창조":    "chaos swirling into cosmos, dark energy transforming into starlight, abstract",
    "극복":    "storm-battered lone mountain path at dusk, dramatic clouds, no people",
    "고독":    "empty candlelit library at midnight, single flickering flame, ancient shelves",
    "지혜":    "ancient manuscript open on worn desk, shaft of light on old text, no people",
    "행복":    "simple objects on worn wooden desk, gentle morning light through old window",
    "삶":      "pendulum clock in dim study, shadows swinging across stone floor",
    "욕망":    "half-empty glass on dark table, long shadow, dramatic side light",
    "탐욕":    "spilled coins on dark surface, single spotlight, no hands",
    "죽음":    "hourglass on ancient stone, last grains of sand falling, candle nearly spent",
    "시간":    "pocket watch open on old desk, clock hands in dramatic light",
    "자유":    "open cage on a windowsill, dark room, light pouring through open window",
    "운명":    "winding road disappearing into dark stormy horizon, no people",
    "두려움":  "long dark corridor with single light at far end, stone walls",
    "편견":    "two mirrors facing each other in dark room, infinite reflections",
    "현재":    "single candle flame close-up, darkness all around, warm glow",
    "희생":    "worn coat on an empty chair, candlelight, dark study",
    "의지":    "lone bare tree on cliff edge against stormy sky, dramatic silhouette",
    "창조":    "ink spilling from overturned bottle across blank paper, candlelight",
    "예술":    "old violin resting on stack of musical scores, soft dramatic light",
    "생명":    "single green sprout emerging from cracked dark stone, dramatic light",
    "도덕":    "scales of justice in shadow on old desk, candlelight casting long shadow",
    "해석":    "broken mirror fragments reflecting same scene differently, dark dramatic",
    "집단심리": "empty theatre seats in darkness, single spotlight on empty stage",
    "진실":    "cracked clock face on dark wall, dramatic shadow, no people",
    "관계":    "two empty chairs facing each other across candlelit table",
    "기대":    "door slightly ajar with bright light beyond, dark hallway",
    "질투":    "two candles — one burning bright, one melting in its own wax",
    "무게":    "heavy stone on old wooden floorboard, dramatic low light",
    "성장":    "old tree root breaking through stone pavement, dramatic light",
    "사랑":    "dried flowers pressed in open old book, soft candlelight",
    "무지":    "closed book gathering dust on shelf, single shaft of light",
    "자기기만": "distorted reflection in dark water, candlelight trembling",
    "희망":    "single window in dark stone wall, light breaking through storm outside",
    "탐험":    "old map unrolled on dark table, compass and candle",
}

_DEFAULT_VISUAL = "ancient philosophical study, candles and shadows, dramatic atmosphere"

_SUFFIX = (
    ", TALL VERTICAL 9:16 PORTRAIT composition, "
    "absolutely NO faces, NO people, NO text in image, "
    "cinematic dark dramatic photography, deep shadows, film grain, "
    "high contrast chiaroscuro lighting"
)

_FALLBACK = (
    "old philosopher's desk, stack of ancient books, single candle flame, "
    "dramatic shadow, dark moody atmosphere, no people"
    + _SUFFIX
)


def _call_flux(prompt: str) -> bytes:
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
    url = result["images"][0]["url"]
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    return resp.content


def generate_images(script: dict, ep_dir: str):
    ep          = Path(ep_dir)
    ep.mkdir(parents=True, exist_ok=True)

    philosopher = script.get("philosopher_en", "nietzsche").lower()
    theme       = script.get("theme", "")
    atmos       = _PHILOSOPHER_ATMOS.get(philosopher, _PHILOSOPHER_ATMOS["nietzsche"])
    theme_vis   = _THEME_VISUAL.get(theme, _DEFAULT_VISUAL)

    prompts = [
        f"{atmos}, wide establishing shot, no people{_SUFFIX}",
        f"{theme_vis}{_SUFFIX}",
        f"{atmos}, intimate close-up still life, personal objects{_SUFFIX}",
    ]

    for i, prompt in enumerate(prompts):
        out = ep / f"bg{i+1}.jpg"
        if out.exists():
            print(f"  ✅ bg{i+1}.jpg (기존)")
            continue
        print(f"  🎨 Flux 이미지 생성 중 ({i+1}/3)...")
        success = False
        for attempt in range(3):
            try:
                data = _call_flux(prompt)
                out.write_bytes(data)
                print(f"  ✅ bg{i+1}.jpg 완료")
                success = True
                break
            except Exception as e:
                err = str(e).lower()
                if any(k in err for k in ("safety", "content", "blocked", "policy")):
                    print(f"  ⚠️ content policy — fallback 전환")
                    break
                if attempt < 2:
                    time.sleep(2 ** attempt)
                else:
                    print(f"  ⚠️ 실패: {e}")

        if not success:
            try:
                data = _call_flux(_FALLBACK)
                out.write_bytes(data)
                print(f"  ✅ bg{i+1}.jpg fallback 완료")
            except Exception as e2:
                print(f"  ❌ bg{i+1}.jpg 최종 실패: {e2}")

        time.sleep(0.5)

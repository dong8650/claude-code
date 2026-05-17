"""
generate_image.py
=================
fal.ai Flux.1 Dev — 에피소드별 분위기 이미지 3장 생성
Dark Academia 스타일 가중치: cinematic/woodcut/ink 우선 (합산 53%)

TODO: _SUBJECT_ATMOS 를 채널 주제에 맞게 수정
"""
import os
import random
import sys
import time
import requests
from pathlib import Path

# TODO: 채널명으로 변경
CHANNEL_ID = "org"

sys.path.insert(0, f"/root/content/runtime/{CHANNEL_ID}")
from config import FAL_API_KEY

# ── 주제별 배경 분위기 ─────────────────────────────────────
# TODO: 채널 주제에 맞게 수정
# key: topics JSON의 image_set 값과 일치시킬 것
_SUBJECT_ATMOS = {
    "default": (
        "dramatic dark atmospheric study, candlelit workspace, "
        "ancient books and manuscripts, deep shadows, moody heavy atmosphere"
    ),
    # 예시: 철학자 채널
    # "nietzsche": "Friedrich Nietzsche's 1880s study, dark dramatic atmosphere, ...",
    # 예시: 역사 채널
    # "lincoln": "19th century American presidential study, candlelit, ...",
}

# ── 테마별 비주얼 매핑 ─────────────────────────────────────
# TODO: 채널 주제 풀의 theme 값에 맞게 추가
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
    "도전":    "lone figure on cliff edge facing vast dark storm, back to camera, dramatic scale",
    "변화":    "burning book transforming into rising ash and sparks, dark background, dramatic light",
    "인식":    "cracked gilded mirror revealing raw stone wall behind, single candle reflection",
    "선택":    "ancient forked road at dusk, one path lit, one in shadow, no people",
    "자존감":  "single weathered chair facing dark window, rain outside, warm inner glow",
}

_DEFAULT_VISUAL = "ancient philosophical study, candles and shadows, dramatic atmosphere"
_PORTRAIT = ", TALL VERTICAL 9:16 PORTRAIT composition"

# ── Dark Academia 이미지 스타일 (8종) ──────────────────────
_STYLE_SUFFIXES = [
    # 1. 다크 시네마틱 (weight: 3)
    (", absolutely NO faces, NO people, NO text in image,"
     " cinematic dark dramatic photography, deep shadows, film grain,"
     " high contrast chiaroscuro lighting"),
    # 2. 렘브란트 유화 (weight: 2)
    (", NO faces, NO people,"
     " dramatic Rembrandt-style oil painting, impasto brushwork,"
     " rich dark earth tones, warm candlelight, museum-quality fine art"),
    # 3. 독일 표현주의 목판화 (weight: 3)
    (", NO faces, NO people,"
     " German expressionist woodcut print, bold stark black lines,"
     " deep crimson and black limited palette, vintage 1920s graphic art"),
    # 4. 다크 애니메이션 배경 (weight: 1)
    (", no characters visible,"
     " dark atmospheric anime environment art, no people,"
     " highly detailed background, Studio Ghibli mood, moody dramatic lighting"),
    # 5. 잉크 일러스트 (weight: 3)
    (", no people,"
     " detailed editorial ink illustration on aged parchment,"
     " dense crosshatching, dramatic chiaroscuro, black ink art style"),
    # 6. 실루엣 인물 (weight: 2)
    (", lone dark human silhouette against dramatic stormy sky,"
     " absolutely NO face details, strong backlighting,"
     " cinematic emotional composition"),
    # 7. 3D 추상 렌더 (weight: 1)
    (", no people,"
     " abstract 3D CGI render, volumetric fog and dramatic light rays,"
     " dark atmosphere, award-winning visual effects style"),
    # 8. 수채화 일러스트 (weight: 2)
    (", no people,"
     " moody atmospheric watercolor illustration,"
     " loose expressive brushwork, deep indigo and burnt sienna tones,"
     " melancholic emotional"),
]

# Dark Academia 핵심 3종(cinematic/woodcut/ink) weight 3, 나머지 1~2
_STYLE_WEIGHTS = [3, 2, 3, 1, 3, 2, 1, 2]

def _pick_style() -> str:
    return random.choices(_STYLE_SUFFIXES, weights=_STYLE_WEIGHTS, k=1)[0] + _PORTRAIT


_FALLBACK_BASE = (
    "old study desk, stack of ancient books, single candle flame, "
    "dramatic shadow, dark moody atmosphere, no people"
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

    image_set = script.get("image_set", "default").lower()
    theme     = script.get("theme", "")
    atmos     = _SUBJECT_ATMOS.get(image_set, _SUBJECT_ATMOS["default"])
    theme_vis = _THEME_VISUAL.get(theme, _DEFAULT_VISUAL)

    # 에피소드 단위로 스타일 1회 선택 → 3장 동일 스타일 (시각적 통일감)
    style = _pick_style()
    print(f"  🎨 이미지 스타일: {style[:50]}...")

    prompts = [
        f"{atmos}, wide establishing shot{style}",
        f"{theme_vis}{style}",
        f"{atmos}, intimate close-up still life, personal objects{style}",
    ]
    fallback = _FALLBACK_BASE + style

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
                data = _call_flux(fallback)
                out.write_bytes(data)
                print(f"  ✅ bg{i+1}.jpg fallback 완료")
            except Exception as e2:
                print(f"  ❌ bg{i+1}.jpg 최종 실패: {e2}")

        time.sleep(0.5)

"""
run_custom_v2.py
================
사전 정의된 스크립트로 S급 쇼츠 영상 즉시 생성
사용법: python3 run_custom_v2.py
"""
import asyncio
import json
import sys
import time
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, "/root/auto_pipeline")

SCRIPT = {
    "title": "달리기 후 뇌 변화",
    "content_type": "건강상식",
    "hook": "달리기 20분 후 뇌에서 일어나는 일",
    "scenes": [
        {
            "duration": 3,
            "caption": "달리기 20분 후\n뇌에서 일어나는 일",
            "narration": "달리기 20분 후, 뇌에서 일어나는 일입니다",
            "image_prompt": "cute cartoon brain character running joyfully with legs, endorphin sparkles floating around, bright colorful Korean health infographic style, 9:16 vertical portrait"
        },
        {
            "duration": 5,
            "caption": "기분이 좋아지는 게\n기분 탓이 아님\n과학적 이유가 있음 🧠",
            "narration": "기분이 좋아지는 게 기분 탓이 아닙니다. 과학적 이유가 있어요",
            "image_prompt": "cute cartoon brain character with magnifying glass, question marks and science beakers, cheerful pastel colors, 9:16 vertical portrait, health science illustration"
        },
        {
            "duration": 6,
            "caption": "도파민 + 세로토닌 동시 분비\n→ 항우울제와 동일한 효과\n→ 지속 시간 최대 2~3시간",
            "narration": "도파민과 세로토닌이 동시에 분비되면서, 항우울제와 동일한 효과가 나타납니다. 지속 시간은 최대 2~3시간",
            "image_prompt": "cute cartoon dopamine and serotonin molecule characters high-fiving, happy brain in background, colorful chemistry bubbles, 9:16 vertical portrait, kawaii health science style"
        },
        {
            "duration": 5,
            "caption": "운동 후 행복한 게\n의지력이 아니라\n화학반응임 😱",
            "narration": "운동 후 행복한 게, 의지력이 아니라 화학반응입니다",
            "image_prompt": "cute cartoon brain character with shocked surprised expression, chemical formula bubbles floating, dramatic colorful health infographic, 9:16 vertical portrait"
        },
        {
            "duration": 3,
            "caption": "저장해두고 운동 하기 싫을 때\n꺼내봐 💾",
            "narration": "저장해두고 운동하기 싫을 때 꺼내봐요",
            "image_prompt": "cute cartoon running shoe with bookmark ribbon, save icon, motivational bright colors, cheerful health illustration, 9:16 vertical portrait"
        },
        {
            "duration": 3,
            "caption": "처음부터 보면 복선 있음 👀",
            "narration": "",
            "image_prompt": "cute cartoon brain character pointing backward with loop arrow, playful winking expression, bright colorful, 9:16 vertical portrait"
        }
    ],
    "total_duration": 25,
    "save_trigger": "저장해두고 운동 하기 싫을 때 꺼내봐 💾",
    "loop_trigger": "처음부터 보면 복선 있음 👀",
    "tags_ko": ["건강상식연구소", "달리기", "뇌과학", "운동효과", "쇼츠"]
}


async def _tts_async(text: str, voice: str, out_path: str):
    import edge_tts
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(out_path)


def generate_tts_simple(scenes: list, out_path: Path):
    narrations = [s["narration"] for s in scenes if s.get("narration", "").strip()]
    if not narrations:
        print("  ⚠️ 나레이션 없음 — TTS 건너뜀")
        return False
    full_text = " ".join(narrations)
    print(f"  🎙️ TTS 생성: {full_text[:50]}...")
    asyncio.run(_tts_async(full_text, "ko-KR-SunHiNeural", str(out_path)))
    print(f"  ✅ TTS 완료: {out_path}")
    return True


def main():
    today = datetime.now().strftime("%Y%m%d")
    episodes_dir = BASE_DIR / "episodes_v2"
    episodes_dir.mkdir(exist_ok=True)
    existing = sorted(episodes_dir.glob(f"{today}_*"))
    seq = len(existing) + 1
    ep_dir = episodes_dir / f"{today}_{seq:03d}"
    ep_dir.mkdir(exist_ok=True)
    print(f"\n📁 에피소드 디렉토리: {ep_dir}")

    # 1. 스크립트 저장
    script_file = ep_dir / "script_v2.json"
    script_file.write_text(json.dumps(SCRIPT, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ 스크립트 저장 완료")

    # 2. DALL-E 이미지 생성
    print(f"\n🎨 DALL-E 이미지 생성 중... ({len(SCRIPT['scenes'])}장, 세로형 9:16)")
    from generate_image_v2 import generate_all_images
    generate_all_images(SCRIPT["scenes"], ep_dir)
    print(f"✅ 이미지 생성 완료")

    # 3. TTS
    print(f"\n🎙️ TTS 생성 중...")
    voice_file = ep_dir / "voice_ko.mp3"
    generate_tts_simple(SCRIPT["scenes"], voice_file)

    # 4. 영상 합성
    print(f"\n🎬 영상 합성 중...")
    from make_video_v2 import make_video
    bgm_path = "/root/auto_pipeline/bgm/bgm_dramatic_ambient.mp3"
    output = make_video(ep_dir, SCRIPT, bgm_path if Path(bgm_path).exists() else None)
    print(f"\n✅ 완성: {output}")


if __name__ == "__main__":
    start = time.time()
    main()
    print(f"⏱️ 총 소요: {time.time()-start:.1f}초")

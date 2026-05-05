"""
run_custom_v2.py
================
사전 정의된 스크립트로 S급 쇼츠 영상 즉시 생성
사용법: python3 run_custom_v2.py
"""
import json
import sys
import time
from pathlib import Path
from datetime import datetime

BASE_DIR    = Path(__file__).parent
RUNTIME_DIR = Path("/root/content/runtime/health")
sys.path.insert(0, str(BASE_DIR))

# S급 7씬 구조 — image_style 3종 적용 버전
SCRIPT = {
    "title": "달리기 후 뇌 변화",
    "content_type": "건강상식",
    "hook": "매일 달리기 했던 당신, 뇌에서 일어난 일 알고 있었나",
    "hook_type": "identity_attack",
    "scenes": [
        {
            "duration": 3,
            "caption": "매일 달리기 했던 당신\n뇌에서 일어난 일 알고 있었나",
            "narration": "매일 달리기 했던 당신, 뇌에서 무슨 일이 일어나는지 알고 있었나",
            "image_style": "photo",
            "image_prompt": "lone runner sprinting on empty road at golden hour sunrise, shot from behind, dynamic motion, warm orange light, cinematic depth of field, 9:16 vertical portrait"
        },
        {
            "duration": 5,
            "caption": "도파민 + 세로토닌 동시 분비\n→ 항우울제와 동일한 효과\n→ 지속 시간 최대 2~3시간 🧠",
            "narration": "도파민, 세로토닌 동시 분비. 항우울제와 동일한 효과, 2~3시간 지속",
            "image_style": "digital",
            "image_prompt": "cinematic sci-fi visualization of dopamine and serotonin neural pathways in brain, glowing blue and gold neon particles flowing through dark neural network, brain anatomy, 9:16 vertical portrait"
        },
        {
            "duration": 6,
            "caption": "BDNF(뇌유래신경영양인자) 분비\n→ 뇌세포 새로 생성\n→ 기억력·집중력 즉시 향상 💡",
            "narration": "BDNF 분비로 뇌세포가 새로 생성됩니다. 기억력, 집중력 즉시 향상",
            "image_style": "digital",
            "image_prompt": "cinematic sci-fi digital art of BDNF neurotrophic factor activating new brain cell growth, glowing green neon neurons branching and multiplying, dark dramatic background, volumetric light, 9:16 vertical portrait"
        },
        {
            "duration": 5,
            "caption": "근데 대부분이\n'운동 후에 머리 아프다'\n그냥 쉬어버림 ⚠️",
            "narration": "근데 대부분은 운동 후 머리 아프다며 그냥 쉬어버림",
            "image_style": "photo",
            "image_prompt": "cinematic photo of running shoes abandoned on the floor next to a couch, dim indoor lighting, lazy afternoon atmosphere, no people, 9:16 vertical portrait"
        },
        {
            "duration": 3,
            "caption": "매일 쉬기만 했던 당신\n뇌가 굶고 있었음 😱",
            "narration": "매일 쉬기만 했던 당신, 뇌가 굶고 있었음",
            "image_style": "object",
            "image_prompt": "cinematic still life of gym bag left closed and unused by the front door, running shoes beside it, dark moody hallway, dramatic side lighting, no people, 9:16 vertical portrait"
        },
        {
            "duration": 2,
            "caption": "공감됐으면 좋아요 누르고\n저장해둬 💾👍",
            "narration": "공감됐으면 좋아요 누르고 저장해둬",
            "image_style": "object",
            "image_prompt": "cinematic close-up of worn running shoes being tied on a starting line, golden morning light, motivational atmosphere, no people, no text, 9:16 vertical portrait"
        },
        {
            "duration": 1,
            "caption": "첫 장면 달리는 이유\n다시 보면 힌트 있음 👀",
            "narration": "첫 장면 다시 봐",
            "image_style": "photo",
            "image_prompt": "cinematic runner looking back over shoulder mid-run on a trail, motion blur, golden backlight, mysterious atmosphere, silhouette, no text, 9:16 vertical portrait"
        }
    ],
    "total_duration": 25,
    "save_trigger": "공감됐으면 좋아요 누르고 저장해둬 💾👍",
    "loop_trigger": "첫 장면 달리는 이유 다시 보면 힌트 있음 👀",
    "tags_ko": ["건강상식연구소", "달리기", "뇌과학", "운동효과", "쇼츠"]
}


def main():
    today = datetime.now().strftime("%Y%m%d")
    episodes_dir = RUNTIME_DIR / "episodes"
    episodes_dir.mkdir(parents=True, exist_ok=True)
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

    # 3+4. 영상 합성 (TTS + Ken Burns + BGM)
    print(f"\n🎬 영상 합성 중 (TTS + Ken Burns + BGM)...")
    from make_video_v2 import make_video
    bgm_path = str(RUNTIME_DIR / "bgm/bgm_dramatic_ambient.mp3")
    output = make_video(ep_dir, SCRIPT, bgm_path if Path(bgm_path).exists() else None, generate_tts=True)
    print(f"\n✅ 완성: {output}")


if __name__ == "__main__":
    start = time.time()
    main()
    print(f"⏱️ 총 소요: {time.time()-start:.1f}초")

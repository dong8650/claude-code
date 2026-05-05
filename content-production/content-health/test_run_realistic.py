"""
test_run_realistic.py
=====================
[테스트] 실사/포토리얼리스틱 이미지 스타일 — 달리기 후 뇌 변화

run_custom_v2.py 와 동일한 스크립트/파이프라인.
차이점: DALL-E 프롬프트를 카툰→시네마틱 실사 스타일로 변경.
기존 make_video_v2.py 코드 변경 없음.

실행: python3 test_run_realistic.py
출력: /root/content/runtime/health/episodes/test_realistic_YYYYMMDD_001/output_final.mp4
"""
import json
import sys
import time
from pathlib import Path
from datetime import datetime

BASE_DIR    = Path(__file__).parent
RUNTIME_DIR = Path("/root/content/runtime/health")
sys.path.insert(0, str(BASE_DIR))

# ── 실제 런닝하는 사람 이미지 프롬프트 ───────────────────────────────────
SCRIPT = {
    "title": "달리기 후 뇌 변화",
    "content_type": "건강상식",
    "hook": "달리기 20분 후 뇌에서 일어나는 일",
    "scenes": [
        {
            "duration": 3,
            "caption": "달리기 20분 후\n뇌에서 일어나는 일",
            "narration": "달리기 20분 후 뇌에서 일어나는 일",
            "image_prompt": (
                "professional sports photography, lone runner sprinting on an empty road at golden hour sunrise, "
                "shot from behind, dynamic motion, warm orange light, cinematic depth of field, "
                "no text, 9:16 vertical portrait"
            ),
        },
        {
            "duration": 5,
            "caption": "도파민 + 세로토닌 동시 분비\n→ 항우울제와 동일한 효과\n→ 지속 시간 최대 2~3시간 🧠",
            "narration": "도파민, 세로토닌 동시 분비. 항우울제와 동일한 효과, 2~3시간 지속",
            "image_prompt": (
                "professional sports photography, runner mid-stride with arms raised in joy and triumph, "
                "euphoric energy, bright sunlight, park trail, motion blur on background, "
                "shot from low angle, no text, 9:16 vertical portrait"
            ),
        },
        {
            "duration": 6,
            "caption": "BDNF(뇌유래신경영양인자) 분비\n→ 뇌세포 새로 생성\n→ 기억력·집중력 즉시 향상 💡",
            "narration": "BDNF 분비로 뇌세포가 새로 생성됩니다. 기억력, 집중력 즉시 향상",
            "image_prompt": (
                "cinematic close-up of a runner's focused expression and determined eyes, "
                "sweat on skin, intense concentration, dramatic side lighting, "
                "shallow depth of field, blurred green trail background, no text, 9:16 vertical portrait"
            ),
        },
        {
            "duration": 5,
            "caption": "근데 대부분이\n'운동 후에 머리 아프다'\n그냥 쉬어버림 ⚠️",
            "narration": "근데 대부분은 운동 후 머리 아프다며 그냥 쉬어버림",
            "image_prompt": (
                "cinematic photo of running shoes left on the floor next to a couch, "
                "workout towel and water bottle untouched, soft warm indoor lighting, "
                "post-exercise rest atmosphere, no people, no text, 9:16 vertical portrait"
            ),
        },
        {
            "duration": 3,
            "caption": "매일 쉬기만 했던 당신\n뇌가 굶고 있었음 😱",
            "narration": "매일 쉬기만 했던 당신, 뇌가 굶고 있었음",
            "image_prompt": (
                "cinematic photo of a gym bag left closed and unused by the front door, "
                "running shoes beside it, dark moody hallway, dramatic side lighting, "
                "procrastination and inactivity concept, no people, no text, 9:16 vertical portrait"
            ),
        },
        {
            "duration": 2,
            "caption": "저장해두고 운동 하기 싫을 때\n꺼내봐 💾",
            "narration": "저장해두고 꺼내봐",
            "image_prompt": (
                "cinematic close-up of worn running shoes being tied on a starting line, "
                "golden morning light, motivational atmosphere, no text, 9:16 vertical portrait"
            ),
        },
        {
            "duration": 1,
            "caption": "처음부터 보면 복선 있음 👀",
            "narration": "",
            "image_prompt": (
                "professional sports photography, runner looking back over their shoulder mid-run on a trail, "
                "motion blur, golden backlight, mysterious atmosphere, no text, 9:16 vertical portrait"
            ),
        },
    ],
    "total_duration": 25,
    "save_trigger": "저장해두고 운동 하기 싫을 때 꺼내봐 💾",
    "loop_trigger": "처음부터 보면 복선 있음 👀",
    "tags_ko": ["건강상식연구소", "달리기", "뇌과학", "운동효과", "쇼츠"],
}


def generate_realistic_image(image_prompt: str, out_path: Path, retry: int = 3) -> Path:
    """실사/시네마틱 DALL-E 이미지 (카툰 스타일 없음).
    content_policy_violation 발생 시 오브젝트 기반 안전 프롬프트로 자동 재시도.
    """
    import base64
    from openai import OpenAI
    sys.path.insert(0, "/root/content/runtime/health")
    from config import OPENAI_API_KEY

    client = OpenAI(api_key=OPENAI_API_KEY)

    base_suffix = (
        ", TALL VERTICAL 9:16 PORTRAIT composition, single main subject centered vertically, "
        "NO horizontal layout, NO text in image, NO real human faces, "
        "photorealistic cinematic style, dramatic professional lighting"
    )

    # content_policy 차단 시 사람 없는 오브젝트 기반 대체 프롬프트
    safe_fallback = (
        f"cinematic photo of running shoes and workout gear on a wooden floor, "
        f"dramatic spotlight, motivational sports atmosphere, no people, no text, "
        f"9:16 vertical portrait"
    )

    prompts_to_try = [image_prompt + base_suffix, safe_fallback + base_suffix]

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
                print(f"    ✅ {out_path.name}")
                return out_path
            except Exception as e:
                err_str = str(e)
                if "content_policy_violation" in err_str:
                    print(f"    ⚠️  콘텐츠 필터 차단 → 안전 프롬프트로 재시도")
                    break  # 즉시 safe_fallback으로 전환
                if attempt < retry - 1:
                    time.sleep(2 ** attempt)
                else:
                    print(f"    ❌ {out_path.name}: {e}")
                    raise e


def main():
    ep_dir = RUNTIME_DIR / "episodes" / f"test_realistic_{datetime.now().strftime('%Y%m%d')}_001"
    ep_dir.mkdir(parents=True, exist_ok=True)
    print(f"\n📁 테스트 디렉토리: {ep_dir}")
    print("🎨 스타일: 실사/시네마틱 DALL-E (카툰 없음)\n")

    (ep_dir / "script_v2.json").write_text(
        json.dumps(SCRIPT, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("✅ 스크립트 저장 완료")

    # 실사 이미지 생성
    print(f"\n🖼️  DALL-E 실사 이미지 생성 중... ({len(SCRIPT['scenes'])}장)")
    for i, scene in enumerate(SCRIPT["scenes"]):
        out_path = ep_dir / f"bg{i+1}.jpg"
        if out_path.exists():
            print(f"    ⏭️  bg{i+1}.jpg 이미 존재, 스킵")
            continue
        generate_realistic_image(scene["image_prompt"], out_path)
        time.sleep(1)
    print("✅ 이미지 생성 완료\n")

    # 영상 합성 — make_video_v2.py 그대로 사용 (변경 없음)
    print("🎬 영상 합성 중 (TTS + Ken Burns + BGM)...")
    from make_video_v2 import make_video
    bgm_path = str(RUNTIME_DIR / "bgm/bgm_dramatic_ambient.mp3")
    output = make_video(
        ep_dir, SCRIPT,
        bgm_path if Path(bgm_path).exists() else None,
        generate_tts=True,
    )
    print(f"\n✅ 완성: {output}")


if __name__ == "__main__":
    start = time.time()
    main()
    print(f"⏱️  총 소요: {time.time()-start:.1f}초")

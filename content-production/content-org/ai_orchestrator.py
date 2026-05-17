"""
ai_orchestrator.py
==================
content-org 파이프라인 오케스트레이터

실행:
  python3 ai_orchestrator.py --batch --count 1 --auto
  python3 ai_orchestrator.py --batch --count 1 --auto --subject 주제명
  setsid python3 -u ai_orchestrator.py --batch --count 1 --auto \
    > $RUNTIME/daily_gen.log 2>&1 </dev/null &

TODO: CHANNEL_ID 채널명으로 변경
"""
import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

# TODO: 채널명으로 변경
CHANNEL_ID = "org"

sys.path.insert(0, f"/root/content/runtime/{CHANNEL_ID}")
from config import RUNTIME_DIR

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("orchestrator")

EP_DIR = Path(RUNTIME_DIR) / "episodes"


def _next_ep_id() -> str:
    today    = datetime.now().strftime("%Y%m%d")
    existing = sorted(EP_DIR.glob(f"{today}_*"))
    seq      = len(existing) + 1
    return f"{today}_{seq:03d}"


def run_episode(subject: str = None) -> dict:
    ep_id  = _next_ep_id()
    ep_dir = str(EP_DIR / ep_id)
    log.info("[%s] 시작 — subject=%s", ep_id, subject or "랜덤")

    # ① 대본 생성
    log.info("[%s] 대본 생성", ep_id)
    from generate_script import generate_script
    script = generate_script(subject=subject, ep_dir=ep_dir)

    # ② 이미지 생성 (fal.ai Flux — 에피소드별 3장)
    log.info("[%s] 이미지 생성 (Flux)", ep_id)
    from generate_image import generate_images
    generate_images(script, ep_dir)

    # ③ TTS 생성
    log.info("[%s] TTS 생성", ep_id)
    from generate_tts import generate_tts
    durations = generate_tts(script, ep_dir)

    # ④ 영상 합성
    log.info("[%s] 영상 합성", ep_id)
    from make_video import make_video
    output = make_video(script, ep_dir, durations)

    result_summary = {
        "ep_id":     ep_id,
        "output":    output,
        "subject":   script.get("subject", ""),
        "title":     script.get("title", ""),
        "quote_ko":  script.get("quote_ko", ""),
        "echo_ko":   script.get("echo_ko", ""),
        "total_dur": durations["total_dur"],
    }
    log.info("[%s] 완료 → %s", ep_id, output)
    print(f"\n✅ 완성: {output}")
    print(f"   실제 길이: {durations['total_dur']:.1f}초 (음성 기준: {durations['total_dur']:.1f}초)")
    return {"ep_id": ep_id, "output": output, "script": script}


def main():
    p = argparse.ArgumentParser(description=f"content-{CHANNEL_ID} 파이프라인")
    p.add_argument("--batch",   action="store_true", help="배치 모드")
    p.add_argument("--count",   type=int, default=1, help="생성 편수")
    p.add_argument("--auto",    action="store_true", help="자동 실행")
    p.add_argument("--subject", help="특정 주제 분류 선택")
    args = p.parse_args()

    EP_DIR.mkdir(parents=True, exist_ok=True)

    if args.batch:
        for _ in range(args.count):
            try:
                result = run_episode(subject=args.subject)
                print(json.dumps(result["script"], ensure_ascii=False, indent=2))
            except Exception as e:
                log.error("에피소드 생성 실패: %s", e)
    else:
        result = run_episode(subject=args.subject)
        print(json.dumps(result["script"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

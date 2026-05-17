"""
ai_orchestrator.py
==================
content-saying 파이프라인 오케스트레이터

실행:
  # 랜덤 철학자
  python3 ai_orchestrator.py --batch --count 1 --auto

  # 니체만
  python3 ai_orchestrator.py --batch --count 1 --auto --philosopher 니체

  # 백그라운드 (n8n용)
  setsid python3 -u ai_orchestrator.py --batch --count 1 --auto \
    > $RUNTIME/daily_gen.log 2>&1 </dev/null &
"""
import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, "/root/content/runtime/saying")
from config import RUNTIME_DIR

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("orchestrator")

EP_DIR = Path(RUNTIME_DIR) / "episodes"


def _next_ep_id() -> str:
    today = datetime.now().strftime("%Y%m%d")
    existing = sorted(EP_DIR.glob(f"{today}_*"))
    seq = len(existing) + 1
    return f"{today}_{seq:03d}"


def run_episode(philosopher: str = None) -> dict:
    ep_id  = _next_ep_id()
    ep_dir = str(EP_DIR / ep_id)
    log.info("[%s] 시작 — philosopher=%s", ep_id, philosopher or "랜덤")

    # ① 대본 생성
    log.info("[%s] 대본 생성", ep_id)
    from generate_script import generate_script
    script = generate_script(philosopher=philosopher, ep_dir=ep_dir)

    # ② TTS 생성
    log.info("[%s] TTS 생성", ep_id)
    from generate_tts import generate_tts
    durations = generate_tts(script, ep_dir)

    # ③ 영상 합성
    log.info("[%s] 영상 합성", ep_id)
    from make_video import make_video
    output = make_video(script, ep_dir, durations)

    log.info("[%s] 완료 → %s", ep_id, output)
    return {"ep_id": ep_id, "output": output, "script": script}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--batch",       action="store_true")
    p.add_argument("--count",       type=int, default=1)
    p.add_argument("--auto",        action="store_true")
    p.add_argument("--philosopher", choices=["니체", "쇼펜하우어"])
    args = p.parse_args()

    EP_DIR.mkdir(parents=True, exist_ok=True)

    if args.batch:
        for i in range(args.count):
            try:
                result = run_episode(philosopher=args.philosopher)
                print(json.dumps(result["script"], ensure_ascii=False, indent=2))
            except Exception as e:
                log.error("에피소드 생성 실패: %s", e)
    else:
        result = run_episode(philosopher=args.philosopher)
        print(json.dumps(result["script"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

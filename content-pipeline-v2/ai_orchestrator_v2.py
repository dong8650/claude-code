"""
ai_orchestrator_v2.py
=====================
S급 드라마 쇼츠 파이프라인 오케스트레이터

사용법:
  python3 ai_orchestrator_v2.py --batch --count 1 --auto
  python3 ai_orchestrator_v2.py --topic glory_quote_revenge
"""
import argparse
import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("orchestrator_v2")


def get_next_ep_dir(base: Path) -> Path:
    today = datetime.now().strftime("%Y%m%d")
    episodes_dir = base / "episodes_v2"
    episodes_dir.mkdir(exist_ok=True)
    existing = sorted(episodes_dir.glob(f"{today}_*"))
    seq = len(existing) + 1
    ep_dir = episodes_dir / f"{today}_{seq:03d}"
    ep_dir.mkdir(exist_ok=True)
    return ep_dir


def run_episode(topic_id: str = None, auto: bool = False, channel: str = "health") -> dict:
    from generate_script_v2 import generate_script, load_used, save_used, pick_topic

    pool_file = BASE_DIR / "topics_health.json"
    pool = json.loads(pool_file.read_text(encoding="utf-8"))

    if topic_id:
        topic = next((t for t in pool if t["id"] == topic_id), None)
        if not topic:
            return {"error": f"topic_id not found: {topic_id}"}
    else:
        used_ids = load_used()
        topic, used_ids = pick_topic(pool, used_ids)

    ep_dir = get_next_ep_dir(BASE_DIR)
    ep_name = ep_dir.name
    logger.info(f"[{ep_name}] 시작 — {topic.get('drama', topic.get('title', ''))} / {topic['content_type']} / {topic['theme']}")

    start_time = time.time()

    # 1. 대본 생성
    logger.info(f"[{ep_name}] 대본 생성 중...")
    try:
        script = generate_script(topic)
    except Exception as e:
        logger.error(f"[{ep_name}] 대본 생성 실패: {e}")
        return {"error": str(e), "ep_dir": str(ep_dir)}

    script_file = ep_dir / "script_v2.json"
    script_file.write_text(json.dumps(script, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info(f"[{ep_name}] 대본 완성 — Hook: {script.get('hook', '')}")

    # 2. 이미지 생성
    logger.info(f"[{ep_name}] DALL-E 이미지 생성 중... ({len(script['scenes'])}장)")
    try:
        from generate_image_v2 import generate_all_images
        generate_all_images(script["scenes"], ep_dir)
    except Exception as e:
        logger.error(f"[{ep_name}] 이미지 생성 실패: {e}")
        return {"error": str(e), "ep_dir": str(ep_dir)}

    # 3+4. 영상 합성 (TTS 포함 — make_video_v2가 장면별 TTS 처리)
    logger.info(f"[{ep_name}] 영상 합성 중 (TTS + Ken Burns + BGM)...")
    try:
        from make_video_v2 import make_video
        bgm_path = "/root/auto_pipeline/bgm/bgm_dramatic_ambient.mp3"
        output = make_video(ep_dir, script, bgm_path if Path(bgm_path).exists() else None, generate_tts=True)
    except Exception as e:
        logger.error(f"[{ep_name}] 영상 합성 실패: {e}")
        return {"error": str(e), "ep_dir": str(ep_dir)}

    elapsed = time.time() - start_time

    # 사용 기록
    if not topic_id:
        used_ids.add(topic["id"])
        save_used(used_ids)

    logger.info(f"[{ep_name}] 완료 ({elapsed:.1f}s) — {output}")
    return {
        "ep_dir": str(ep_dir),
        "ep_name": ep_name,
        "drama": topic.get("drama", topic.get("title", "")),
        "content_type": topic["content_type"],
        "hook": script.get("hook", ""),
        "video_path": str(output),
        "total_duration": script.get("total_duration", 0),
        "tags_ko": script.get("tags_ko", []),
        "elapsed": elapsed,
    }



def main():
    parser = argparse.ArgumentParser(description="S급 드라마 쇼츠 생성")
    parser.add_argument("--batch", action="store_true")
    parser.add_argument("--count", type=int, default=1)
    parser.add_argument("--auto", action="store_true")
    parser.add_argument("--topic", type=str, default=None, help="특정 topic_id 지정")
    parser.add_argument("--channel", type=str, default="health", help="health | drama")
    args = parser.parse_args()

    results = []
    count = args.count if args.batch else 1

    logger.info(f"배치 시작 — {count}편")
    logger.info("=" * 55)

    for i in range(count):
        result = run_episode(topic_id=args.topic if not args.batch else None, auto=args.auto, channel=args.channel)
        results.append(result)
        if result.get("error"):
            logger.warning(f"  FAIL — {result['error']}")
        else:
            logger.info(f"  PASS {result['ep_name']} | {result['drama']} | {result['content_type']} | {result['elapsed']:.1f}s")

    success = [r for r in results if not r.get("error")]
    logger.info("=" * 55)
    logger.info(f"배치 완료 — 성공: {len(success)} / 전체: {len(results)}")

    report_file = BASE_DIR / "batch_report_v2.json"
    report_file.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info(f"리포트 저장 → {report_file}")


if __name__ == "__main__":
    main()

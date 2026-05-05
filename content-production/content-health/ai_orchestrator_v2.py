"""
ai_orchestrator_v2.py
=====================
S급 건강 상식 파이프라인 오케스트레이터

사용법:
  python3 ai_orchestrator_v2.py --batch --count 1 --auto            # 숏폼만 (기본값)
  python3 ai_orchestrator_v2.py --batch --count 1 --auto --mode both # 롱폼+숏폼
  python3 ai_orchestrator_v2.py --topic morning_water
"""
import argparse
import json
import logging
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path

BASE_DIR    = Path(__file__).parent
RUNTIME_DIR = Path("/root/content/runtime/health")
sys.path.insert(0, str(BASE_DIR))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("orchestrator_v2")


def get_next_ep_dir() -> Path:
    today = datetime.now().strftime("%Y%m%d")
    episodes_dir = RUNTIME_DIR / "episodes"
    episodes_dir.mkdir(parents=True, exist_ok=True)
    existing = sorted(episodes_dir.glob(f"{today}_*"))
    seq = len(existing) + 1
    ep_dir = episodes_dir / f"{today}_{seq:03d}"
    ep_dir.mkdir(exist_ok=True)
    return ep_dir


def _pick_shortform_images(longform_ep_dir: Path, n_longform: int, shortform_ep_dir: Path, n_shortform: int = 7):
    """롱폼 이미지에서 숏폼용 7장 선택 후 복사.
    선택 기준: 0번(hook) 고정 + 중간 균등 분포 + 마지막 2장(저장유도, 루프트리거) 고정.
    """
    if n_longform <= n_shortform:
        indices = list(range(n_longform))
    else:
        middle_count = n_shortform - 3
        step = (n_longform - 3) / (middle_count + 1)
        middle = [round(1 + step * i) for i in range(middle_count)]
        indices = sorted(set([0] + middle + [n_longform - 2, n_longform - 1]))[:n_shortform]

    copied = 0
    for sf_idx, lf_idx in enumerate(indices):
        src = longform_ep_dir / f"bg{lf_idx + 1}.jpg"
        dst = shortform_ep_dir / f"bg{sf_idx + 1}.jpg"
        if src.exists():
            shutil.copy(str(src), str(dst))
            copied += 1
    logger.info(f"  이미지 재활용: 롱폼 {n_longform}장 → 숏폼 {copied}장 복사")


def run_episode(topic_id: str = None, auto: bool = False, channel: str = "health") -> dict:
    from generate_script_v2 import generate_script, load_used, save_used, pick_topic

    pool_file = BASE_DIR / "topics_health.json"
    pool = json.loads(pool_file.read_text(encoding="utf-8"))

    if topic_id:
        topic = next((t for t in pool if t["id"] == topic_id), None)
        if not topic:
            return {"error": f"topic_id not found: {topic_id}"}
        used_ids = load_used()
    else:
        used_ids = load_used()
        topic, used_ids = pick_topic(pool, used_ids)

    ep_dir  = get_next_ep_dir()
    ep_name = ep_dir.name
    logger.info(f"[{ep_name}] 시작 — {topic.get('title', '')} / {topic['content_type']} / {topic['theme']}")

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
    logger.info(f"[{ep_name}] Flux 이미지 생성 중... ({len(script['scenes'])}장)")
    try:
        from generate_image_v2 import generate_all_images
        generate_all_images(script["scenes"], ep_dir)
    except Exception as e:
        logger.error(f"[{ep_name}] 이미지 생성 실패: {e}")
        return {"error": str(e), "ep_dir": str(ep_dir)}

    # 3+4. 영상 합성
    logger.info(f"[{ep_name}] 영상 합성 중 (TTS + Ken Burns + BGM)...")
    try:
        from make_video_v2 import make_video
        bgm_path = str(RUNTIME_DIR / "bgm/bgm_dramatic_ambient.mp3")
        output = make_video(ep_dir, script, bgm_path if Path(bgm_path).exists() else None, generate_tts=True)
    except Exception as e:
        logger.error(f"[{ep_name}] 영상 합성 실패: {e}")
        return {"error": str(e), "ep_dir": str(ep_dir)}

    elapsed = time.time() - start_time

    if not topic_id:
        used_ids.add(topic["id"])
        save_used(used_ids)

    logger.info(f"[{ep_name}] 완료 ({elapsed:.1f}s) — {output}")
    return {
        "ep_dir":         str(ep_dir),
        "ep_name":        ep_name,
        "title":          topic.get("title", ""),
        "content_type":   topic["content_type"],
        "hook":           script.get("hook", ""),
        "video_path":     str(output),
        "video_type":     "shortform",
        "total_duration": script.get("total_duration", 0),
        "tags_ko":        script.get("tags_ko", []),
        "elapsed":        elapsed,
    }


def run_episode_both(topic_id: str = None, auto: bool = False) -> dict:
    """롱폼 생성 → 숏폼 이미지 재활용 순차 실행."""
    from generate_script_v2 import generate_script, load_used, save_used, pick_topic
    from generate_script_longform import generate_longform_script
    from generate_image_v2 import generate_all_images
    from make_video_v2 import make_video

    pool_file = BASE_DIR / "topics_health.json"
    pool = json.loads(pool_file.read_text(encoding="utf-8"))

    if topic_id:
        topic = next((t for t in pool if t["id"] == topic_id), None)
        if not topic:
            return {"error": f"topic_id not found: {topic_id}"}
        used_ids = load_used()
    else:
        used_ids = load_used()
        topic, used_ids = pick_topic(pool, used_ids)

    bgm_path = str(RUNTIME_DIR / "bgm/bgm_dramatic_ambient.mp3")
    bgm      = bgm_path if Path(bgm_path).exists() else None

    logger.info(f"롱폼+숏폼 생성 시작 — {topic['title']}")
    logger.info("─" * 55)

    # ── 1단계: 롱폼 ──────────────────────────────────────────────
    lf_ep_dir  = get_next_ep_dir()
    lf_ep_name = lf_ep_dir.name
    lf_start   = time.time()

    logger.info(f"[{lf_ep_name}] 롱폼 대본 생성 중...")
    try:
        lf_script = generate_longform_script(topic)
    except Exception as e:
        logger.error(f"[{lf_ep_name}] 롱폼 대본 실패: {e}")
        return {"longform": {"error": str(e)}, "shortform": {"error": "longform failed"}}

    (lf_ep_dir / "script_longform.json").write_text(
        json.dumps(lf_script, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    logger.info(f"[{lf_ep_name}] 롱폼 대본 완성 — {len(lf_script['scenes'])}씬")

    logger.info(f"[{lf_ep_name}] Pexels 이미지 다운로드 중... ({len(lf_script['scenes'])}장, 무료)")
    try:
        from generate_image_longform import generate_all_images_pexels
        generate_all_images_pexels(lf_script["scenes"], lf_ep_dir)
    except Exception as e:
        logger.error(f"[{lf_ep_name}] 롱폼 이미지 실패: {e}")
        return {"longform": {"error": str(e)}, "shortform": {"error": "longform failed"}}

    logger.info(f"[{lf_ep_name}] 롱폼 영상 합성 중...")
    try:
        lf_output = make_video(lf_ep_dir, lf_script, bgm, generate_tts=True)
    except Exception as e:
        logger.error(f"[{lf_ep_name}] 롱폼 영상 합성 실패: {e}")
        return {"longform": {"error": str(e)}, "shortform": {"error": "longform failed"}}

    lf_elapsed = time.time() - lf_start
    logger.info(f"[{lf_ep_name}] 롱폼 완료 ({lf_elapsed:.1f}s)")
    logger.info("─" * 55)

    # ── 2단계: 숏폼 (이미지 재활용) ──────────────────────────────
    sf_ep_dir  = get_next_ep_dir()
    sf_ep_name = sf_ep_dir.name
    sf_start   = time.time()

    logger.info(f"[{sf_ep_name}] 숏폼 대본 생성 중...")
    try:
        sf_script = generate_script(topic)
    except Exception as e:
        logger.error(f"[{sf_ep_name}] 숏폼 대본 실패: {e}")
        return {
            "longform": {"ep_dir": str(lf_ep_dir), "ep_name": lf_ep_name, "video_path": str(lf_output), "video_type": "longform", "elapsed": lf_elapsed},
            "shortform": {"error": str(e)},
        }

    (sf_ep_dir / "script_v2.json").write_text(
        json.dumps(sf_script, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    logger.info(f"[{sf_ep_name}] 숏폼 대본 완성 — Hook: {sf_script.get('hook', '')}")

    # 숏폼은 Flux 이미지 독립 생성 (롱폼은 Pexels, 숏폼은 Flux)
    logger.info(f"[{sf_ep_name}] Flux 이미지 생성 중... ({len(sf_script['scenes'])}장)")
    try:
        from generate_image_v2 import generate_all_images
        generate_all_images(sf_script["scenes"], sf_ep_dir)
    except Exception as e:
        logger.error(f"[{sf_ep_name}] 숏폼 이미지 실패: {e}")
        return {
            "longform": {"ep_dir": str(lf_ep_dir), "ep_name": lf_ep_name, "video_path": str(lf_output), "video_type": "longform", "elapsed": lf_elapsed},
            "shortform": {"error": str(e)},
        }

    logger.info(f"[{sf_ep_name}] 숏폼 영상 합성 중...")
    try:
        sf_output = make_video(sf_ep_dir, sf_script, bgm, generate_tts=True)
    except Exception as e:
        logger.error(f"[{sf_ep_name}] 숏폼 영상 합성 실패: {e}")
        return {
            "longform": {"ep_dir": str(lf_ep_dir), "ep_name": lf_ep_name, "video_path": str(lf_output), "video_type": "longform", "elapsed": lf_elapsed},
            "shortform": {"error": str(e)},
        }

    sf_elapsed = time.time() - sf_start

    if not topic_id:
        used_ids.add(topic["id"])
        save_used(used_ids)

    logger.info(f"[{sf_ep_name}] 숏폼 완료 ({sf_elapsed:.1f}s)")
    logger.info("=" * 55)
    logger.info(f"롱폼+숏폼 완료 — 총 {lf_elapsed + sf_elapsed:.1f}s")

    return {
        "longform": {
            "ep_dir":         str(lf_ep_dir),
            "ep_name":        lf_ep_name,
            "title":          topic["title"],
            "hook":           lf_script.get("hook", ""),
            "video_path":     str(lf_output),
            "video_type":     "longform",
            "n_scenes":       len(lf_script["scenes"]),
            "total_duration": lf_script.get("total_duration", 0),
            "tags_ko":        lf_script.get("tags_ko", []),
            "elapsed":        lf_elapsed,
        },
        "shortform": {
            "ep_dir":         str(sf_ep_dir),
            "ep_name":        sf_ep_name,
            "title":          topic["title"],
            "hook":           sf_script.get("hook", ""),
            "video_path":     str(sf_output),
            "video_type":     "shortform",
            "total_duration": sf_script.get("total_duration", 0),
            "tags_ko":        sf_script.get("tags_ko", []),
            "elapsed":        sf_elapsed,
        },
    }


def main():
    parser = argparse.ArgumentParser(description="S급 건강 상식 파이프라인")
    parser.add_argument("--batch",   action="store_true")
    parser.add_argument("--count",   type=int, default=1)
    parser.add_argument("--auto",    action="store_true")
    parser.add_argument("--topic",   type=str, default=None, help="특정 topic_id 지정")
    parser.add_argument("--channel", type=str, default="health")
    parser.add_argument("--mode",    type=str, default="shorts", choices=["shorts", "both"],
                        help="shorts=숏폼만(기본값) / both=롱폼+숏폼 순차 생성")
    args = parser.parse_args()

    count = args.count if args.batch else 1
    logger.info(f"배치 시작 — {count}편 / 모드: {args.mode}")
    logger.info("=" * 55)

    results = []
    for i in range(count):
        topic_id = args.topic if not args.batch else None

        if args.mode == "both":
            result = run_episode_both(topic_id=topic_id, auto=args.auto)
            lf = result.get("longform", {})
            sf = result.get("shortform", {})
            if lf.get("error"):
                logger.warning(f"  FAIL(LF) — {lf['error']}")
            else:
                logger.info(f"  PASS(LF) {lf['ep_name']} | {lf['title']} | {lf['elapsed']:.1f}s")
            if sf.get("error"):
                logger.warning(f"  FAIL(SF) — {sf['error']}")
            else:
                logger.info(f"  PASS(SF) {sf['ep_name']} | {sf['title']} | {sf['elapsed']:.1f}s")
        else:
            result = run_episode(topic_id=topic_id, auto=args.auto, channel=args.channel)
            if result.get("error"):
                logger.warning(f"  FAIL — {result['error']}")
            else:
                logger.info(f"  PASS {result['ep_name']} | {result['title']} | {result['content_type']} | {result['elapsed']:.1f}s")

        results.append(result)

    success = sum(
        1 for r in results
        if not r.get("error") and not r.get("longform", {}).get("error")
    )
    logger.info("=" * 55)
    logger.info(f"배치 완료 — 성공: {success} / 전체: {len(results)}")

    report_file = BASE_DIR / "batch_report_v2.json"
    report_file.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info(f"리포트 저장 → {report_file}")


if __name__ == "__main__":
    main()

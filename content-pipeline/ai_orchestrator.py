"""
ai_orchestrator.py
==================
콘텐츠 자동화 파이프라인 오케스트레이터 v3.1 — Seed Topic Pool 기반

Flow per episode:
  ① topics.json에서 content_type 비율에 맞게 topic_seed 선택
  ② Quality Gate 재검수 — 기존 script.json이 있으면 v3로 먼저 검사
  ③ generate_script — GPT 각색 + Claude 검수 + Quality Gate (PASS만 통과)
  ④ generate_images / generate_tts / make_video (PASS 시만 진행)

실행 방법:
  # 배치 (emotion 30% / ranking 30% / money 20% / quote 20%)
  python ai_orchestrator.py --batch --count 10

  # 배치 대본만
  python ai_orchestrator.py --batch --count 10 --script-only

  # 특정 topic 지정 단일 실행
  python ai_orchestrator.py --ep 20260501_001 --topic-id emotion_001

  # content-type만 지정 (pool에서 자동 선택)
  python ai_orchestrator.py --ep 20260501_001 --content-type ranking
"""

import argparse
import json
import logging
import os
import random
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import anthropic

from config import CLAUDE_API_KEY
from generate_script import generate_best_script
from quality_gate import recheck_v3

log = logging.getLogger("orchestrator")

BASE_DIR    = Path(os.getenv("PIPELINE_BASE", "/root/auto_pipeline"))
TOPICS_FILE = Path(os.getenv("TOPICS_FILE",   "/root/auto_pipeline/topics.json"))

# ─────────────────────────────────────────────
# 콘텐츠 타입 비율
# ─────────────────────────────────────────────
CONTENT_RATIO = {
    "emotion": 30,
    "ranking": 30,
    "money":   20,
    "quote":   20,
}

TYPE_STYLE_MAP = {
    "emotion": "docsul",
    "ranking": "list",
    "money":   "docsul",
    "quote":   "janas",
    "hybrid":  "docsul",
}


# ─────────────────────────────────────────────
# 결과 데이터클래스
# ─────────────────────────────────────────────
@dataclass
class EpisodeResult:
    ep_id:          str
    topic_id:       str
    topic:          str
    content_type:   str
    style:          str
    success:        bool
    final_status:   str        = "FAIL"
    fail_reason:    str        = ""
    scores:         dict       = field(default_factory=dict)
    view_score:     int        = 0
    output_mp4:     str | None = None
    elapsed_s:      float      = 0.0


# ─────────────────────────────────────────────
# Topic Pool 관리
# ─────────────────────────────────────────────

def _load_topics(topics_file: Path = TOPICS_FILE) -> list[dict]:
    """topics.json을 로드한다. 없으면 에러."""
    if not topics_file.exists():
        raise FileNotFoundError(f"topics.json 없음: {topics_file}")
    return json.loads(topics_file.read_text(encoding="utf-8"))


def _save_topics(topics: list[dict], topics_file: Path = TOPICS_FILE) -> None:
    """topics.json에 사용 이력을 저장한다."""
    topics_file.write_text(
        json.dumps(topics, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _select_topic(
    content_type: str,
    topics:       list[dict],
    used_ids:     set[str],
    exclude_days: int = 7,
) -> dict | None:
    """
    content_type에 맞는 topic_seed를 선택한다.

    우선순위:
    1. 현재 배치에서 미사용 + 최근 exclude_days일 미사용
    2. (없으면) 최근 exclude_days일 미사용
    3. (없으면) 배치 내 미사용 중 가장 오래된 것
    4. (없으면) 전체 중 가장 오래된 것

    같은 topic이 배치 내에서 중복 사용되지 않는다.
    """
    now      = datetime.now(tz=timezone.utc)
    pool     = [t for t in topics if t["content_type"] == content_type]

    if not pool:
        return None

    def days_since(t: dict) -> float:
        lu = t.get("last_used")
        if not lu:
            return float("inf")
        try:
            dt = datetime.fromisoformat(lu)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return (now - dt).total_seconds() / 86400
        except Exception:
            return float("inf")

    not_used_batch    = [t for t in pool if t["id"] not in used_ids]
    not_used_recent   = [t for t in not_used_batch if days_since(t) >= exclude_days]
    any_not_recent    = [t for t in pool if days_since(t) >= exclude_days]

    for candidates in [not_used_recent, any_not_recent, not_used_batch, pool]:
        if candidates:
            candidates.sort(key=lambda t: (t.get("use_count", 0), days_since(t) * -1))
            return candidates[0]

    return pool[0]


def _mark_topic_used(topic_id: str, topics: list[dict]) -> None:
    """topics 리스트에서 해당 topic의 사용 이력을 업데이트한다."""
    for t in topics:
        if t["id"] == topic_id:
            t["last_used"] = datetime.now(tz=timezone.utc).isoformat()
            t["use_count"] = t.get("use_count", 0) + 1
            break


# ─────────────────────────────────────────────
# 배치 계획
# ─────────────────────────────────────────────

def _plan_batch(count: int) -> list[str]:
    """count개 에피소드의 content_type 순서를 비율대로 결정한다."""
    types: list[str] = []
    for t, pct in CONTENT_RATIO.items():
        n = max(1, round(count * pct / 100))
        types.extend([t] * n)
    while len(types) < count:
        types.append("emotion")
    random.shuffle(types)
    return types[:count]


def _make_ep_id(seq: int) -> str:
    return f"{datetime.now().strftime('%Y%m%d')}_{seq:03d}"


# ─────────────────────────────────────────────
# 기존 script.json 재검수
# ─────────────────────────────────────────────

def _recheck_existing(ep_dir: Path, client: anthropic.Anthropic) -> dict | None:
    """기존 script.json이 있으면 v3 Quality Gate로 재검수.
    PASS면 script dict, FAIL이거나 없으면 None.
    """
    script_path = ep_dir / "script.json"
    if not script_path.exists():
        return None
    try:
        script = json.loads(script_path.read_text(encoding="utf-8"))
    except Exception as e:
        log.warning("[재검수] script.json 로드 실패: %s", e)
        return None

    scores = script.get("_meta", {}).get("scores", {})
    gate   = recheck_v3(script, scores, client, str(ep_dir))

    if gate.final_status == "PASS":
        log.info("[재검수] PASS — 기존 대본 v3 통과 (view_score=%d)", gate.view_score)
        return script

    log.warning("[재검수] FAIL — 기존 대본 탈락: %s", gate.fail_reason)
    return None


# ─────────────────────────────────────────────
# 대본 출력
# ─────────────────────────────────────────────

def _print_script(script: dict) -> None:
    meta   = script.get("_meta", {})
    scores = meta.get("scores", {})
    ep_id  = script.get("ep_id",  meta.get("ep_id",  "-"))
    ctype  = script.get("content_type", "-")
    topic  = script.get("topic", "")
    angle  = script.get("angle", meta.get("angle", ""))

    print(f"\n{'=' * 55}")
    print(f"  [{ep_id}] 생성된 대본")
    print(f"{'=' * 55}")
    print(f"  topic_id     : {script.get('topic_id', '-')}")
    print(f"  주제         : {topic}")
    print(f"  각도         : {angle}")
    print(f"  콘텐츠 타입  : {ctype}")
    print(f"  패턴         : {script.get('pattern_type', '-')}")
    print(
        f"  품질         : scroll_stop={scores.get('scroll_stop_power', '-')} "
        f"emotional={scores.get('emotional_attack', '-')} "
        f"repeat={scores.get('repeat_value', '-')} "
        f"view={script.get('view_score', meta.get('view_score', '-'))}"
    )
    print(f"  제목         : {script.get('t1', '')} / {script.get('t2', '')}")
    print("─" * 55)
    print(f"hook    : {script.get('hook', '')}")
    print("script  :")
    for line in script.get("script_ko", "").split(". "):
        if line.strip():
            print(f"          {line.strip()}.")
    print(f"closing : {script.get('closing_ko', '')}")
    print(f"{'=' * 55}\n")


# ─────────────────────────────────────────────
# 단일 에피소드 실행
# ─────────────────────────────────────────────

def run_episode(
    ep_id:        str,
    topic_seed:   dict,
    content_type: str        = "emotion",
    style:        str | None = None,
    base_dir:     Path       = BASE_DIR,
    script_only:  bool       = False,
    auto:         bool       = False,
) -> EpisodeResult:
    """
    단일 에피소드 파이프라인 실행.
    FAIL이면 영상 단계로 절대 넘기지 않는다.
    """
    ep_dir = base_dir / "episodes" / ep_id
    ep_dir.mkdir(parents=True, exist_ok=True)
    t_start = datetime.now()

    resolved_style = style or TYPE_STYLE_MAP.get(content_type, "docsul")
    topic          = topic_seed["topic"]
    topic_id       = topic_seed.get("id", "")

    log.info("=" * 55)
    log.info("[%s] 시작 — type=%s topic='%s' (id=%s)",
             ep_id, content_type, topic, topic_id)

    client_claude = anthropic.Anthropic(api_key=CLAUDE_API_KEY)

    try:
        # ① 기존 script.json v3 재검수
        script = _recheck_existing(ep_dir, client_claude)

        # ② 없거나 탈락 시 신규 생성
        if script is None:
            log.info("[%s] 신규 대본 생성 (최대 3회)", ep_id)
            script = generate_best_script(
                topic_seed=topic_seed,
                content_type=content_type,
                ep_dir=str(ep_dir),
                ep_id=ep_id,
                style=resolved_style,
            )

        if script is None:
            return EpisodeResult(
                ep_id=ep_id, topic_id=topic_id, topic=topic,
                content_type=content_type, style=resolved_style,
                success=False, final_status="FAIL",
                fail_reason="Quality Gate 3회 실패",
                elapsed_s=(datetime.now() - t_start).total_seconds(),
            )

        # FAIL 상태면 영상 단계로 절대 안 넘김
        if script.get("final_status", "PASS") != "PASS":
            return EpisodeResult(
                ep_id=ep_id, topic_id=topic_id,
                topic=script.get("topic", topic),
                content_type=content_type, style=resolved_style,
                success=False, final_status="FAIL",
                fail_reason=script.get("fail_reason", "FAIL"),
                elapsed_s=(datetime.now() - t_start).total_seconds(),
            )

        meta      = script.get("_meta", {})
        scores    = meta.get("scores", {})
        cur_type  = script.get("content_type", content_type)
        cur_view  = script.get("view_score", meta.get("view_score", 0))

        _print_script(script)

        if script_only:
            log.info("[%s] --script-only 완료", ep_id)
            return EpisodeResult(
                ep_id=ep_id, topic_id=topic_id, topic=topic,
                content_type=cur_type, style=resolved_style,
                success=True, final_status="PASS",
                scores=scores, view_score=cur_view,
                elapsed_s=(datetime.now() - t_start).total_seconds(),
            )

        # ③ 사용자 확인
        if not auto:
            answer = input("▶ 이 대본으로 영상을 제작할까요? [y/N]: ").strip().lower()
            if answer != "y":
                return EpisodeResult(
                    ep_id=ep_id, topic_id=topic_id, topic=topic,
                    content_type=cur_type, style=resolved_style,
                    success=False, final_status="FAIL", fail_reason="사용자 취소",
                    elapsed_s=(datetime.now() - t_start).total_seconds(),
                )

        # ④ 이미지 생성
        log.info("[%s] 이미지 생성", ep_id)
        from generate_image import generate_images
        raw_scenes = script.get("scenes", [])
        scenes = [s if isinstance(s, dict) else {"image_prompt": s} for s in raw_scenes]
        generate_images(scenes, str(ep_dir))

        # ⑤ TTS + 자막
        log.info("[%s] TTS + 자막", ep_id)
        from generate_tts import generate_tts
        generate_tts(script, str(ep_dir / "voice_ko.mp3"), style=resolved_style)

        # ⑥ 영상 합성
        log.info("[%s] 영상 합성", ep_id)
        from make_video import make_video
        make_video(str(ep_dir), script, style=resolved_style)

        output_mp4 = ep_dir / "output_final.mp4"
        elapsed    = (datetime.now() - t_start).total_seconds()
        log.info("[%s] 완료 (%.1fs) — %s", ep_id, elapsed, output_mp4)

        return EpisodeResult(
            ep_id=ep_id, topic_id=topic_id, topic=topic,
            content_type=cur_type, style=resolved_style,
            success=True, final_status="PASS",
            scores=scores, view_score=cur_view,
            output_mp4=str(output_mp4), elapsed_s=elapsed,
        )

    except Exception as exc:
        elapsed = (datetime.now() - t_start).total_seconds()
        log.error("[%s] 예외 (%.1fs): %s", ep_id, elapsed, exc, exc_info=True)
        return EpisodeResult(
            ep_id=ep_id, topic_id=topic_id, topic=topic,
            content_type=content_type, style=resolved_style,
            success=False, final_status="FAIL", fail_reason=str(exc),
            elapsed_s=elapsed,
        )


# ─────────────────────────────────────────────
# 배치 실행
# ─────────────────────────────────────────────

def run_batch(
    count:        int  = 10,
    base_dir:     Path = BASE_DIR,
    topics_file:  Path = TOPICS_FILE,
    script_only:  bool = False,
    start_seq:    int  = 1,
    exclude_days: int  = 7,
) -> list[EpisodeResult]:
    """
    count개 에피소드를 CONTENT_RATIO 비율대로 자동 생성한다.
    topics.json에서 topic_seed를 선택하고, 사용 이력을 업데이트한다.
    """
    topics    = _load_topics(topics_file)
    type_plan = _plan_batch(count)
    used_ids: set[str] = set()
    results:  list[EpisodeResult] = []

    log.info("배치 시작 — %d편 | 타입 계획: %s", count,
             {t: type_plan.count(t) for t in set(type_plan)})

    for seq, content_type in enumerate(type_plan, start=start_seq):
        ep_id      = _make_ep_id(seq)
        topic_seed = _select_topic(content_type, topics, used_ids, exclude_days)

        if topic_seed is None:
            log.error("[%s] type=%s에 해당하는 topic이 없음 — SKIP", ep_id, content_type)
            results.append(EpisodeResult(
                ep_id=ep_id, topic_id="", topic="",
                content_type=content_type, style="docsul",
                success=False, final_status="FAIL",
                fail_reason=f"topics.json에 {content_type} 항목 없음",
            ))
            continue

        used_ids.add(topic_seed["id"])

        r = run_episode(
            ep_id=ep_id,
            topic_seed=topic_seed,
            content_type=content_type,
            base_dir=base_dir,
            script_only=script_only,
            auto=True,
        )
        results.append(r)

        # 사용 이력 업데이트
        _mark_topic_used(topic_seed["id"], topics)
        _save_topics(topics, topics_file)

    _save_batch_report(results, base_dir)
    return results


def _save_batch_report(results: list[EpisodeResult], base_dir: Path = BASE_DIR) -> None:
    success = [r for r in results if r.success]
    failed  = [r for r in results if not r.success]

    log.info("=" * 55)
    log.info("배치 완료 — 성공: %d / 전체: %d", len(success), len(results))

    if success:
        log.info("── 성공 ──────────────────────────────────────")
        for r in success:
            ssp = r.scores.get("scroll_stop_power", "-")
            emo = r.scores.get("emotional_attack",  "-")
            rep = r.scores.get("repeat_value",       "-")
            log.info(
                "  PASS %-16s | %-12s | type=%-8s | ssp=%s emo=%s rep=%s view=%s | %.1fs",
                r.ep_id, r.topic[:12], r.content_type,
                ssp, emo, rep, r.view_score, r.elapsed_s,
            )

    if failed:
        log.warning("── 실패 ──────────────────────────────────────")
        for r in failed:
            log.warning("  FAIL %-16s | %-12s | %s",
                        r.ep_id, r.topic[:12], r.fail_reason)

    if success:
        type_counts: dict[str, int] = {}
        for r in success:
            type_counts[r.content_type] = type_counts.get(r.content_type, 0) + 1
        log.info("── 콘텐츠 타입 분포 ──────────────────────────")
        for t, n in sorted(type_counts.items(), key=lambda x: -x[1]):
            log.info("  %-10s: %d편 (%.0f%%)", t, n, n / len(success) * 100)

    report = [
        {
            "ep_id":        r.ep_id,
            "topic_id":     r.topic_id,
            "content_type": r.content_type,
            "topic":        r.topic,
            "final_status": r.final_status,
            "fail_reason":  r.fail_reason,
            "scores":       r.scores,
            "view_score":   r.view_score,
            "output_mp4":   r.output_mp4,
            "elapsed_s":    r.elapsed_s,
        }
        for r in results
    ]

    report_path = base_dir / "batch_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    log.info("리포트 저장 → %s", report_path)


# ─────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="매일의 설계 콘텐츠 파이프라인 v3.1",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("--batch",         action="store_true",  help="배치 자동 생성")
    p.add_argument("--count",         type=int, default=10, help="생성할 편수 (기본 10)")
    p.add_argument("--script-only",   action="store_true",  help="대본만 생성")
    p.add_argument("--start-seq",     type=int, default=1,  help="시퀀스 시작 번호")
    p.add_argument("--exclude-days",  type=int, default=7,  help="최근 N일 사용 topic 제외")
    p.add_argument("--ep",            default=None,         help="단일 에피소드 ID")
    p.add_argument("--topic-id",      default=None,         help="topics.json의 id (단일 실행용)")
    p.add_argument("--content-type",  default=None,
                   choices=["emotion", "ranking", "money", "quote", "hybrid"],
                   help="topic-id 없을 때 pool에서 자동 선택")
    p.add_argument("--style",         default=None,
                   choices=["docsul", "janas", "list", "seulki"])
    p.add_argument("--auto",          action="store_true",  help="대본 확인 없이 자동 진행")
    p.add_argument("--base",          default=str(BASE_DIR))
    p.add_argument("--topics-file",   default=str(TOPICS_FILE))
    return p


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
        datefmt="%H:%M:%S",
    )

    parser = _build_parser()
    args   = parser.parse_args()
    base   = Path(args.base)
    topics_file = Path(args.topics_file)

    if args.batch:
        run_batch(
            count=args.count,
            base_dir=base,
            topics_file=topics_file,
            script_only=args.script_only,
            start_seq=args.start_seq,
            exclude_days=args.exclude_days,
        )

    elif args.ep:
        topics = _load_topics(topics_file)

        # topic_id 직접 지정 or content_type으로 pool 선택
        if args.topic_id:
            seed = next((t for t in topics if t["id"] == args.topic_id), None)
            if not seed:
                log.error("topic_id '%s' 를 topics.json에서 찾을 수 없음", args.topic_id)
                sys.exit(1)
        elif args.content_type:
            seed = _select_topic(args.content_type, topics, set(), args.exclude_days)
            if not seed:
                log.error("content_type '%s'에 해당하는 topic 없음", args.content_type)
                sys.exit(1)
        else:
            log.error("--topic-id 또는 --content-type 중 하나는 필수")
            parser.print_help()
            sys.exit(1)

        result = run_episode(
            ep_id=args.ep,
            topic_seed=seed,
            content_type=seed["content_type"],
            style=args.style,
            base_dir=base,
            script_only=args.script_only,
            auto=args.auto,
        )

        if result.success:
            _mark_topic_used(seed["id"], topics)
            _save_topics(topics, topics_file)

        sys.exit(0 if result.success else 1)

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()

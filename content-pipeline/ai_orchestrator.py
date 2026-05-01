"""
ai_orchestrator.py
==================
콘텐츠 자동화 파이프라인 오케스트레이터 v3

Flow per episode:
  ① Quality Gate 재검수 — 기존 script.json이 있으면 v3로 먼저 검사
  ② generate_script  — GPT-4o + Claude + Quality Gate (PASS만 통과)
  ③ generate_images  — DALL-E 3 HD 8장
  ④ generate_tts     — Edge TTS / ElevenLabs + ASS 자막
  ⑤ make_video       — FFmpeg 최종 합성

FAIL이면 절대 ③으로 넘기지 않는다.

실행 방법:
  # 배치 (자동 비율: emotion 30% / ranking 30% / money 20% / quote 20%)
  python ai_orchestrator.py --batch --count 10

  # 배치 대본만
  python ai_orchestrator.py --batch --count 10 --script-only

  # 단일 에피소드 (주제 지정)
  python ai_orchestrator.py --ep 20260501_001 --topic "참을수록 망가지는 이유" --content-type emotion

  # 단일 (주제 자동)
  python ai_orchestrator.py --ep 20260501_001 --content-type ranking
"""

import argparse
import json
import logging
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import anthropic

from config import CLAUDE_API_KEY
from generate_script import generate_best_script
from quality_gate import recheck_v3

log = logging.getLogger("orchestrator")

BASE_DIR = Path(os.getenv("PIPELINE_BASE", "/root/auto_pipeline"))

# ─────────────────────────────────────────────
# 콘텐츠 타입 비율 (배치 자동 분배)
# ─────────────────────────────────────────────
CONTENT_RATIO = {
    "emotion": 30,
    "ranking": 30,
    "money":   20,
    "quote":   20,
}

# content_type → 기본 style 매핑
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
    ep_id:        str
    content_type: str
    topic:        str
    style:        str
    success:      bool
    final_status: str        = "FAIL"
    fail_reason:  str        = ""
    scores:       dict       = field(default_factory=dict)
    view_score:   int        = 0
    output_mp4:   str | None = None
    elapsed_s:    float      = 0.0


# ─────────────────────────────────────────────
# 배치 계획 (비율 기반 content_type 순서)
# ─────────────────────────────────────────────

def _plan_batch(count: int) -> list[str]:
    """count개 에피소드의 content_type 순서를 비율대로 결정한다."""
    types: list[str] = []
    for t, pct in CONTENT_RATIO.items():
        n = max(1, round(count * pct / 100))
        types.extend([t] * n)

    # 반올림 오차 보정
    while len(types) < count:
        types.append("emotion")

    return types[:count]


def _make_ep_id(seq: int) -> str:
    """YYYYMMDD_NNN 형식 ep_id 생성."""
    return f"{datetime.now().strftime('%Y%m%d')}_{seq:03d}"


# ─────────────────────────────────────────────
# 기존 script.json 재검수
# ─────────────────────────────────────────────

def _recheck_existing(ep_dir: Path, client: anthropic.Anthropic) -> dict | None:
    """기존 script.json이 있으면 v3 Quality Gate로 재검수한다.
    PASS이면 script dict 반환, FAIL이거나 없으면 None.
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
    ep_id  = script.get("ep_id", meta.get("ep_id", "-"))
    ctype  = script.get("content_type", "-")
    topic  = script.get("topic", meta.get("topic", ""))

    print(f"\n{'=' * 55}")
    print(f"  [{ep_id}] 생성된 대본")
    print(f"{'=' * 55}")
    print(f"  주제         : {topic}")
    print(f"  콘텐츠 타입  : {ctype}  (mix: {script.get('mix', ctype)})")
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
    content_type: str        = "emotion",
    topic:        str | None = None,
    style:        str | None = None,
    base_dir:     Path       = BASE_DIR,
    script_only:  bool       = False,
    auto:         bool       = False,
) -> EpisodeResult:
    """
    단일 에피소드 파이프라인 실행.
    FAIL이면 영상 단계(generate_images 이후)로 절대 넘기지 않는다.

    Parameters
    ----------
    ep_id        : 에피소드 ID (YYYYMMDD_NNN)
    content_type : emotion | ranking | money | quote | hybrid
    topic        : 영상 주제 (None이면 GPT 자동 선정)
    style        : docsul | janas | list | seulki (None이면 content_type 기반 자동)
    base_dir     : 베이스 디렉토리
    script_only  : True이면 대본 생성까지만
    auto         : True이면 대본 확인 없이 자동 진행 (배치용)
    """
    ep_dir  = base_dir / "episodes" / ep_id
    ep_dir.mkdir(parents=True, exist_ok=True)
    t_start = datetime.now()

    resolved_style = style or TYPE_STYLE_MAP.get(content_type, "docsul")

    log.info("=" * 55)
    log.info("[%s] 시작 — type=%s style=%s topic=%s",
             ep_id, content_type, resolved_style, topic or "(GPT 자동)")

    client_claude = anthropic.Anthropic(api_key=CLAUDE_API_KEY)

    try:
        # ① 기존 script.json v3 재검수
        script = _recheck_existing(ep_dir, client_claude)

        # ② FAIL이거나 없으면 신규 생성
        if script is None:
            log.info("[%s] 신규 대본 생성 (최대 3회)", ep_id)
            script = generate_best_script(
                topic=topic,
                content_type=content_type,
                ep_dir=str(ep_dir),
                ep_id=ep_id,
                style=resolved_style,
            )

        if script is None:
            return EpisodeResult(
                ep_id=ep_id, content_type=content_type,
                topic=topic or "", style=resolved_style,
                success=False, final_status="FAIL",
                fail_reason="Quality Gate 3회 실패",
                elapsed_s=(datetime.now() - t_start).total_seconds(),
            )

        # final_status 확인 — FAIL이면 절대 영상 단계로 안 넘김
        if script.get("final_status", "PASS") != "PASS":
            log.error("[%s] script final_status=FAIL — 영상 생성 중단", ep_id)
            return EpisodeResult(
                ep_id=ep_id, content_type=content_type,
                topic=script.get("topic", topic or ""), style=resolved_style,
                success=False, final_status="FAIL",
                fail_reason=script.get("fail_reason", "FAIL"),
                elapsed_s=(datetime.now() - t_start).total_seconds(),
            )

        meta     = script.get("_meta", {})
        scores   = meta.get("scores", {})
        cur_type = script.get("content_type", content_type)
        cur_view = script.get("view_score", meta.get("view_score", 0))
        cur_topic= script.get("topic", topic or "")

        _print_script(script)

        if script_only:
            log.info("[%s] --script-only 완료", ep_id)
            return EpisodeResult(
                ep_id=ep_id, content_type=cur_type,
                topic=cur_topic, style=resolved_style,
                success=True, final_status="PASS",
                scores=scores, view_score=cur_view,
                elapsed_s=(datetime.now() - t_start).total_seconds(),
            )

        # ③ 사용자 확인
        if not auto:
            answer = input("▶ 이 대본으로 영상을 제작할까요? [y/N]: ").strip().lower()
            if answer != "y":
                log.info("[%s] 사용자 취소", ep_id)
                return EpisodeResult(
                    ep_id=ep_id, content_type=cur_type,
                    topic=cur_topic, style=resolved_style,
                    success=False, final_status="FAIL", fail_reason="사용자 취소",
                    elapsed_s=(datetime.now() - t_start).total_seconds(),
                )

        # ④ 이미지 생성
        log.info("[%s] 이미지 생성", ep_id)
        from generate_image import generate_images
        raw_scenes = script.get("scenes", [])
        scenes = [
            s if isinstance(s, dict) else {"image_prompt": s}
            for s in raw_scenes
        ]
        generate_images(scenes, str(ep_dir))

        # ⑤ TTS + 자막
        log.info("[%s] TTS + 자막", ep_id)
        from generate_tts import generate_tts
        voice_path = ep_dir / "voice_ko.mp3"
        generate_tts(script, str(voice_path), style=resolved_style)

        # ⑥ 영상 합성
        log.info("[%s] 영상 합성", ep_id)
        from make_video import make_video
        make_video(str(ep_dir), script, style=resolved_style)

        output_mp4 = ep_dir / "output_final.mp4"
        elapsed    = (datetime.now() - t_start).total_seconds()
        log.info("[%s] 완료 (%.1fs) — %s", ep_id, elapsed, output_mp4)

        return EpisodeResult(
            ep_id=ep_id, content_type=cur_type,
            topic=cur_topic, style=resolved_style,
            success=True, final_status="PASS",
            scores=scores, view_score=cur_view,
            output_mp4=str(output_mp4), elapsed_s=elapsed,
        )

    except Exception as exc:
        elapsed = (datetime.now() - t_start).total_seconds()
        log.error("[%s] 예외 (%.1fs): %s", ep_id, elapsed, exc, exc_info=True)
        return EpisodeResult(
            ep_id=ep_id, content_type=content_type,
            topic=topic or "", style=resolved_style,
            success=False, final_status="FAIL", fail_reason=str(exc),
            elapsed_s=elapsed,
        )


# ─────────────────────────────────────────────
# 배치 실행
# ─────────────────────────────────────────────

def run_batch(
    count:       int  = 10,
    base_dir:    Path = BASE_DIR,
    script_only: bool = False,
    start_seq:   int  = 1,
) -> list[EpisodeResult]:
    """
    count개 에피소드를 CONTENT_RATIO 비율대로 자동 생성한다.
    ep_id: YYYYMMDD_NNN (시퀀스 번호 자동 증가)
    topic: GPT 자동 선정
    배치는 항상 auto=True (대본 확인 없이 진행).
    """
    type_plan = _plan_batch(count)
    results:   list[EpisodeResult] = []

    log.info("배치 시작 — %d편 | 타입 계획: %s", count,
             {t: type_plan.count(t) for t in set(type_plan)})

    for seq, content_type in enumerate(type_plan, start=start_seq):
        ep_id = _make_ep_id(seq)
        r = run_episode(
            ep_id=ep_id,
            content_type=content_type,
            topic=None,  # GPT 자동 선정
            base_dir=base_dir,
            script_only=script_only,
            auto=True,
        )
        results.append(r)

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
                "  PASS %-16s | type=%-8s | ssp=%-2s emo=%-2s rep=%-2s view=%-2s | %.1fs",
                r.ep_id, r.content_type, ssp, emo, rep, r.view_score, r.elapsed_s,
            )

    if failed:
        log.warning("── 실패 ──────────────────────────────────────")
        for r in failed:
            log.warning("  FAIL %-16s | %s", r.ep_id, r.fail_reason)

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
        description="매일의 설계 콘텐츠 파이프라인 v3",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = p.add_subparsers(dest="cmd")

    # -- 배치
    b = sub.add_parser("batch", help="배치 자동 생성")
    b.add_argument("--count",       type=int, default=10, help="생성할 편수 (기본 10)")
    b.add_argument("--script-only", action="store_true",  help="대본만 생성")
    b.add_argument("--start-seq",   type=int, default=1,  help="시퀀스 시작 번호")
    b.add_argument("--base",        default=str(BASE_DIR))

    # -- 단일
    s = sub.add_parser("episode", help="단일 에피소드")
    s.add_argument("--ep",           required=True, help="에피소드 ID (YYYYMMDD_NNN)")
    s.add_argument("--content-type", default="emotion",
                   choices=["emotion", "ranking", "money", "quote", "hybrid"])
    s.add_argument("--topic",        default=None,  help="주제 (없으면 GPT 자동)")
    s.add_argument("--style",        default=None,
                   choices=["docsul", "janas", "list", "seulki"])
    s.add_argument("--script-only",  action="store_true")
    s.add_argument("--auto",         action="store_true")
    s.add_argument("--base",         default=str(BASE_DIR))

    # 하위 호환: 플래그 직접 (--batch --count)
    p.add_argument("--batch",        action="store_true")
    p.add_argument("--count",        type=int, default=10)
    p.add_argument("--script-only",  action="store_true")
    p.add_argument("--start-seq",    type=int, default=1)
    p.add_argument("--ep",           default=None)
    p.add_argument("--content-type", default="emotion",
                   choices=["emotion", "ranking", "money", "quote", "hybrid"])
    p.add_argument("--topic",        default=None)
    p.add_argument("--style",        default=None)
    p.add_argument("--auto",         action="store_true")
    p.add_argument("--base",         default=str(BASE_DIR))

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

    if args.batch:
        run_batch(
            count=args.count,
            base_dir=base,
            script_only=args.script_only,
            start_seq=args.start_seq,
        )

    elif args.ep:
        ct    = getattr(args, "content_type", "emotion")
        style = getattr(args, "style", None)
        result = run_episode(
            ep_id=args.ep,
            content_type=ct,
            topic=args.topic,
            style=style,
            base_dir=base,
            script_only=args.script_only,
            auto=args.auto,
        )
        sys.exit(0 if result.success else 1)

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()

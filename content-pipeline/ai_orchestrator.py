"""
ai_orchestrator.py
==================
전체 콘텐츠 파이프라인 오케스트레이터

Flow per episode:
  ① generate_script  : GPT-4o 초안 → Claude 검수/교정 → script.json
  ② generate_images  : DALL-E 3 HD 8장 → bg1~bg8.jpg
  ③ generate_tts     : Edge TTS / ElevenLabs → voice_ko.mp3 + subtitles_tts.ass
  ④ make_video       : FFmpeg → output_final.mp4

실행 방법:
  # 단일 에피소드
  python ai_orchestrator.py --ep ep011 --topic "참을수록 망가지는 이유" --style docsul

  # 배치 (EPISODE_LIST 기준)
  python ai_orchestrator.py --batch

  # 대본만 생성 (영상 없이)
  python ai_orchestrator.py --ep ep011 --topic "..." --style docsul --script-only
"""

import argparse
import json
import logging
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from generate_script import generate_best_script

log = logging.getLogger("orchestrator")

BASE_DIR = Path(os.getenv("PIPELINE_BASE", "/root/auto_pipeline"))

# ─────────────────────────────────────────────
# 에피소드 목록 (대기 중 EP011~EP020)
# ─────────────────────────────────────────────
EPISODE_LIST: list[tuple[str, str, str]] = [
    # (ep_id,      topic,                              style)
    ("ep011", "참을수록 망가지는 이유",                   "docsul"),
    ("ep012", "일희일비가 운을 믿지 않는 이유",            "docsul"),
    ("ep013", "뇌과학이 말한 진짜 강한 사람의 조건",        "docsul"),
    ("ep014", "자기믿음이 절대 부자 못 되는 구조",          "docsul"),
    ("ep015", "팀장이 대화하며만 일 시키는 이유",           "janas"),
    ("ep016", "퇴사하려다 막히는 그런 밤",                 "janas"),
    ("ep017", "40대 되면 후회하는 30대의 실수들",           "list"),
    ("ep018", "돈 못 버는 사람이 매일 하는 말",             "list"),
    ("ep019", "진짜 번아웃이 온 사람들의 증상",             "list"),
    ("ep020", "착한 척하는 사람 옆에 있으면 생기는 일",     "docsul"),
]


# ─────────────────────────────────────────────
# 결과 데이터클래스
# ─────────────────────────────────────────────
@dataclass
class EpisodeResult:
    ep_id:      str
    topic:      str
    style:      str
    success:    bool
    error:      str | None  = None
    scores:     dict        = field(default_factory=dict)
    output_mp4: str | None  = None
    elapsed_s:  float       = 0.0


# ─────────────────────────────────────────────
# 단일 에피소드 실행
# ─────────────────────────────────────────────

def run_episode(
    ep_id:       str,
    topic:       str,
    style:       str        = "docsul",
    base_dir:    Path       = BASE_DIR,
    script_only: bool       = False,
) -> EpisodeResult:
    """
    단일 에피소드 전체(또는 대본만) 파이프라인 실행.

    Parameters
    ----------
    ep_id       : 에피소드 ID (예: ep011)
    topic       : 영상 주제
    style       : docsul | janas | list | seulki
    base_dir    : /root/auto_pipeline
    script_only : True이면 대본 생성까지만 실행
    """
    ep_dir  = base_dir / "episodes" / ep_id
    ep_dir.mkdir(parents=True, exist_ok=True)
    t_start = datetime.now()

    log.info("=" * 55)
    log.info("[%s] 시작 — topic='%s', style='%s'", ep_id, topic, style)

    try:
        # ① 대본 생성 (GPT → Claude)
        log.info("[%s] ① 대본 생성", ep_id)
        script = generate_best_script(topic, style, ep_dir=str(ep_dir))
        scores = script.get("_meta", {}).get("scores", {})

        if script_only:
            log.info("[%s] --script-only 모드: 대본 생성 완료 후 종료", ep_id)
            return EpisodeResult(
                ep_id=ep_id, topic=topic, style=style,
                success=True, scores=scores,
                elapsed_s=(datetime.now() - t_start).total_seconds(),
            )

        # ② 이미지 생성
        log.info("[%s] ② 이미지 생성", ep_id)
        from generate_image import generate_images
        generate_images(script.get("scenes", []), str(ep_dir))

        # ③ TTS + 자막
        log.info("[%s] ③ TTS + 자막", ep_id)
        from generate_tts import generate_tts
        voice_path = ep_dir / "voice_ko.mp3"
        generate_tts(script, str(voice_path), style=style)

        # ④ 영상 합성
        log.info("[%s] ④ 영상 합성", ep_id)
        from make_video import make_video
        make_video(str(ep_dir), script, style=style)

        output_mp4 = ep_dir / "output_final.mp4"
        elapsed    = (datetime.now() - t_start).total_seconds()
        log.info("[%s] ✅ 완료 (%.1fs) — %s", ep_id, elapsed, output_mp4)

        return EpisodeResult(
            ep_id=ep_id, topic=topic, style=style,
            success=True, scores=scores,
            output_mp4=str(output_mp4), elapsed_s=elapsed,
        )

    except Exception as exc:
        elapsed = (datetime.now() - t_start).total_seconds()
        log.error("[%s] ❌ 실패 (%.1fs): %s", ep_id, elapsed, exc, exc_info=True)
        return EpisodeResult(
            ep_id=ep_id, topic=topic, style=style,
            success=False, error=str(exc), elapsed_s=elapsed,
        )


# ─────────────────────────────────────────────
# 배치 실행
# ─────────────────────────────────────────────

def run_batch(
    episodes:    list[tuple[str, str, str]] | None = None,
    base_dir:    Path                              = BASE_DIR,
    script_only: bool                             = False,
) -> list[EpisodeResult]:
    """
    여러 에피소드를 순차 실행하고 요약 리포트를 출력한다.

    Parameters
    ----------
    episodes    : [(ep_id, topic, style), ...] — None이면 EPISODE_LIST 사용
    base_dir    : 베이스 디렉토리
    script_only : True이면 대본 생성까지만 실행
    """
    targets = episodes or EPISODE_LIST
    results: list[EpisodeResult] = []

    for ep_id, topic, style in targets:
        r = run_episode(ep_id, topic, style, base_dir, script_only)
        results.append(r)

    _print_batch_report(results)
    return results


def _print_batch_report(results: list[EpisodeResult]) -> None:
    """배치 완료 후 요약 리포트를 출력한다."""
    success = [r for r in results if r.success]
    failed  = [r for r in results if not r.success]

    log.info("=" * 55)
    log.info("배치 완료 — 성공: %d / 전체: %d", len(success), len(results))

    if success:
        log.info("── 성공 목록 ──────────────────────────────────")
        for r in success:
            ssp = r.scores.get("scroll_stop_power", "-")
            emo = r.scores.get("emotional_attack",  "-")
            rep = r.scores.get("repeat_value",       "-")
            log.info(
                "  ✅ %-12s | ssp=%-3s emo=%-3s rep=%-3s | %.1fs",
                r.ep_id, ssp, emo, rep, r.elapsed_s,
            )

    if failed:
        log.warning("── 실패 목록 ──────────────────────────────────")
        for r in failed:
            log.warning("  ❌ %-12s | %s", r.ep_id, r.error)

    # 리포트 JSON 저장
    report_path = BASE_DIR / "batch_report.json"
    report = [
        {
            "ep_id":      r.ep_id,
            "topic":      r.topic,
            "style":      r.style,
            "success":    r.success,
            "error":      r.error,
            "scores":     r.scores,
            "elapsed_s":  r.elapsed_s,
            "output_mp4": r.output_mp4,
        }
        for r in results
    ]
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    log.info("리포트 저장 → %s", report_path)


# ─────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────
def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="매일의 설계 콘텐츠 자동화 파이프라인",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("--ep",          help="단일 에피소드 ID (예: ep011)")
    p.add_argument("--topic",       help="영상 주제")
    p.add_argument("--style",       default="docsul",
                   choices=["docsul", "janas", "list", "seulki"],
                   help="스타일 (기본: docsul)")
    p.add_argument("--batch",       action="store_true", help="배치 실행 (EPISODE_LIST)")
    p.add_argument("--script-only", action="store_true", help="대본 생성까지만 실행")
    p.add_argument("--base",        default=str(BASE_DIR), help="베이스 디렉토리")
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
        run_batch(base_dir=base, script_only=args.script_only)

    elif args.ep and args.topic:
        result = run_episode(
            args.ep, args.topic, args.style,
            base_dir=base, script_only=args.script_only,
        )
        sys.exit(0 if result.success else 1)

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()

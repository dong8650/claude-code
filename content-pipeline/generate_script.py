"""
generate_script.py
==================
대본 생성 파이프라인 — GPT-4o (초안) → Claude (검수/교정/저장)

Flow:
  1. GPT-4o: 바이럴 최적화 대본 초안 생성
  2. Claude: 100만 조회수 규칙 검수 + 자동 교정 + 품질 점수 기록
  3. 최종 script.json 저장
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path

import anthropic
import openai

from config import CLAUDE_API_KEY, OPENAI_API_KEY

log = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# 스타일 정의
# ─────────────────────────────────────────────
STYLE_INSTRUCTIONS: dict[str, str] = {
    "docsul": (
        "독설형: 날카롭고 직격적인 어조. "
        "듣기 불편하지만 공감되는 말투. "
        "주어 생략, 단문 선호."
    ),
    "janas": (
        "일화형: 실제 대화/상황처럼 장면을 제시. "
        "'누군가가 말했다' '그 순간' 같은 도입부 사용."
    ),
    "list": (
        "리스트형: '~하는 N가지' 구조. "
        "각 항목을 짧고 임팩트 있게. 번호 없이 흐름으로 연결."
    ),
    "seulki": (
        "감성형: 따뜻하고 울림 있는 어조. "
        "여성 화자 느낌. 감정 공명 극대화."
    ),
}

# ─────────────────────────────────────────────
# GPT 프롬프트
# ─────────────────────────────────────────────
_GPT_SYSTEM = """\
당신은 유튜브 쇼츠 바이럴 대본 전문 작가입니다.
채널: 매일의 설계 | 대상: 30~40대 직장인 | 테마: 철학·뇌과학·명상
목표: 100만 조회수 / 영상 길이 18~25초

[100만 조회수 대본 규칙]
1. hook     — 8자 이내, 즉시 공격형 (스크롤 정지 유도)
2. script_ko — 3~5문장, 총 60~100자, 각 문장 18자 이하
3. closing_ko — 10자 이내 1문장 (행동 유도)
4. 설명형 금지: "~라고 할 수 있습니다" "~입니다" 형 제거
5. 구조: 직격 → 사실 공감 → 반전/뒤집기 → 행동 이구
6. scenes   — 9:16 세로 영상용 영어 묘사 8개 (DALL-E 3 HD 프롬프트)\
"""

_GPT_USER_TMPL = """\
주제: {topic}
스타일: {style_hint}

아래 JSON 형식으로만 응답 (마크다운·코드블록 없이):
{{
  "hook":       "<8자 이내 첫 문장>",
  "script_ko":  "<문장1. 문장2. 문장3.>",
  "closing_ko": "<10자 이내 마무리>",
  "t1":         "<영상 상단 제목 1줄>",
  "t2":         "<영상 상단 제목 2줄 (임팩트 키워드)>",
  "scenes": [
    "<scene1 영어 묘사, cinematic 9:16>",
    "<scene2>", "<scene3>", "<scene4>",
    "<scene5>", "<scene6>", "<scene7>", "<scene8>"
  ]
}}\
"""

# ─────────────────────────────────────────────
# Claude 검수 프롬프트
# ─────────────────────────────────────────────
_CLAUDE_REVIEW_SYSTEM = """\
당신은 유튜브 쇼츠 대본 품질 검수 AI입니다.
GPT가 생성한 대본을 [검수 규칙]에 따라 점검하고, 위반 항목을 자동 교정합니다.
반드시 JSON으로만 응답합니다.\
"""

_CLAUDE_REVIEW_USER_TMPL = """\
[검수 규칙]
R1. hook: 공백 제외 8자 이내 — 초과 시 핵심만 남겨 단축
R2. script_ko: 문장 수 3~5개 / 총 글자 수 60~100자 / 각 문장 18자 이하
    - 위반 문장은 분할하거나 단축
R3. closing_ko: 공백 제외 10자 이내 — 초과 시 단축
R4. 설명형 문장 금지 ("~할 수 있습니다", "~이라고 합니다" 등) → 직격형으로 교정
R5. 금지어·비속어·법적 위험 요소 탐지 → 교정 또는 삭제
R6. scenes: 반드시 8개 영어 묘사 (부족하면 추가, 초과 시 앞 8개 사용)
R7. t1, t2: 빈 값이면 주제에서 추출해 채움

[품질 지표] 교정 후 평가, 각 10점 만점
- scroll_stop_power : hook이 스크롤을 멈추는 힘
- emotional_attack  : 감정 자극 강도
- repeat_value      : 반복 시청 가치

[원본 대본 (GPT 생성)]
{draft}

[응답 JSON 형식] (마크다운·코드블록 없이)
{{
  "hook":       "...",
  "script_ko":  "...",
  "closing_ko": "...",
  "t1":         "...",
  "t2":         "...",
  "scenes":     ["...", "...", "...", "...", "...", "...", "...", "..."],
  "review_log": {{
    "violations":          ["위반 항목 (없으면 빈 배열)"],
    "corrections":         ["교정 내용 (없으면 빈 배열)"],
    "scroll_stop_power":   0,
    "emotional_attack":    0,
    "repeat_value":        0,
    "verdict":             "PASS | CORRECTED"
  }}
}}\
"""


# ─────────────────────────────────────────────
# 내부 함수
# ─────────────────────────────────────────────

def _gpt_draft(topic: str, style: str, client: openai.OpenAI) -> dict:
    """GPT-4o로 바이럴 대본 초안을 생성한다."""
    style_hint = STYLE_INSTRUCTIONS.get(style, STYLE_INSTRUCTIONS["docsul"])
    user_msg = _GPT_USER_TMPL.format(topic=topic, style_hint=style_hint)

    resp = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": _GPT_SYSTEM},
            {"role": "user",   "content": user_msg},
        ],
        temperature=0.9,
        response_format={"type": "json_object"},
    )

    raw = resp.choices[0].message.content
    log.debug("[GPT draft] %s", raw)
    return json.loads(raw)


def _claude_review(draft: dict, client: anthropic.Anthropic) -> dict:
    """Claude가 GPT 초안을 검수·교정하고 review_log를 포함해 반환한다."""
    draft_str = json.dumps(draft, ensure_ascii=False, indent=2)
    user_msg = _CLAUDE_REVIEW_USER_TMPL.format(draft=draft_str)

    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        system=_CLAUDE_REVIEW_SYSTEM,
        messages=[{"role": "user", "content": user_msg}],
    )

    raw = msg.content[0].text.strip()
    # 마크다운 코드블록 방어 처리
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    log.debug("[Claude review] %s", raw)
    return json.loads(raw)


def _log_review(review_log: dict, ep_dir: str | None) -> None:
    """검수 결과를 로거에 출력하고 review_log.json으로 저장한다."""
    verdict  = review_log.get("verdict", "UNKNOWN")
    ssp      = review_log.get("scroll_stop_power", "-")
    emo      = review_log.get("emotional_attack", "-")
    rep      = review_log.get("repeat_value", "-")

    log.info(
        "[검수] verdict=%-10s | scroll_stop=%s | emotional=%s | repeat=%s",
        verdict, ssp, emo, rep,
    )
    for v in review_log.get("violations", []):
        log.warning("  ⚠ 위반: %s", v)
    for c in review_log.get("corrections", []):
        log.info("  ✏ 교정: %s", c)

    if ep_dir:
        log_path = Path(ep_dir) / "review_log.json"
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump(review_log, f, ensure_ascii=False, indent=2)
        log.info("[저장] %s", log_path)


# ─────────────────────────────────────────────
# 퍼블릭 엔트리포인트
# ─────────────────────────────────────────────

def generate_best_script(
    topic: str,
    style: str = "docsul",
    ep_dir: str | None = None,
) -> dict:
    """
    GPT → Claude 파이프라인으로 최종 대본을 생성한다.

    Parameters
    ----------
    topic   : 영상 주제 (예: "참을수록 망가지는 이유")
    style   : docsul | janas | list | seulki
    ep_dir  : 경로 지정 시 script.json + review_log.json 저장

    Returns
    -------
    script dict (review_log 제거, _meta 포함)
    """
    client_openai  = openai.OpenAI(api_key=OPENAI_API_KEY)
    client_claude  = anthropic.Anthropic(api_key=CLAUDE_API_KEY)

    # ① GPT 초안
    log.info("[GPT-4o] 대본 초안 생성 — topic='%s', style='%s'", topic, style)
    draft = _gpt_draft(topic, style, client_openai)

    # ② 디렉토리 먼저 생성 (review_log.json 저장 전 필요)
    if ep_dir:
        Path(ep_dir).mkdir(parents=True, exist_ok=True)

    # ③ Claude 검수·교정
    log.info("[Claude] 검수 및 교정 중...")
    reviewed = _claude_review(draft, client_claude)

    # ④ review_log 분리 및 기록
    review_log = reviewed.pop("review_log", {})
    _log_review(review_log, ep_dir)

    # ⑤ 메타 정보 추가 (script.json에 포함, 영상 생성 로직에는 무영향)
    reviewed["_meta"] = {
        "topic":        topic,
        "style":        style,
        "generated_at": datetime.now().isoformat(),
        "verdict":      review_log.get("verdict", "UNKNOWN"),
        "scores": {
            "scroll_stop_power": review_log.get("scroll_stop_power"),
            "emotional_attack":  review_log.get("emotional_attack"),
            "repeat_value":      review_log.get("repeat_value"),
        },
    }

    # ⑥ script.json 저장
    if ep_dir:
        out_path = Path(ep_dir) / "script.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(reviewed, f, ensure_ascii=False, indent=2)
        log.info("[저장] %s", out_path)

    return reviewed


# ─────────────────────────────────────────────
# 단독 실행 (테스트용)
# ─────────────────────────────────────────────
if __name__ == "__main__":
    import argparse

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    parser = argparse.ArgumentParser(description="대본 단독 생성 테스트")
    parser.add_argument("--topic", required=True, help="영상 주제")
    parser.add_argument("--style", default="docsul", help="스타일 (docsul/janas/list/seulki)")
    parser.add_argument("--ep-dir", default=None, help="저장 경로 (지정 시 script.json 저장)")
    args = parser.parse_args()

    result = generate_best_script(args.topic, args.style, args.ep_dir)
    print(json.dumps(result, ensure_ascii=False, indent=2))

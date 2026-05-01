"""
generate_script.py
==================
대본 생성 파이프라인 v3

Flow:
  1. GPT-4o: content_type 기반 주제 자동 선정 + 대본 초안 생성
  2. Claude: 규칙 검수 + 자동 교정 + 품질 점수
  3. Quality Gate: Hard → DROP → Soft (viewability)
  4. FAIL 시 content_type 변경 후 재시도 (최대 3회)

script.json 필수 필드:
  ep_id, content_type, mix, topic, hook, script_ko,
  closing_ko, view_score, final_status
"""

import json
import logging
from datetime import datetime
from pathlib import Path

import anthropic
import openai

from config import CLAUDE_API_KEY, OPENAI_API_KEY
from quality_gate import run_gate

MAX_ATTEMPTS = 3

log = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# content_type 순환 (FAIL 시 다음 타입으로)
# ─────────────────────────────────────────────
_TYPE_CYCLE = ["emotion", "ranking", "money", "quote", "emotion", "ranking"]

STYLE_INSTRUCTIONS: dict[str, str] = {
    "docsul": "독설형: 날카롭고 직격적인 어조. 듣기 불편하지만 공감되는 말투. 주어 생략, 단문 선호.",
    "janas":  "일화형: 실제 대화/상황처럼 장면을 제시. '그 순간' '누군가가 말했다' 도입부 사용.",
    "list":   "리스트형: '~하는 N가지' 구조. 각 항목 짧고 임팩트 있게. 번호 없이 흐름으로 연결.",
    "seulki": "감성형: 따뜻하고 울림 있는 어조. 여성 화자 느낌. 감정 공명 극대화.",
}

# ─────────────────────────────────────────────
# GPT 시스템 프롬프트
# ─────────────────────────────────────────────
_GPT_SYSTEM_BASE = """\
당신은 유튜브 쇼츠 바이럴 대본 전문 작가입니다.
채널: 매일의 설계 | 대상: 30~40대 직장인 | 테마: 철학·뇌과학·명상
목표: 조회수 1만 이상

[절대 금지]
  클리셰: "상사 눈치", "퇴근 자책", "퇴근 후 후회", "회의실 침묵", "잘리고 싶지 않아서", "회의실에서"
  비유/은유: "불씨가 태양 된다", "내면의 폭풍" 등 추상 표현
  설명형: "~하면 ~된다", "~이라고 합니다"
  조언형: "해보세요", "시작하세요"\
"""

_GPT_TYPE_RULES = {
    "emotion": """\

━━━━ [content_type: emotion] 정체성 공격형 ━━━━
목표: "이게 나 얘기다" 충격

HOOK: 6~12자, 반드시 "너/넌/니" 중 1개 포함, 강한 단정형
  PASS ✅ "넌 그냥 겁쟁이야" / "니가 원인이야" / "넌 아직 모른다"
  FAIL ❌ 너/넌/니 없음 / 조언형 / 의문형

BODY: 4~5문장, 총 80~120자, 각 문장 18자 이하
  문장1~2: 클리셰 없는 직장인 내면 묘사 (공감)
  문장3  : 반전 — 예상을 뒤집는 사실
  문장4  : 정체성 타격 — "나는 왜 이러는가"
  문장5  : closing 연결 (선택)

CLOSING: 최대 12자, hook 핵심어 역설 반전
  hook "넌 겁쟁이야" → closing "겁쟁이가 살아남는다"
  행동 촉구 완전 금지\
""",
    "ranking": """\

━━━━ [content_type: ranking] 순위/목록형 ━━━━
목표: "이건 꼭 알아야 해" 궁금증 + 충격

HOOK: 6~12자, 숫자(TOP3·TOP5·3가지·5가지) 포함, 강한 단정형
  PASS ✅ "이 3가지가 망친다" / "TOP3가 뭔지 알아?" / "5가지만 알면 된다"
  FAIL ❌ 숫자 없음

BODY: 4~5문장, 총 80~120자, 각 문장 18자 이하
  각 항목은 반드시 구체적 사실·수치·뇌과학 기반이어야 함
  클리셰 예시 절대 금지:
    ❌ "회의가 많으면 지친다" (당연한 말)
    ❌ "커피를 많이 마신다" (행동 묘사)
  충격 예시:
    ✅ "멀티태스킹 후 IQ 10p 떨어진다" (수치 충격)
    ✅ "수면 6시간이면 뇌 판단력 제로" (뇌과학 사실)
    ✅ "체크리스트가 창의력을 죽인다" (예상 밖 반전)
  마지막 항목이 가장 충격적 — 예상 밖 반전 필수

CLOSING: 최대 12자, hook 핵심 단어를 반드시 역설로 뒤집어라
  ✅ hook "이 5가지가 망친다"  → closing "5가지가 답이다"     (망친다→답)
  ✅ hook "이 3가지가 망친다"  → closing "3가지가 살린다"     (망친다→살린다)
  ✅ hook "뇌를 망친다"        → closing "뇌가 살아난다"      (망친다→살아난다)
  ✅ hook "몸이 망가진다"       → closing "망가짐이 시작이다"  (망가→시작)
  hook 핵심 단어를 그대로 뒤집어라 — 행동 촉구·질문형 완전 금지\
""",
    "money": """\

━━━━ [content_type: money] 현실 수치형 ━━━━
목표: 구체 숫자로 현실 충격 → 감정 압박

HOOK: 6~12자, 숫자+기간 or 금액 포함 필수
  PASS ✅ "10년이 사라졌다" / "월급 30%가 증발한다" / "3년만에 끝났다"
  FAIL ❌ 숫자 없음

BODY: 4~5문장, 총 80~120자, 각 문장 18자 이하
  문장1~2: 현실 수치 제시 (금액·기간·비율)
  문장3  : 충격 반전 — 알고 보면 더 심각
  문장4  : 감정 압박 — "나도 이럴 수 있다" 공포

CLOSING: 최대 12자, hook 핵심 단어(수치/동사)를 반드시 역설로 뒤집어라
  ✅ hook "10년이 사라졌다"   → closing "10년이 기회였다"   (사라졌다→기회)
  ✅ hook "퇴직금 절반 증발"  → closing "증발이 시작이다"   (증발→시작)
  ✅ hook "월급 30%가 사라져" → closing "30%가 여지다"      (사라져→여지)
  hook 핵심 단어를 그대로 뒤집어라 — 행동 촉구·질문형 완전 금지\
""",
    "quote": """\

━━━━ [content_type: quote] 현실 비틀기 명언형 ━━━━
목표: "들어본 말"을 뒤집어 충격 + 공감

HOOK: 6~12자, 통념을 뒤집는 반전 선언 (일반 명언 금지)
  PASS ✅ "노력하면 더 망한다" / "착한 게 패인이었다" / "참는 게 독이었다"
  FAIL ❌ 통념 그대로 / 조언형

BODY: 4~5문장, 총 80~120자, 각 문장 18자 이하
  문장1: hook의 통념이 왜 틀렸는지 현실 제시
  문장2~3: 실제로 벌어지는 반대 현상
  문장4: "나도 그 통념을 믿었다" 정체성 타격

CLOSING: 최대 12자, hook 비틀기를 완성하는 역설 명언 (일반 격언 금지)
  hook "노력하면 더 망한다" → closing "방향이 노력이다"\
""",
    "hybrid": """\

━━━━ [content_type: hybrid] 복합형 (emotion + ranking) ━━━━
목표: 정체성 공격 + 목록 구조 결합

HOOK: 6~12자, 반드시 "너/넌/니" + 숫자 포함
  PASS ✅ "넌 이 3가지야" / "니가 5가지를 몰라"

BODY: emotion 구조에 ranking 항목 배치
  문장1: 정체성 공격 맥락 설정
  문장2~4: 충격 순위 항목 (각 1문장)
  문장5: closing 연결

CLOSING: 최대 12자, hook 역설 반전\
""",
}

_GPT_USER_TMPL = """\
content_type: {content_type}
{topic_line}
스타일: {style_hint}

[body 필수]
각 문장 최대 18자 / 총 80~120자 / 설명형·클리셰·비유 완전 금지

[응답 JSON — 마크다운·코드블록 없이]
{{
  "topic":        "<이 대본의 핵심 주제 (15자 이내)>",
  "content_type": "{content_type}",
  "mix":          "<단일 타입이면 content_type 그대로 / hybrid면 '타입A+타입B'>",
  "pattern_type": "<정체성 파괴 | 자기합리화 파괴 | 현실 충격 | 통념 비틀기>",
  "hook":         "<규칙에 맞는 hook>",
  "script_ko":    "<body 문장들. 마침표로 끝냄. 클리셰·설명형·비유 금지>",
  "closing_ko":   "<최대 12자, hook 역설 반전, 행동 촉구 금지>",
  "t1":           "<영상 상단 제목 1줄>",
  "t2":           "<영상 상단 제목 2줄 (임팩트 키워드, 주황색 표시)>",
  "scenes": [
    "<scene1 영어 묘사, cinematic 9:16, no text, no face>",
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
GPT 생성 대본을 규칙에 따라 점검하고 위반 항목을 자동 교정합니다.
반드시 JSON으로만 응답합니다.\
"""

_CLAUDE_REVIEW_USER_TMPL = """\
[검수 규칙]
R1. hook: 공백 제외 12자 이내 — 초과 시 핵심만 남겨 단축
R2. script_ko: 반드시 4~5문장 / 총 80~120자 / 각 문장 18자 이하
    문장 부족 시 추가, 글자 부족 시 내용 보강
R3. closing_ko: 공백 포함 최대 15자 이내
R4. 설명형 금지 ("~할 수 있습니다", "~이라고 합니다") → 직격형 교정
    ※ 예외: ranking/money 타입에서 구체 수치·뇌과학 사실 문장은 교정 금지
      ✅ 보존: "멀티태스킹 후 IQ 10p 떨어진다" / "수면 6시간이면 판단력 60% 저하"
      ❌ 교정 금지: 수치/사실 → 행동묘사형("~한다")으로 변환하지 말 것
R5. 금지어·비속어·법적 위험 요소 → 교정 또는 삭제
R6. scenes: 반드시 8개 영어 묘사 (부족하면 추가)
R7. t1, t2: 빈 값이면 topic에서 추출
R8. 비유·은유 금지: 추상 표현 → 직장인 일상 구체 표현
R9. 클리셰 금지: "상사 눈치", "퇴근 자책", "회의실 침묵" → 내면 묘사 교정
R10. content_type 규칙 준수:
    emotion: "너/넌/니" 포함 필수
    ranking: 숫자 포함 필수 / 각 항목은 수치·사실 기반 충격 (행동묘사형으로 변환 금지)
    money: 숫자+기간 포함 필수
    quote: 통념 비틀기, 일반 명언 금지

[품질 지표] 교정 후 최종 기준, 각 10점 만점

scroll_stop_power:
  10: 즉시 손이 멈추는 수준 — 정체성/자기합리화 직격
   9: 강한 단정형 hook, "너/넌/니" 포함 or 숫자 충격
   8: 강하지만 예측 가능
   7: 충격 있으나 약함
  6↓: 설명·조언형

emotional_attack:
  10: 심장 철렁, 소름 or 눈물 수준
   9: "이게 나잖아" 반응 — 직장인 내면 직격
   8: 공감되지만 무난
   7: 감정 자극 약함
  6↓: 정보 전달 수준

repeat_value:
   9: hook-closing 역설 완벽, 다시 보면 다른 의미
   8: 흐름 좋고 여운 있음
   7: 역설 있고 깔끔한 마무리
  6↓: 단순 종결

[원본 대본]
{draft}

[응답 JSON — 마크다운·코드블록 없이]
{{
  "topic":        "...",
  "content_type": "...",
  "mix":          "...",
  "pattern_type": "...",
  "hook":         "...",
  "script_ko":    "...",
  "closing_ko":   "...",
  "t1":           "...",
  "t2":           "...",
  "scenes":       ["...", "...", "...", "...", "...", "...", "...", "..."],
  "review_log": {{
    "violations":          [],
    "corrections":         [],
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

def _next_type(attempt: int, preferred: str | None) -> str:
    """시도 번호에 따라 content_type을 선택한다."""
    if attempt == 1 and preferred:
        return preferred
    return _TYPE_CYCLE[(attempt - 1) % len(_TYPE_CYCLE)]


def _gpt_draft(
    content_type: str,
    style:        str,
    client:       openai.OpenAI,
    topic:        str | None = None,
    prev_fail:    str        = "",
) -> dict:
    """GPT-4o로 대본 초안을 생성한다.
    topic=None이면 GPT가 주제도 자동 선정한다.
    """
    style_hint  = STYLE_INSTRUCTIONS.get(style, STYLE_INSTRUCTIONS["docsul"])
    type_rules  = _GPT_TYPE_RULES.get(content_type, _GPT_TYPE_RULES["emotion"])
    system_msg  = _GPT_SYSTEM_BASE + type_rules

    if topic:
        topic_line = f"주제: {topic}"
    else:
        topic_line = (
            "주제: 아래 content_type에 맞게 30~40대 직장인이 즉시 공감할 주제를 "
            "스스로 선정하고 topic 필드에 기입하라."
        )

    user_msg = _GPT_USER_TMPL.format(
        content_type=content_type,
        topic_line=topic_line,
        style_hint=style_hint,
    )

    if prev_fail:
        user_msg += (
            "\n\n[이전 시도 실패 이유 — 반드시 수정하고 재작성]\n" + prev_fail
        )

    resp = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_msg},
            {"role": "user",   "content": user_msg},
        ],
        temperature=0.95,
        response_format={"type": "json_object"},
    )

    raw    = resp.choices[0].message.content
    result = json.loads(raw)
    result["content_type"] = content_type  # GPT가 바꾸지 못하게 강제
    return result


def _claude_review(draft: dict, client: anthropic.Anthropic) -> dict:
    """Claude가 GPT 초안을 검수·교정한다."""
    draft_str = json.dumps(draft, ensure_ascii=False, indent=2)
    user_msg  = _CLAUDE_REVIEW_USER_TMPL.format(draft=draft_str)

    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        system=_CLAUDE_REVIEW_SYSTEM,
        messages=[{"role": "user", "content": user_msg}],
    )

    raw = msg.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    result = json.loads(raw)
    result["content_type"] = draft.get("content_type", "emotion")
    result.setdefault("mix", draft.get("mix", result["content_type"]))
    result.setdefault("topic", draft.get("topic", ""))
    return result


def _log_review(review_log: dict, ep_dir: str | None) -> None:
    verdict = review_log.get("verdict", "UNKNOWN")
    ssp     = review_log.get("scroll_stop_power", "-")
    emo     = review_log.get("emotional_attack",  "-")
    rep     = review_log.get("repeat_value",       "-")

    log.info(
        "[검수] verdict=%-10s | scroll_stop=%s | emotional=%s | repeat=%s",
        verdict, ssp, emo, rep,
    )
    for v in review_log.get("violations", []):
        log.warning("  ⚠ 위반: %s", v)
    for c in review_log.get("corrections", []):
        log.info("  ✏ 교정: %s", c)

    if ep_dir:
        Path(ep_dir).mkdir(parents=True, exist_ok=True)
        log_path = Path(ep_dir) / "review_log.json"
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump(review_log, f, ensure_ascii=False, indent=2)


# ─────────────────────────────────────────────
# 퍼블릭 API
# ─────────────────────────────────────────────

def generate_best_script(
    topic:        str | None = None,
    content_type: str        = "emotion",
    mix:          str | None = None,
    ep_dir:       str | None = None,
    ep_id:        str        = "",
    style:        str        = "docsul",
) -> dict | None:
    """
    GPT → Claude → Quality Gate 파이프라인 (v3).

    Parameters
    ----------
    topic        : 영상 주제 (None이면 GPT가 자동 선정)
    content_type : 콘텐츠 타입 (emotion/ranking/money/quote/hybrid)
    mix          : hybrid 시 결합 타입 (예: "emotion+ranking"), 단일 타입이면 None
    ep_dir       : 저장 경로
    ep_id        : 에피소드 ID (script.json에 기록)
    style        : docsul | janas | list | seulki

    Returns
    -------
    dict (PASS 대본) | None (3회 실패)

    script.json 필수 필드:
      ep_id, content_type, mix, topic, hook, script_ko,
      closing_ko, view_score, final_status
    """
    client_openai = openai.OpenAI(api_key=OPENAI_API_KEY)
    client_claude = anthropic.Anthropic(api_key=CLAUDE_API_KEY)

    if ep_dir:
        Path(ep_dir).mkdir(parents=True, exist_ok=True)

    gen_log:   dict = {"ep_id": ep_id, "attempts": [], "final_status": "FAIL"}
    prev_fail: str  = ""
    used_types: list[str] = []

    for attempt in range(1, MAX_ATTEMPTS + 1):
        # 재시도마다 다른 content_type
        cur_type = _next_type(attempt, content_type if attempt == 1 else None)
        while cur_type in used_types and len(used_types) < len(_TYPE_CYCLE):
            cur_type = _TYPE_CYCLE[len(used_types) % len(_TYPE_CYCLE)]
        used_types.append(cur_type)

        log.info(
            "[시도 %d/%d] ep=%s type=%s style=%s",
            attempt, MAX_ATTEMPTS, ep_id or "-", cur_type, style,
        )

        # ① GPT 초안
        draft = _gpt_draft(cur_type, style, client_openai, topic=topic, prev_fail=prev_fail)

        # ② Claude 검수·교정
        log.info("[시도 %d] Claude 검수 중...", attempt)
        reviewed   = _claude_review(draft, client_claude)
        review_log = reviewed.pop("review_log", {})
        _log_review(review_log, ep_dir)

        scores = {
            "scroll_stop_power": review_log.get("scroll_stop_power", 0),
            "emotional_attack":  review_log.get("emotional_attack",  0),
            "repeat_value":      review_log.get("repeat_value",       0),
        }

        # ③ Quality Gate
        gate = run_gate(reviewed, scores, client_claude, ep_dir)

        gen_log["attempts"].append({
            "attempt":      attempt,
            "content_type": cur_type,
            "topic":        reviewed.get("topic", ""),
            "final_status": gate.final_status,
            "fail_reason":  gate.fail_reason,
        })

        if gate.final_status == "PASS":
            final_topic = reviewed.get("topic") or topic or ""
            final_mix   = reviewed.get("mix") or mix or cur_type

            # script.json 필수 필드 보장
            reviewed.update({
                "ep_id":        ep_id,
                "content_type": cur_type,
                "mix":          final_mix,
                "topic":        final_topic,
                "view_score":   gate.view_score,
                "final_status": "PASS",
                "_meta": {
                    "ep_id":        ep_id,
                    "topic":        final_topic,
                    "style":        style,
                    "content_type": cur_type,
                    "mix":          final_mix,
                    "generated_at": datetime.now().isoformat(),
                    "verdict":      review_log.get("verdict", "UNKNOWN"),
                    "scores":       scores,
                    "view_score":   gate.view_score,
                    "attempts":     attempt,
                },
            })

            gen_log.update({"final_status": "PASS", "content_type": cur_type, "view_score": gate.view_score})

            if ep_dir:
                (Path(ep_dir) / "script.json").write_text(
                    json.dumps(reviewed, ensure_ascii=False, indent=2), encoding="utf-8"
                )
                (Path(ep_dir) / "generation_log.json").write_text(
                    json.dumps(gen_log, ensure_ascii=False, indent=2), encoding="utf-8"
                )
                log.info("[저장] %s/script.json", ep_dir)

            return reviewed

        prev_fail = gate.fail_reason
        log.warning("[시도 %d 실패] type=%s | %s", attempt, cur_type, gate.fail_reason)

    # 3회 모두 실패
    log.error("3회 모두 실패 — EP SKIP | ep_id='%s'", ep_id)
    if ep_dir:
        (Path(ep_dir) / "generation_log.json").write_text(
            json.dumps(gen_log, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    return None


# ─────────────────────────────────────────────
# 단독 실행 (테스트용)
# ─────────────────────────────────────────────
if __name__ == "__main__":
    import argparse
    import logging as _logging

    _logging.basicConfig(
        level=_logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    p = argparse.ArgumentParser(description="대본 단독 생성 테스트 (v3)")
    p.add_argument("--topic",        default=None,       help="영상 주제 (없으면 GPT 자동 선정)")
    p.add_argument("--content-type", default="emotion",
                   choices=["emotion", "ranking", "money", "quote", "hybrid"])
    p.add_argument("--style",        default="docsul",
                   choices=["docsul", "janas", "list", "seulki"])
    p.add_argument("--ep-id",        default="",         help="에피소드 ID")
    p.add_argument("--ep-dir",       default=None,       help="저장 경로")
    args = p.parse_args()

    result = generate_best_script(
        topic=args.topic,
        content_type=args.content_type,
        ep_dir=args.ep_dir,
        ep_id=args.ep_id,
        style=args.style,
    )
    if result:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("3회 시도 모두 실패")

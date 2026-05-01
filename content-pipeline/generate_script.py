"""
generate_script.py
==================
대본 생성 파이프라인 v3.1 — Seed Topic Pool 기반

GPT 역할: 주제 발명 X / 검증된 topic_seed를 content_type 규칙으로 각색
Flow:
  1. GPT-4o: topic_seed(topic + angle + target_emotion) 기반 대본 초안 각색
  2. Claude: 규칙 검수 + 자동 교정 + 품질 점수
  3. Quality Gate: Hard → DROP → Soft (viewability)
  4. FAIL 시 동일 topic_seed, 다른 접근각으로 재시도 (최대 3회)

script.json 필수 필드:
  ep_id, topic_id, content_type, topic, angle, target_emotion,
  hook, script_ko, closing_ko, view_score, final_status
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

STYLE_INSTRUCTIONS: dict[str, str] = {
    "docsul": "독설형: 날카롭고 직격적인 어조. 듣기 불편하지만 공감되는 말투. 주어 생략, 단문 선호.",
    "janas":  "일화형: 실제 대화/상황처럼 장면을 제시. '그 순간' '누군가가 말했다' 도입부 사용.",
    "list":   "리스트형: '~하는 N가지' 구조. 각 항목 짧고 임팩트 있게. 번호 없이 흐름으로 연결.",
    "seulki": "감성형: 따뜻하고 울림 있는 어조. 여성 화자 느낌. 감정 공명 극대화.",
}

# ─────────────────────────────────────────────
# content_type별 규칙 (각색 기준)
# ─────────────────────────────────────────────
_GPT_SYSTEM_BASE = """\
당신은 유튜브 쇼츠 대본 각색 전문가입니다.
채널: 매일의 설계 | 대상: 30~40대 직장인

채널의 역할: "대신 말해주고, 관점을 바꿔주는 채널"
  - 시청자가 혼자 생각하지만 말 못하는 것을 정확히 언어로 잡아준다
  - 충격 → 공감 → 관점 전환 → 하나의 takeaway
  - 보고 나면 세상을 조금 다르게 보게 된다

중요: 당신의 역할은 주제를 새로 만드는 것이 아니다.
검증된 topic과 angle을 받아서 "터지게 각색"하는 것이다.
target_emotion이 대본 전체를 관통해야 한다.

[절대 금지]
  클리셰: "상사 눈치", "퇴근 자책", "퇴근 후 후회", "회의실 침묵", "잘리고 싶지 않아서"
  비유/은유: 추상 표현 ("불씨가 태양 된다", "내면의 폭풍")
  설명형: "~하면 ~된다", "~이라고 합니다"
  조언형: "해보세요", "시작하세요"\
"""

_GPT_TYPE_RULES = {
    "emotion": """\

━━━━ [content_type: emotion] 정체성 공격형 ━━━━
HOOK: 6~12자, 반드시 "너/넌/니" 중 1개 포함, 강한 단정형
  PASS ✅ "넌 그냥 겁쟁이야" / "니가 원인이야" / "넌 아직 모른다"
  FAIL ❌ 너/넌/니 없음 / 조언형 / 의문형

BODY: 4~5문장, 총 80~120자, 각 문장 18자 이하
  문장1~2: 직장인 내면 구체 묘사 (target_emotion이 느껴져야 함)
  문장3  : 반전 — 예상을 뒤집는 사실
  문장4  : 정체성 타격 — "나는 왜 이러는가"
  문장5  : closing 연결 (선택)

CLOSING: 최대 15자, 관점 전환 한 문장
  시청자가 보고 나서 "아, 이렇게 보면 되는구나"가 느껴지는 문장
  "살린다", "답이었다", "기회다" 같은 단어 반전 ❌ 절대 금지
  PASS ✅ 예시:
    "참을수록 망가진다" body → closing: "말할 때 비로소 산다"
    "착하면 손해다" body → closing: "착함보다 경계가 먼저다"
    "넌 을이다" body → closing: "을의 자리를 선택한 거다"\
""",
    "ranking": """\

━━━━ [content_type: ranking] 순위/목록형 ━━━━
HOOK: 6~12자, 숫자(TOP3·TOP5·3가지) 포함, 강한 선언형
  PASS ✅ "이 3가지가 망친다" / "TOP3가 뭔지 알아?"
  FAIL ❌ 숫자 없음

BODY: 4~5문장, 총 80~120자, 각 문장 18자 이하
  각 항목: 클리셰가 아닌 "이건 몰랐다" 수준의 구체 사실
  마지막 항목: 가장 예상 밖 충격
  수치/과학적 사실 기반 (단순 행동 묘사 ❌)
  예시 ✅ "멀티태스킹 후 IQ 10p 떨어진다"
  예시 ❌ "커피를 많이 마신다" / "상사 말만 듣는다"

CLOSING: 최대 15자, 관점 전환 한 문장
  신호를 안 것 자체가 이미 기회다 — 그 방향으로 마무리
  "이 3가지가 망친다" body → closing: "신호가 보이면 아직 기회다"
  "TOP3가 뇌를 망친다" body → closing: "먼저 멈추는 게 회복이다"\
""",
    "money": """\

━━━━ [content_type: money] 현실 수치형 ━━━━
HOOK: 6~12자, 구체적 숫자+기간 or 금액 포함 필수
  PASS ✅ "10년이 사라졌다" / "퇴직금 절반 증발"
  FAIL ❌ 숫자 없음

BODY: 4~5문장, 총 80~120자, 각 문장 18자 이하
  문장1~2: 구체 수치로 현실 충격
  문장3  : 예상보다 더 심각한 반전
  문장4  : "나도 이럴 수 있다" 감정 압박
  수치는 검증 가능한 현실 기반 (과장 금지)

CLOSING: 최대 15자, 관점 전환 한 문장
  수치 현실을 보고 나서 "그래서 뭘 해야 하나"의 방향을 준다
  "퇴직금 절반 증발" body → closing: "월급 말고 자산을 만들어라"
  "10년이 사라졌다" body → closing: "지금부터가 진짜 시작이다"\
""",
    "quote": """\

━━━━ [content_type: quote] 현실 비틀기 명언형 ━━━━
HOOK: 6~12자, 통념을 뒤집는 반전 선언 (일반 명언 금지)
  PASS ✅ "노력하면 더 망한다" / "착한 게 패인이었다"
  FAIL ❌ 통념 그대로 / 조언형

BODY: 4~5문장, 총 80~120자, 각 문장 18자 이하
  문장1: hook의 통념이 왜 틀렸는지 현실 제시
  문장2~3: 실제 벌어지는 반대 현상
  문장4: "나도 그 통념을 믿었다" 정체성 타격

CLOSING: 최대 15자, 관점 전환 한 문장 (일반 격언 금지)
  통념을 뒤집은 이유가 여기서 완성된다 — "그래서 어떻게 보면 되냐"
  "노력하면 더 망한다" body → closing: "먼저 방향, 그다음 노력이다"
  "착하게 살아서 잘 됐냐" body → closing: "착함은 전략이 아니다"\
""",
    "hybrid": """\

━━━━ [content_type: hybrid] 복합형 ━━━━
emotion + ranking 결합
HOOK: "너/넌/니" + 숫자 포함
  PASS ✅ "넌 이 3가지야" / "니가 TOP3야"

BODY: emotion 정체성 공격 + ranking 충격 사실 결합
CLOSING: 최대 12자, hook 역설 반전\
""",
}

_GPT_USER_TMPL = """\
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[각색 대상 — 변경 금지]
topic         : {topic}
angle         : {angle}
target_emotion: {target_emotion}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
content_type  : {content_type}
style         : {style_hint}

[각색 지침]
1. topic을 다른 주제로 바꾸지 말 것
2. angle(각도)이 대본의 핵심 관점이다 — 이 각도로 후킹해라
3. target_emotion({target_emotion})이 보는 사람에게 직격으로 느껴져야 한다
4. body에서 "이 사람이 혼자 생각하지만 말 못하는 것"을 정확히 언어로 잡아라
5. closing은 역설 말장난이 아니라 관점 전환 — "이렇게 보면 달라진다" 수준의 takeaway

[body 필수]
각 문장 최대 18자 / 총 80~120자 / 설명형·클리셰·비유 완전 금지

[응답 JSON — 마크다운·코드블록 없이]
{{
  "topic":        "{topic}",
  "content_type": "{content_type}",
  "mix":          "<단일 타입이면 content_type 그대로 / hybrid면 '타입A+타입B'>",
  "pattern_type": "<정체성 파괴 | 자기합리화 파괴 | 현실 충격 | 통념 비틀기>",
  "hook":         "<규칙에 맞는 hook>",
  "script_ko":    "<body 문장들. 마침표로 끝냄.>",
  "closing_ko":   "<최대 15자, 관점 전환 한 문장 — 보고 나서 달라지는 시각>",
  "t1":           "<영상 상단 제목 1줄 — topic 기반>",
  "t2":           "<영상 상단 제목 2줄 (임팩트 키워드, 주황색)>",
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
    ★ 관점 전환 보호 (절대 교정 금지):
      "이렇게 보면 달라진다" 수준의 takeaway closing은 수정 금지
      예) "먼저 방향, 그다음 노력이다" ✅ 교정 금지
      예) "월급 말고 자산을 만들어라" ✅ 교정 금지
      단순 역설 말장난("살린다", "기회다")은 관점 전환으로 교정 권장
R4. 설명형 금지 ("~할 수 있습니다", "~이라고 합니다") → 직격형 교정
    ※ 예외: ranking/money 타입의 구체 수치·사실 문장은 교정 금지
      ✅ 보존: "멀티태스킹 후 IQ 10p 떨어진다" / "수면 6시간이면 판단력 60% 저하"
      ❌ 교정 금지: 수치/사실 → 행동묘사형("~한다")으로 변환하지 말 것
R5. 금지어·비속어·법적 위험 요소 → 교정 또는 삭제
R6. scenes: 반드시 8개 영어 묘사 (부족하면 추가)
R7. t1, t2: 빈 값이면 topic에서 추출
R8. 비유·은유 금지: 추상 표현 → 직장인 일상 구체 표현
R9. 클리셰 금지: "상사 눈치", "퇴근 자책", "회의실 침묵" → 내면 묘사 교정
R10. content_type 규칙 준수:
    emotion: "너/넌/니" 포함 필수
    ranking: 숫자 포함 필수 / 각 항목은 수치·사실 기반 (행동묘사형 변환 금지)
    money: 숫자+기간 포함 필수
    quote: 통념 비틀기, 일반 명언 금지

[품질 지표] 교정 후 최종 기준, 각 10점 만점

scroll_stop_power:
  10: 보는 순간 손이 멈추는 수준
   9: 강한 단정형 hook, "너/넌/니" or 숫자 충격
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
   9: closing이 완벽한 관점 전환 — 보고 나서 생각이 달라짐
   8: closing이 takeaway를 주고 흐름이 자연스러움
   7: 관점 전환 있으나 약함
  6↓: 단순 종결 or 역설 말장난에 그침

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

def _gpt_draft(
    topic_seed:   dict,
    content_type: str,
    style:        str,
    client:       openai.OpenAI,
    prev_fail:    str = "",
) -> dict:
    """GPT-4o로 topic_seed를 각색한 대본 초안을 생성한다."""
    style_hint   = STYLE_INSTRUCTIONS.get(style, STYLE_INSTRUCTIONS["docsul"])
    type_rules   = _GPT_TYPE_RULES.get(content_type, _GPT_TYPE_RULES["emotion"])
    system_msg   = _GPT_SYSTEM_BASE + type_rules

    user_msg = _GPT_USER_TMPL.format(
        topic          = topic_seed["topic"],
        angle          = topic_seed["angle"],
        target_emotion = topic_seed["target_emotion"],
        content_type   = content_type,
        style_hint     = style_hint,
    )

    if prev_fail:
        user_msg += (
            "\n\n[이전 시도 실패 이유 — 이 부분을 반드시 고쳐서 재각색]\n" + prev_fail
        )

    resp = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_msg},
            {"role": "user",   "content": user_msg},
        ],
        temperature=0.9,
        response_format={"type": "json_object"},
    )

    raw    = resp.choices[0].message.content
    result = json.loads(raw)
    # topic / content_type은 GPT가 바꾸지 못하게 강제
    result["topic"]        = topic_seed["topic"]
    result["content_type"] = content_type
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
    # 원본 값 보존
    result["topic"]        = draft.get("topic", "")
    result["content_type"] = draft.get("content_type", "emotion")
    result.setdefault("mix", draft.get("mix", result["content_type"]))
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
        (Path(ep_dir) / "review_log.json").write_text(
            json.dumps(review_log, ensure_ascii=False, indent=2), encoding="utf-8"
        )


# ─────────────────────────────────────────────
# 퍼블릭 API
# ─────────────────────────────────────────────

def generate_best_script(
    topic_seed:   dict,
    content_type: str  = "emotion",
    ep_dir:       str | None = None,
    ep_id:        str  = "",
    style:        str  = "docsul",
) -> dict | None:
    """
    topic_seed 기반 GPT → Claude → Quality Gate 파이프라인.

    Parameters
    ----------
    topic_seed   : {"id", "topic", "angle", "target_emotion", ...}
                   topics.json에서 선택된 항목
    content_type : emotion | ranking | money | quote | hybrid
    ep_dir       : 저장 경로
    ep_id        : 에피소드 ID
    style        : docsul | janas | list | seulki

    Returns
    -------
    dict (PASS 대본) | None (3회 실패)
    """
    client_openai = openai.OpenAI(api_key=OPENAI_API_KEY)
    client_claude = anthropic.Anthropic(api_key=CLAUDE_API_KEY)

    if ep_dir:
        Path(ep_dir).mkdir(parents=True, exist_ok=True)

    gen_log: dict = {
        "ep_id":      ep_id,
        "topic_id":   topic_seed.get("id", ""),
        "topic":      topic_seed["topic"],
        "attempts":   [],
        "final_status": "FAIL",
    }
    prev_fail: str = ""

    for attempt in range(1, MAX_ATTEMPTS + 1):
        log.info(
            "[시도 %d/%d] ep=%s type=%s topic='%s'",
            attempt, MAX_ATTEMPTS, ep_id or "-", content_type, topic_seed["topic"],
        )

        # ① GPT 각색
        draft = _gpt_draft(topic_seed, content_type, style, client_openai, prev_fail)

        # ② Claude 검수
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
            "content_type": content_type,
            "final_status": gate.final_status,
            "fail_reason":  gate.fail_reason,
        })

        if gate.final_status == "PASS":
            reviewed.update({
                "ep_id":          ep_id,
                "topic_id":       topic_seed.get("id", ""),
                "content_type":   content_type,
                "topic":          topic_seed["topic"],
                "angle":          topic_seed.get("angle", ""),
                "target_emotion": topic_seed.get("target_emotion", ""),
                "view_score":     gate.view_score,
                "final_status":   "PASS",
                "_meta": {
                    "ep_id":          ep_id,
                    "topic_id":       topic_seed.get("id", ""),
                    "topic":          topic_seed["topic"],
                    "angle":          topic_seed.get("angle", ""),
                    "target_emotion": topic_seed.get("target_emotion", ""),
                    "style":          style,
                    "content_type":   content_type,
                    "generated_at":   datetime.now().isoformat(),
                    "verdict":        review_log.get("verdict", "UNKNOWN"),
                    "scores":         scores,
                    "view_score":     gate.view_score,
                    "attempts":       attempt,
                },
            })

            gen_log.update({
                "final_status": "PASS",
                "content_type": content_type,
                "view_score":   gate.view_score,
            })

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
        log.warning("[시도 %d 실패] %s", attempt, gate.fail_reason)

    log.error("3회 모두 실패 — EP SKIP | ep_id='%s' topic='%s'",
              ep_id, topic_seed["topic"])
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

    p = argparse.ArgumentParser(description="대본 단독 생성 테스트 (v3.1 seed pool)")
    p.add_argument("--topic-id",    required=True,  help="topics.json의 id (예: emotion_001)")
    p.add_argument("--topics-file", default="topics.json")
    p.add_argument("--style",       default="docsul",
                   choices=["docsul", "janas", "list", "seulki"])
    p.add_argument("--ep-id",       default="test_001")
    p.add_argument("--ep-dir",      default=None)
    args = p.parse_args()

    with open(args.topics_file, encoding="utf-8") as f:
        all_topics = json.load(f)

    seed = next((t for t in all_topics if t["id"] == args.topic_id), None)
    if not seed:
        print(f"topic_id '{args.topic_id}' 를 topics.json에서 찾을 수 없음")
        raise SystemExit(1)

    result = generate_best_script(
        topic_seed=seed,
        content_type=seed["content_type"],
        ep_dir=args.ep_dir,
        ep_id=args.ep_id,
        style=args.style,
    )
    if result:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("3회 시도 모두 실패")

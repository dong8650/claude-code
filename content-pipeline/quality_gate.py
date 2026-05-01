"""
quality_gate.py — Script Quality Gate v3
=========================================
목표: "조회수 1만 이상 가능성 있는 대본만 통과"

HARD GATE : 수치 기반 즉시 FAIL
SOFT GATE : Claude 의미 판단 (타입 검증 + 시청 가능성)
"""

import json
import logging
from dataclasses import asdict, dataclass
from pathlib import Path

import anthropic

log = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# HARD GATE 임계값 (v3: 7/7/6)
# ─────────────────────────────────────────────
HARD = {
    "hook_length_max":        12,
    "script_length_max":     120,
    "sentence_count_max":      5,
    "closing_length_max":     15,
    "scroll_stop_power_min":   7,
    "emotional_attack_min":    7,
    "repeat_value_min":        6,
}


# ─────────────────────────────────────────────
# 결과 데이터클래스
# ─────────────────────────────────────────────
@dataclass
class GateResult:
    content_type:         str  = ""
    hook_length:          int  = 0
    script_length:        int  = 0
    sentence_count:       int  = 0
    closing_length:       int  = 0
    scroll_stop_power:    int  = 0
    emotional_attack:     int  = 0
    repeat_value:         int  = 0
    view_score:           int  = 0
    semantic_hook_pass:   bool = False
    semantic_body_pass:   bool = False
    flow_pass:            bool = False
    repeat_pass:          bool = False
    viewability_pass:     bool = False
    final_status:         str  = "FAIL"
    fail_reason:          str  = ""


# ─────────────────────────────────────────────
# SOFT GATE 프롬프트
# ─────────────────────────────────────────────
_SOFT_PROMPT = """\
유튜브 쇼츠 대본 바이럴 가능성 심사 전문가입니다.
채널 대상: 30~40대 직장인 / 목표: 조회수 1만 이상

[대본]
content_type : {content_type}
hook         : {hook}
body         : {body}
closing      : {closing}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[A] 공통 4가지 기준 평가
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. semantic_hook_pass
   PASS: 첫 1초 안에 멈추게 하는 충격 — 아래 중 하나 충족:
         ① 정체성 단정 ("넌 겁쟁이야", "니가 원인이야")
         ② 숨겨진 사실 폭로 ("이 3가지가 망친다", "퇴직금 절반 증발")
         ③ 통념 역전 ("노력하면 더 망한다", "착한 게 패인이었다")
   ranking/money 타입: 숫자 포함 강한 사실 선언이면 PASS
   FAIL: 추상 표현, 일반 경고("~에 주의하세요"), 조언형

2. semantic_body_pass
   emotion/quote 타입:
     PASS: 현실 공감 1문장 이상 + 반전 문장 1문장 이상
     FAIL: 전부 설명형 / 클리셰(상사 눈치, 퇴근 자책, 회의실 침묵)
   ranking/money 타입:
     PASS: 각 항목이 구체적 사실 or 수치 기반 / 최소 1문장 예상 밖 충격 포함
     FAIL: 전부 "~하면 ~된다" 조언형 / 클리셰 / 추상 표현만 있음
   ※ ranking/money는 항목 나열 구조 자체는 허용. 내용이 충격적이면 PASS.

3. flow_pass
   PASS: Hook → Body → Closing 흐름 자연스럽고 맥락 연결됨
   FAIL: 뜬금 결론, 흐름 단절

4. repeat_pass
   PASS: Closing이 Hook의 핵심 단어/개념을 역설적으로 뒤집음
         아래 패턴 중 하나면 PASS:
         ① 부정→긍정: "망친다" → "답이다" / "증발" → "기회였다" ✅
         ② 낙인→역전: "겁쟁이야" → "겁쟁이가 살아남는다" ✅
         ③ 비꼼→현실: "착하게 살았냐" → "착한 게 패인이었다" ✅
         ④ 행동→본질: "해봤자야" → "해본 자만 안다" ✅
   FAIL: 단순 반복(같은 단어 재사용), 행동 명령("해라","시작해"), 질문형("몇 개 해당되나")

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[B] content_type 규칙 검증
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

content_type에 맞는 규칙 1개만 적용:

emotion : 정체성 공격 필수 / "너/넌/니" 포함 / 클리셰 금지
ranking : 숫자(TOP3·TOP5) 포함 / 궁금증 유발 / 충격 요소 1개 이상
money   : 숫자+기간 필수 / 현실 수치 / 마지막 감정 압박
quote   : 일반 명언 금지 / 현실 비틀기 필수 (노력하면 된다 → 노력하면 더 망한다)
hybrid  : 최소 2개 타입 결합 확인

type_rule_pass: 위 규칙 충족 시 true

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[C] 조회수 1만 가능성 판단 (핵심)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

아래 3가지 기준으로 종합 판단:
  - 기분 나쁘지만 맞는 말인가?
  - 댓글 달고 싶어지는가?
  - 나한테 하는 말 같은가?

view_score: 1~10 (7 이상이면 1만 조회 가능성 있음)
viewability_pass: view_score ≥ 7이면 true

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
JSON으로만 응답 (마크다운 없이):
{{
  "semantic_hook_pass":   true,
  "semantic_hook_reason": "한 줄",
  "semantic_body_pass":   true,
  "semantic_body_reason": "한 줄",
  "flow_pass":            true,
  "flow_reason":          "한 줄",
  "repeat_pass":          true,
  "repeat_reason":        "한 줄",
  "type_rule_pass":       true,
  "type_rule_reason":     "한 줄",
  "view_score":           8,
  "viewability_pass":     true,
  "viewability_reason":   "한 줄"
}}\
"""

# ─────────────────────────────────────────────
# DROP 규칙 (즉시 FAIL)
# ─────────────────────────────────────────────
CLICHES = [
    "상사 눈치", "퇴근 후 후회", "퇴근 자책", "회의실 침묵",
    "잘리고 싶지 않아서", "회의실에서",
]

def _check_cliche(script: dict) -> str | None:
    body = script.get("script_ko", "")
    for c in CLICHES:
        if c in body:
            return f"클리셰 감지: '{c}'"
    return None


# ─────────────────────────────────────────────
# 내부 함수
# ─────────────────────────────────────────────

def _measure(script: dict, scores: dict) -> GateResult:
    hook    = script.get("hook", "")
    body    = script.get("script_ko", "")
    closing = script.get("closing_ko", "")
    sentences = [s.strip() for s in body.replace("。", ".").split(".") if s.strip()]

    return GateResult(
        content_type       = script.get("content_type", ""),
        hook_length        = len(hook.replace(" ", "")),
        script_length      = len(body.replace(" ", "")),
        sentence_count     = len(sentences),
        closing_length     = len(closing.replace(" ", "")),
        scroll_stop_power  = scores.get("scroll_stop_power", 0),
        emotional_attack   = scores.get("emotional_attack",  0),
        repeat_value       = scores.get("repeat_value",       0),
    )


def _hard_check(r: GateResult) -> tuple[bool, str]:
    checks = [
        (r.hook_length       > HARD["hook_length_max"],
         f"hook {r.hook_length}자 > {HARD['hook_length_max']}자"),
        (r.script_length     > HARD["script_length_max"],
         f"script {r.script_length}자 > {HARD['script_length_max']}자"),
        (r.sentence_count    > HARD["sentence_count_max"],
         f"문장 {r.sentence_count}개 > {HARD['sentence_count_max']}개"),
        (r.closing_length    > HARD["closing_length_max"],
         f"closing {r.closing_length}자 > {HARD['closing_length_max']}자"),
        (r.scroll_stop_power < HARD["scroll_stop_power_min"],
         f"scroll_stop_power {r.scroll_stop_power} < {HARD['scroll_stop_power_min']}"),
        (r.emotional_attack  < HARD["emotional_attack_min"],
         f"emotional_attack {r.emotional_attack} < {HARD['emotional_attack_min']}"),
        (r.repeat_value      < HARD["repeat_value_min"],
         f"repeat_value {r.repeat_value} < {HARD['repeat_value_min']}"),
    ]
    for failed, reason in checks:
        if failed:
            return False, reason
    return True, ""


def _soft_check(script: dict, client: anthropic.Anthropic) -> dict:
    prompt = _SOFT_PROMPT.format(
        content_type = script.get("content_type", ""),
        hook         = script.get("hook", ""),
        body         = script.get("script_ko", ""),
        closing      = script.get("closing_ko", ""),
    )
    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=768,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = msg.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()
    return json.loads(raw)


def _save(result: GateResult, ep_dir: str | None) -> None:
    log.info(
        "[QGate] %s | type=%-8s | hook=%s script=%s sent=%s closing=%s "
        "ssp=%s emo=%s rep=%s view=%s | "
        "hook=%s body=%s flow=%s repeat=%s type=%s view=%s",
        result.final_status, result.content_type,
        result.hook_length, result.script_length,
        result.sentence_count, result.closing_length,
        result.scroll_stop_power, result.emotional_attack,
        result.repeat_value, result.view_score,
        result.semantic_hook_pass, result.semantic_body_pass,
        result.flow_pass, result.repeat_pass,
        "?", result.viewability_pass,
    )
    if result.final_status == "FAIL":
        log.warning("[QGate] 실패: %s", result.fail_reason)
    if ep_dir:
        out = Path(ep_dir) / "script_review.json"
        with open(out, "w", encoding="utf-8") as f:
            json.dump(asdict(result), f, ensure_ascii=False, indent=2)


# ─────────────────────────────────────────────
# 퍼블릭 API
# ─────────────────────────────────────────────

def run_gate(
    script:  dict,
    scores:  dict,
    client:  anthropic.Anthropic,
    ep_dir:  str | None = None,
) -> GateResult:
    """Hard Gate → DROP 규칙 → Soft Gate 순서로 실행."""
    r = _measure(script, scores)

    # ─ HARD GATE ─
    hard_ok, hard_fail = _hard_check(r)
    if not hard_ok:
        r.final_status = "FAIL"
        r.fail_reason  = f"[HARD] {hard_fail}"
        _save(r, ep_dir)
        return r

    # ─ DROP 규칙 ─
    cliche = _check_cliche(script)
    if cliche:
        r.final_status = "FAIL"
        r.fail_reason  = f"[DROP] {cliche}"
        _save(r, ep_dir)
        return r

    # ─ SOFT GATE ─
    soft = _soft_check(script, client)

    r.semantic_hook_pass = soft.get("semantic_hook_pass", False)
    r.semantic_body_pass = soft.get("semantic_body_pass", False)
    r.flow_pass          = soft.get("flow_pass",          False)
    r.repeat_pass        = soft.get("repeat_pass",        False)
    r.view_score         = soft.get("view_score",         0)
    r.viewability_pass   = soft.get("viewability_pass",   False)

    fails = []
    if not r.semantic_hook_pass:
        fails.append(f"[HOOK] {soft.get('semantic_hook_reason', '')}")
    if not r.semantic_body_pass:
        fails.append(f"[BODY] {soft.get('semantic_body_reason', '')}")
    if not r.flow_pass:
        fails.append(f"[FLOW] {soft.get('flow_reason', '')}")
    if not r.repeat_pass:
        fails.append(f"[REPEAT] {soft.get('repeat_reason', '')}")
    if not soft.get("type_rule_pass", False):
        fails.append(f"[TYPE:{r.content_type}] {soft.get('type_rule_reason', '')}")
    if not r.viewability_pass:
        fails.append(f"[VIEW:{r.view_score}] {soft.get('viewability_reason', '')}")

    if fails:
        r.final_status = "FAIL"
        r.fail_reason  = " / ".join(fails)
    else:
        r.final_status = "PASS"

    _save(r, ep_dir)
    return r


def recheck_v3(
    script: dict,
    scores: dict,
    client: anthropic.Anthropic,
    ep_dir: str | None = None,
) -> GateResult:
    """기존 PASS 대본을 v3 기준으로 재검수한다."""
    log.info("[V3 재검수] 기존 스크립트 검사 중...")
    return run_gate(script, scores, client, ep_dir)

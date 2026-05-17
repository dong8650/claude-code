"""
quality_gate.py — Script Quality Gate v4
=========================================
목표: "매일의 설계 채널답고, 신뢰할 수 있고, 사람이 편집한 흔적이 있는 대본만 통과"

v4 변경 (v3 → v4):
  - scroll_stop_power: 공격형 기준 → 현실 직격형 기준 (최솟값 6으로 낮춤)
  - emotional_attack → practical_value: 감정 공격 → 보고 나서 정리되는가
  - repeat_value → identity_fit: 저장 유도 → 채널 정체성 + 구독 이유
  - SOFT GATE: identity_fit, trust_score, practical_value, human_feel, editorial_intent 추가
  - CTA/협박형 closing → 설계 원칙형으로 평가 기준 변경

HARD GATE : 수치 기반 즉시 FAIL
SOFT GATE : Claude 의미 판단 (채널 정체성 + 신뢰도 + 실용 가치 + 사람 냄새)
"""

import json
import logging
from dataclasses import asdict, dataclass
from pathlib import Path

import anthropic

log = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# HARD GATE 임계값 (v4: 6/6/5 — 현실 설계형 기준)
# ─────────────────────────────────────────────
HARD = {
    "hook_length_max":        14,   # v3 12 → v4 14 (설계 원칙형 hook은 조금 더 필요)
    "script_length_max":     140,   # v4.5: 구체 시간/숫자 + 문장 리듬 여지
    "sentence_count_max":      5,
    "closing_length_max":     24,   # v3 15 → v4 24 (설계 원칙형 closing)
    "scroll_stop_power_min":   6,   # v3 7 → v4 6 (공격형 아닌 현실 직격형도 OK)
    "practical_value_min":     6,   # 신규 (emotional_attack_min 대체)
    "identity_fit_min":        5,   # 신규 (repeat_value_min 대체)
    # 기존 호환 필드
    "emotional_attack_min":    6,
    "repeat_value_min":        5,
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
    practical_value:      int  = 0   # v4 신규 (emotional_attack 대체)
    identity_fit:         int  = 0   # v4 신규 (repeat_value 대체)
    # 기존 호환
    emotional_attack:     int  = 0
    repeat_value:         int  = 0
    view_score:           int  = 0
    semantic_hook_pass:   bool = False
    semantic_body_pass:   bool = False
    flow_pass:            bool = False
    trust_pass:           bool = False   # v4 신규
    human_feel_pass:      bool = False   # v4 신규
    editorial_pass:       bool = False   # v4.1 신규
    viewability_pass:     bool = False
    final_status:         str  = "FAIL"
    fail_reason:          str  = ""


# ─────────────────────────────────────────────
# SOFT GATE 프롬프트
# ─────────────────────────────────────────────
_SOFT_PROMPT = """\
유튜브 쇼츠 대본 품질 심사 전문가입니다.
채널: 매일의 설계 | 대상: 30~40대 직장인 | 채널 방향: 현실 설계형

[대본]
content_type : {content_type}
hook         : {hook}
body         : {body}
closing      : {closing}
editor_point_of_view : {editor_point_of_view}
one_argument         : {one_argument}
real_scene           : {real_scene}
visual_intention     : {visual_intention}
human_pause          : {human_pause}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[A] 채널 정체성 + 사람 냄새 평가
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. semantic_hook_pass
   PASS: 첫 1초 안에 멈추게 하는 현실 문장 — 아래 중 하나 충족:
         ① 현실 직격 ("착한 사람이 먼저 지친다", "월급의 절반이 사라지는 곳")
         ② 구체 상황 ("퇴사보다 먼저 봐야 할 신호", "10년 모아도 집 못 사는 이유")
         ③ 궁금증 유발 ("나만 손해 보는 느낌의 정체", "번아웃과 그냥 지침의 차이")
   FAIL: 추상 표현, 조언형, 정체성 공격형 ("너는 ~야")

2. semantic_body_pass
   PASS: 구체적 장면/수치 1개 이상 + 구조 설명 (개인 탓 X) + 시청자가 자기 상황으로 느낌
   FAIL: 전부 설명형 / 클리셰(상사 눈치, 퇴근 자책) / 추상 표현만 있음

3. flow_pass
   PASS: Hook → Body → Closing 흐름 자연스럽고 맥락 연결됨
   FAIL: 뜬금 결론, 흐름 단절

4. trust_pass (신규 v4)
   PASS: 과장·가짜 통계·근거 없는 수치 없음. 현실 기반 추정 가능한 내용.
   FAIL: "연구에 따르면" 류의 출처 불명 통계 / 선정적 과장 / 가짜 사례

5. human_feel_pass (신규 v4 — 사람 냄새)
   PASS: 아래 중 2개 이상 충족:
         ① 구체적 시간/장소/숫자가 있음 ("점심 11분", "월 30만원", "일요일 밤 11시")
         ② 문장 길이가 다양함 (짧은 문장 + 18자 이상 문장 혼합)
         ③ 직접 경험/관찰한 것처럼 쓰여짐
         ④ 완전히 해결된 척 안 함 (답을 강요하지 않음)
   FAIL: 모든 문장이 같은 길이 / 전형적인 AI 패턴 ("~합니다. ~합니다. ~합니다.")

6. editorial_pass (신규 v4.1 — 편집자 개입 흔적)
   PASS: 아래 4개 모두 충족
         ① editor_point_of_view가 "왜 이 주제를 골랐는지"를 말함
         ② one_argument가 하나의 주장으로 좁혀져 있음
         ③ real_scene이 실제 사람이 고른 구체 장면임
         ④ visual_intention이 대표 이미지가 아니라 편집 의도를 설명함
   FAIL: 빈 값 / 일반론 / 자동 생성 메타 설명 / "좋은 영상 만들기" 같은 추상 표현

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[B] content_type 규칙 검증
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

work  : 일의 설계축 / 경계선·번아웃·직장 구조 / closing은 설계 원칙
money : 돈의 설계축 / 구체 수치 포함 / closing은 설계 원칙
그 외 : work 방향으로 판단

type_rule_pass: closing이 설계 원칙으로 끝나면 PASS (CTA/저장유도면 FAIL)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[C] 종합 시청 가능성 판단
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

아래 3가지 기준으로 판단:
  - 보고 나서 하나가 정리되는가?
  - 이 채널 또 봐야겠다는 느낌이 드는가?
  - 나한테 하는 말 같은가?

view_score: 1~10 (7 이상이면 구독 이유가 생기는 수준)
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
  "trust_pass":           true,
  "trust_reason":         "한 줄",
  "human_feel_pass":      true,
  "human_feel_reason":    "한 줄",
  "editorial_pass":       true,
  "editorial_reason":     "한 줄",
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

    practical = scores.get("practical_value", scores.get("emotional_attack", 0))
    identity  = scores.get("identity_fit",    scores.get("repeat_value",     0))

    return GateResult(
        content_type       = script.get("content_type", ""),
        hook_length        = len(hook.replace(" ", "")),
        script_length      = len(body.replace(" ", "")),
        sentence_count     = len(sentences),
        closing_length     = len(closing.replace(" ", "")),
        scroll_stop_power  = scores.get("scroll_stop_power", 0),
        practical_value    = practical,
        identity_fit       = identity,
        emotional_attack   = practical,   # 호환
        repeat_value       = identity,    # 호환
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
        (r.practical_value   < HARD["practical_value_min"],
         f"practical_value {r.practical_value} < {HARD['practical_value_min']}"),
        (r.identity_fit      < HARD["identity_fit_min"],
         f"identity_fit {r.identity_fit} < {HARD['identity_fit_min']}"),
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
        editor_point_of_view = script.get("editor_point_of_view", ""),
        one_argument         = script.get("one_argument", ""),
        real_scene           = script.get("real_scene", ""),
        visual_intention     = script.get("visual_intention", ""),
        human_pause          = script.get("human_pause", ""),
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
        "ssp=%s pv=%s ifit=%s view=%s | "
        "hook=%s body=%s flow=%s trust=%s feel=%s edit=%s view=%s",
        result.final_status, result.content_type,
        result.hook_length, result.script_length,
        result.sentence_count, result.closing_length,
        result.scroll_stop_power, result.practical_value,
        result.identity_fit, result.view_score,
        result.semantic_hook_pass, result.semantic_body_pass,
        result.flow_pass, result.trust_pass,
        result.human_feel_pass, result.editorial_pass,
        result.viewability_pass,
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
    r.trust_pass         = soft.get("trust_pass",         True)   # 기본 PASS (보수적 운영)
    r.human_feel_pass    = soft.get("human_feel_pass",    False)
    r.editorial_pass     = soft.get("editorial_pass",     False)
    r.view_score         = soft.get("view_score",         0)
    r.viewability_pass   = soft.get("viewability_pass",   False)

    fails = []
    if not r.semantic_hook_pass:
        fails.append(f"[HOOK] {soft.get('semantic_hook_reason', '')}")
    if not r.semantic_body_pass:
        fails.append(f"[BODY] {soft.get('semantic_body_reason', '')}")
    if not r.flow_pass:
        fails.append(f"[FLOW] {soft.get('flow_reason', '')}")
    if not r.trust_pass:
        fails.append(f"[TRUST] {soft.get('trust_reason', '')}")
    if not r.human_feel_pass:
        fails.append(f"[HUMAN] {soft.get('human_feel_reason', '')}")
    if not r.editorial_pass:
        fails.append(f"[EDITORIAL] {soft.get('editorial_reason', '')}")
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

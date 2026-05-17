"""
generate_script.py
==================
대본 생성 파이프라인 v4.1 — 현실 설계형 / 편집자 개입 시스템

채널: 매일의 설계 | content_type: work(일의 설계) / money(돈의 설계)

Flow:
  1. GPT-4o: topic_seed + persona + structure_type + scene_hint 기반 대본 초안
  2. Claude: 규칙 검수 + 자동 교정 + 품질 점수
  3. Quality Gate: Hard → DROP → Soft (채널 정체성 + 신뢰도 + 실용 가치)
  4. FAIL 시 동일 topic_seed, 다른 접근각으로 재시도 (최대 3회)

핵심 변경 (v3.1 → v4.0):
  - content_type: emotion/ranking/quote → work/money
  - persona 시스템: senior_colleague / honest_observer / same_boat
  - structure_type 시스템: story / observation / question / reversal / fact
  - scene_hint: 구체적 현실 장면 주입으로 AI 냄새 제거
  - editorial fields: 사람이 주제를 고르고 편집한 판단 흔적을 대본에 고정
  - closing: CTA 유도 → 설계 원칙으로 마무리

script.json 필수 필드:
  ep_id, topic_id, content_type, topic, angle, target_emotion,
  hook, script_ko, closing_ko, editor_point_of_view, one_argument,
  real_scene, visual_intention, human_pause, view_score, final_status
"""

import json
import logging
from datetime import datetime
from pathlib import Path

import anthropic
import openai

import sys; sys.path.insert(0, "/root/content/runtime/mindset")
from config import CLAUDE_API_KEY, OPENAI_API_KEY
from quality_gate import run_gate

MAX_ATTEMPTS = 3

log = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# 페르소나 시스템 (사람 냄새의 핵심)
# ─────────────────────────────────────────────
PERSONA_INSTRUCTIONS: dict[str, str] = {
    "senior_colleague": (
        "10년 차 직장인이 후배에게 말하듯. 경험 기반, 담담하고 구체적. "
        "'나도 그랬어요'가 깔린 톤. 설명이 아니라 경험 공유. 가르치지 않음."
    ),
    "honest_observer": (
        "구조가 보이는 관찰자처럼. 개인 탓이 아닌 구조로 설명. "
        "날카롭지만 모욕하지 않음. 냉정하지만 차갑지 않음."
    ),
    "same_boat": (
        "같이 고민하는 동료처럼. 완전히 해결한 척 안 함. "
        "공감이 먼저, 조언이 나중. '아직도 모르겠는데'가 있는 톤."
    ),
    # 기존 호환
    "docsul": "독설형: 날카롭고 직격적인 어조. 듣기 불편하지만 공감되는 말투. 주어 생략, 단문 선호.",
    "janas":  "일화형: 실제 대화/상황처럼 장면을 제시. '그 순간' '누군가가 말했다' 도입부 사용.",
    "list":   "리스트형: '~하는 N가지' 구조. 각 항목 짧고 임팩트 있게. 번호 없이 흐름으로 연결.",
    "seulki": "감성형: 따뜻하고 울림 있는 어조. 여성 화자 느낌. 감정 공명 극대화.",
}

# ─────────────────────────────────────────────
# 구조 시스템 (형식 다양화)
# ─────────────────────────────────────────────
STRUCTURE_INSTRUCTIONS: dict[str, str] = {
    "story":       "'어느 날' / '3년 전' / '한 번은' 같은 구체적 상황으로 시작. 시청자가 장면을 떠올리게.",
    "observation": "요즘 주변에서 보이는 패턴 제시. '보면 ~한 사람들이 있다' 흐름. 관찰한 것처럼.",
    "question":    "시청자 스스로 묻게 만드는 구조. '왜 우리는' / '이게 왜 그럴까' 형식.",
    "reversal":    "당연하게 여긴 것을 뒤집기. '~라고 생각하지만 실제로는' 구조. 반전 후 원칙.",
    "fact":        "구체적 수치나 현실 상황 직격. 숫자/시간/장면으로 시작. 설명 아닌 현실 제시.",
}

# 기존 호환용 (style 파라미터를 persona로 폴백)
STYLE_INSTRUCTIONS = PERSONA_INSTRUCTIONS

# ─────────────────────────────────────────────
# content_type별 규칙 (v4.0 — 현실 설계형)
# ─────────────────────────────────────────────
_GPT_SYSTEM_BASE = """\
당신은 유튜브 쇼츠 대본 작가입니다.
채널: 매일의 설계 | 대상: 30~40대 직장인

채널의 역할: "30~40대의 일·돈·몸을 무너지기 전에 다시 설계하는 채널"
  - 시청자의 현실을 과장 없이 짚는다
  - 문제를 개인 탓으로 몰지 않고 구조로 설명한다
  - 마지막에는 하나의 설계 원칙을 남긴다
  - 세게 때리는 것이 아니라 정리해주는 것

중요: 당신의 역할은 주제를 새로 만드는 것이 아니다.
검증된 topic과 angle을 받아서 scene_hint가 살아있는 대본으로 만드는 것이다.
target_emotion이 대본 전체를 관통해야 한다.

[편집자 개입 원칙]
  AI가 정보를 요약한 영상처럼 보이면 실패다.
  사람이 이 주제를 왜 골랐고, 어떤 장면을 왜 보여주는지 판단한 흔적을 남겨야 한다.
  모든 대본은 아래 5가지를 먼저 정한 뒤 작성한다.
    1) editor_point_of_view: 이 주제를 지금 다루는 편집자 관점
    2) one_argument: 이번 영상에서 딱 하나만 말할 주장
    3) real_scene: 시청자가 실제로 본 적 있는 장면
    4) visual_intention: 왜 이 이미지/장면을 보여주는지
    5) human_pause: 자막이나 내레이션에서 일부러 한 박자 쉬는 위치

[절대 금지]
  정체성 공격: "너는 겁쟁이야", "니가 문제야", "당신은 ~한 사람"
  협박형 CTA: "저장 안 하면 또 당한다", "지금 퍼뜨려야 함"
  클리셰: "상사 눈치", "퇴근 자책", "회의실 침묵", "잘리고 싶지 않아서"
  추상 표현: "내면의 폭풍", "불씨가 태양 된다"
  설명형: "~이라고 합니다", "~할 수 있습니다"
  공포 과장: 근거 없는 수치, 가짜 통계\
"""

_GPT_TYPE_RULES = {
    "work": """\

━━━━ [content_type: work] 일의 설계형 ━━━━
HOOK: 6~14자, 현실 문제를 콕 집는 문장 (결론 X, 궁금증·현실 O)
  PASS ✅ "착한 사람이 먼저 지친다" / "경계선 없이 친절한 사람의 결말"
  PASS ✅ "퇴사보다 먼저 봐야 할 신호" / "회사에서 나만 손해 보는 느낌의 정체"
  FAIL ❌ "너는 겁쟁이야" / "니가 문제야" 같은 정체성 공격
  FAIL ❌ 결론을 먼저 말하는 hook ("~하면 됩니다")

BODY: 3~5문장, 총 60~120자, 각 문장 20자 이하
  scene_hint 기반으로 구체적 장면/상황 묘사
  문장1: 현실 상황 구체 묘사 (정확한 시간/숫자 1개 필수: "새벽 1시", "오후 4시", "3번째 보고서")
  문장2: 왜 그런지 구조 설명 (개인 탓 X)
  문장3~4: 시청자가 "내 얘기다" 느끼는 구체성
  마지막: 하나의 설계 원칙 (명령이 아닌 관점)

CLOSING: 최대 24자, 설계 원칙으로 마무리 (CTA 금지)
  PASS ✅ "경계선이 친절보다 먼저입니다" / "말보다 구조가 나를 지킵니다"
  PASS ✅ "퇴사보다 구조를 먼저 봐야 합니다" / "일보다 나를 먼저 설계해야 합니다"
  FAIL ❌ "저장해두세요" / "공유해야 함" / "구독하세요"\
""",
    "money": """\

━━━━ [content_type: money] 돈의 설계형 ━━━━
HOOK: 6~14자, 구체적 숫자 or 현실 상황 직격
  PASS ✅ "월급의 절반이 사라지는 곳" / "10년 모아도 집 못 사는 이유"
  PASS ✅ "퇴직금이 실제로 주는 것" / "고정비가 늘면 노력이 먼저 무너진다"
  FAIL ❌ 숫자 없는 막연한 hook
  FAIL ❌ 공포 마케팅형 ("이러면 망합니다")

BODY: 3~5문장, 총 60~120자, 각 문장 20자 이하
  scene_hint 기반으로 구체적 숫자/상황 제시
  문장1~2: 구체적 수치나 현실 상황 직격 (정확한 금액/시간/횟수 1개 필수)
  문장3: 왜 그런지 구조 설명
  문장4: 시청자 현실과 연결
  마지막: 하나의 설계 원칙 (두려움이 아닌 방향)

CLOSING: 최대 24자, 설계 원칙으로 마무리 (CTA 금지)
  PASS ✅ "먼저 새는 곳부터 막아야 합니다" / "숫자를 먼저 봐야 설계됩니다"
  PASS ✅ "투자보다 구조가 먼저입니다" / "수입보다 지출 구조를 먼저 보세요"
  FAIL ❌ "저장 안 하면 또 당한다" / 불안만 남기는 마무리\
""",
    # 기존 호환 (서버에 구 topics.json이 있을 경우 대비)
    "emotion": """\

━━━━ [content_type: emotion → work 방향 적용] ━━━━
work 타입 규칙으로 처리합니다. 정체성 공격 금지.\
""",
    "ranking": """\

━━━━ [content_type: ranking → work 방향 적용] ━━━━
work 타입 규칙으로 처리합니다. 목록 구조는 유지하되 CTA 금지.\
""",
    "quote": """\

━━━━ [content_type: quote → work 방향 적용] ━━━━
work 타입 규칙으로 처리합니다. 설계 원칙으로 마무리.\
""",
    "hybrid": """\

━━━━ [content_type: hybrid → work 방향 적용] ━━━━
work 타입 규칙으로 처리합니다.\
""",
}

_GPT_USER_TMPL = """\
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[대본 대상 — 변경 금지]
topic          : {topic}
angle          : {angle}
target_emotion : {target_emotion}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
content_type   : {content_type}
axis           : {axis}

[사람 냄새 시스템]
persona        : {persona_hint}
structure_type : {structure_hint}
scene_hint     : {scene_hint}
  → scene_hint의 장면을 hook 또는 body에 구체적으로 활용할 것
  → 추상적인 묘사 금지. 시청자가 떠올릴 수 있는 구체적 장면으로.

[편집자 개입 시스템 — 반드시 먼저 설계]
editor_point_of_view:
  이 주제를 왜 지금 골랐는지, 편집자가 어떤 관점으로 보는지 1문장.
one_argument:
  이번 영상에서 딱 하나만 말할 주장. 여러 조언 금지.
real_scene:
  scene_hint를 바탕으로 실제 사람이 찍거나 고른 듯한 현실 장면 1개.
visual_intention:
  그 장면을 보여주는 이유. 예쁜 대표 이미지 금지, 편집 의도 명시.
human_pause:
  대본에서 한 박자 멈출 문장 뒤의 짧은 메모. 예: "첫 문장 뒤 0.4초 정지"

[작성 지침]
1. topic을 다른 주제로 바꾸지 말 것
2. angle이 대본의 핵심 관점이다
3. target_emotion({target_emotion})이 대본 전체에 흘러야 한다
4. persona 톤을 유지하되 — persona가 직접 경험한 것처럼 쓸 것
5. structure_type 방식으로 전개할 것
6. body에서 개인 탓이 아닌 구조로 설명할 것
7. closing은 설계 원칙 — CTA나 저장 유도 금지
8. editor_point_of_view / one_argument / real_scene / visual_intention / human_pause를 빈 값으로 두지 말 것

[body 필수]
3~5문장 / 총 70~125자 / 설명형·클리셰·비유 완전 금지
정확한 시간·숫자·횟수 중 1개 이상 필수 ("밤새" 같은 막연한 표현 금지)
문장 길이는 일부러 섞을 것: 짧은 문장 1개 + 18~28자 문장 1개 이상
직접 관찰한 듯한 장면 1개 필수 ("내가 본 건"을 쓰지 말고 장면으로 보여줄 것)

[응답 JSON — 마크다운·코드블록 없이]
{{
  "topic":        "{topic}",
  "content_type": "{content_type}",
  "axis":         "{axis}",
  "pattern_type": "<현실 설계 | 구조 분석 | 경험 공유 | 관점 전환>",
  "editor_point_of_view": "<편집자가 이 주제를 고른 이유와 관점 1문장>",
  "one_argument": "<이번 영상에서 딱 하나만 말할 주장 1문장>",
  "real_scene": "<실제 사람이 고른 듯한 구체적 현실 장면 1개>",
  "visual_intention": "<왜 이 장면을 보여주는지 편집 의도 1문장>",
  "human_pause": "<자막/내레이션에서 일부러 쉬어갈 위치 1개>",
  "hook":         "<14자 이하, 현실 문제를 콕 집는 문장>",
  "script_ko":    "<body 문장들. 마침표로 끝냄. 개인 탓 X, 구조 설명 O>",
  "closing_ko":   "<24자 이하, 설계 원칙으로 마무리 — CTA 금지>",
  "t1":           "<영상 상단 제목 1줄 — topic 기반>",
  "t2":           "<영상 상단 제목 2줄 (핵심 키워드, 주황색)>",
  "scenes": [
    "<scene1 영어 묘사, warm cinematic 9:16, everyday Korean workplace/life scene, no face>",
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
R1. hook: 공백 제외 14자 이내 — 초과 시 핵심만 남겨 단축
R2. script_ko: 반드시 3~5문장 / 총 70~125자 / 각 문장 28자 이하
    문장 부족 시 추가, 글자 부족 시 내용 보강
    정확한 시간·숫자·횟수 중 1개 이상 필수 ("새벽 1시", "오후 4시", "월 30만원", "3번째 보고서")
    문장 길이 다양성 필수: 짧은 문장 1개 + 18~28자 문장 1개 이상
R3. closing_ko: 공백 포함 최대 24자 이내
    ★ 설계 원칙형 보호 (절대 교정 금지):
      ✅ "경계선이 친절보다 먼저입니다"
      ✅ "먼저 새는 곳부터 막아야 합니다"
      ✅ "구조를 먼저 봐야 설계됩니다"
    ★ 교정 필수 (CTA/협박형 → 설계 원칙형으로):
      ❌ "저장 안 하면 또 당한다" → 설계 원칙으로 교정
      ❌ "지금 주변에 퍼뜨려야 함" → 설계 원칙으로 교정
      ❌ "이 영상 본 사람만 안다" → 설계 원칙으로 교정
R4. 정체성 공격 금지: "너는 ~야", "니가 문제야" → 구조 설명형으로 교정
R5. 설명형 금지 ("~할 수 있습니다", "~이라고 합니다") → 직격형 교정
    ※ 수치·사실 문장은 교정 금지 ✅ "월급 300 중 실수령은 240이다"
R6. 금지어·비속어·법적 위험·가짜 통계 → 교정 또는 삭제
R7. scenes: 반드시 8개 영어 묘사 (부족하면 추가)
    일상적 한국 직장인/생활 장면 위주 (cinematic, warm, no face)
R8. t1, t2: 빈 값이면 topic에서 추출
R9. 비유·은유·추상 표현 → 직장인 일상 구체 표현으로 교정
R10. 클리셰 금지: "상사 눈치", "퇴근 자책", "회의실 침묵" → 구체 묘사로 교정
R11. 편집자 개입 필드 필수:
    editor_point_of_view / one_argument / real_scene / visual_intention / human_pause
    빈 값이면 대본을 다시 읽고 실제 편집자가 남긴 판단처럼 채울 것.
    FAIL 예: "직장인을 위한 영상입니다" 같은 일반 설명
    PASS 예: "이번 영상은 친절함이 손해로 바뀌는 순간만 보려는 편집입니다"

[품질 지표] 교정 후 최종 기준, 각 10점 만점

scroll_stop_power: 첫 문장이 멈추게 하는가 (공격형이 아닌 현실 직격형도 OK)
  10: 보는 순간 손이 멈춤 — 현실을 콕 찍어서
   9: "이거 내 상황이잖아" 즉각 반응
   8: 강하지만 약간 예측 가능
   7: 멈추지만 임팩트 약함
  6↓: 설명형·조언형

practical_value: 보고 나서 하나가 정리되는가 (이전 emotional_attack 자리)
  10: "이렇게 보면 되는구나" — 구조 이해 완료
   9: 하나의 설계 원칙이 명확히 남음
   8: 공감되고 뭔가 정리됨
   7: 느낌은 있으나 정리 약함
  6↓: 불안만 남거나 뭘 해야 할지 모름

identity_fit: 매일의 설계 채널답고 구독 이유가 생기는가 (이전 repeat_value 자리)
   9: "이 채널 또 봐야겠다" — 채널 정체성과 완전 일치
   8: 채널다운 느낌 + 신뢰감
   7: 보고 나서 채널이 기억됨
  6↓: 일회성 느낌, 채널 정체성 없음

[원본 대본]
{draft}

[응답 JSON — 마크다운·코드블록 없이]
{{
  "topic":        "...",
  "content_type": "...",
  "axis":         "...",
  "pattern_type": "...",
  "editor_point_of_view": "...",
  "one_argument": "...",
  "real_scene": "...",
  "visual_intention": "...",
  "human_pause": "...",
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
    "practical_value":     0,
    "identity_fit":        0,
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
    # persona: topics.json의 persona 필드 우선, 없으면 style 파라미터
    persona_key  = topic_seed.get("persona", style)
    persona_hint = PERSONA_INSTRUCTIONS.get(persona_key, PERSONA_INSTRUCTIONS.get(style, PERSONA_INSTRUCTIONS["honest_observer"]))

    structure_key  = topic_seed.get("structure_type", "observation")
    structure_hint = STRUCTURE_INSTRUCTIONS.get(structure_key, STRUCTURE_INSTRUCTIONS["observation"])

    scene_hint   = topic_seed.get("scene_hint", "")
    axis         = topic_seed.get("axis", content_type)

    type_rules   = _GPT_TYPE_RULES.get(content_type, _GPT_TYPE_RULES["work"])
    system_msg   = _GPT_SYSTEM_BASE + type_rules

    user_msg = _GPT_USER_TMPL.format(
        topic          = topic_seed["topic"],
        angle          = topic_seed["angle"],
        target_emotion = topic_seed["target_emotion"],
        content_type   = content_type,
        axis           = axis,
        persona_hint   = persona_hint,
        structure_hint = structure_hint,
        scene_hint     = scene_hint,
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
    pv      = review_log.get("practical_value", "-")
    ifit    = review_log.get("identity_fit", "-")

    log.info(
        "[검수] verdict=%-10s | scroll_stop=%s | practical=%s | identity_fit=%s",
        verdict, ssp, pv, ifit,
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
    content_type: str  = "work",
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
    content_type : work | money
    ep_dir       : 저장 경로
    ep_id        : 에피소드 ID
    style        : senior_colleague | honest_observer | same_boat

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
            "practical_value":   review_log.get("practical_value",   review_log.get("emotional_attack", 0)),
            "identity_fit":      review_log.get("identity_fit",      review_log.get("repeat_value",     0)),
            # 기존 호환 필드 유지
            "emotional_attack":  review_log.get("practical_value",   review_log.get("emotional_attack", 0)),
            "repeat_value":      review_log.get("identity_fit",      review_log.get("repeat_value",     0)),
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
                "axis":           topic_seed.get("axis", content_type),
                "topic":          topic_seed["topic"],
                "angle":          topic_seed.get("angle", ""),
                "target_emotion": topic_seed.get("target_emotion", ""),
                "persona":        topic_seed.get("persona", style),
                "structure_type": topic_seed.get("structure_type", ""),
                "editor_point_of_view": reviewed.get("editor_point_of_view", ""),
                "one_argument": reviewed.get("one_argument", ""),
                "real_scene": reviewed.get("real_scene", topic_seed.get("scene_hint", "")),
                "visual_intention": reviewed.get("visual_intention", ""),
                "human_pause": reviewed.get("human_pause", ""),
                "view_score":     gate.view_score,
                "final_status":   "PASS",
                "_meta": {
                    "ep_id":          ep_id,
                    "topic_id":       topic_seed.get("id", ""),
                    "topic":          topic_seed["topic"],
                    "angle":          topic_seed.get("angle", ""),
                    "target_emotion": topic_seed.get("target_emotion", ""),
                    "axis":           topic_seed.get("axis", content_type),
                    "persona":        topic_seed.get("persona", style),
                    "structure_type": topic_seed.get("structure_type", ""),
                    "editorial": {
                        "editor_point_of_view": reviewed.get("editor_point_of_view", ""),
                        "one_argument": reviewed.get("one_argument", ""),
                        "real_scene": reviewed.get("real_scene", topic_seed.get("scene_hint", "")),
                        "visual_intention": reviewed.get("visual_intention", ""),
                        "human_pause": reviewed.get("human_pause", ""),
                    },
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

    p = argparse.ArgumentParser(description="대본 단독 생성 테스트 (v4.1 editorial seed pool)")
    p.add_argument("--topic-id",    required=True,  help="topics.json의 id (예: work_001)")
    p.add_argument("--topics-file", default="topics.json")
    p.add_argument("--style",       default="honest_observer",
                   choices=["senior_colleague", "honest_observer", "same_boat",
                            "docsul", "janas", "list", "seulki"])
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

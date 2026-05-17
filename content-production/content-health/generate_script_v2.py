"""
generate_script_v2.py
=====================
매일의 설계 — 몸의 설계 쇼츠 대본 생성 (Claude API 전용)

v4.0 변경사항:
- Hook 3타입 전환: identity_attack 제거 → recovery_design 추가
- 현실 설계형 대본: persona(3종) + structure_type(5종) + scene_hint 주입
- 감정충격 → 몸의 공감 (공격형 제거, 회복 신호 공감으로 전환)
- 저장유도 → 몸의 설계 원칙 (CTA 제거, 24자 이내 실천 원칙)
- 편집자 개입 필드 추가: 사람이 고른 주제/장면/편집 의도처럼 보이게 고정
- Quality Gate: emotional_attack → body_signal_resonance (≥6)
"""
import json
import random
import re
import sys
from pathlib import Path

BASE_DIR      = Path(__file__).parent
RUNTIME_DIR   = Path("/root/content/runtime/health")
USED_FILE     = RUNTIME_DIR / "health_used.json"
INSIGHTS_FILE = RUNTIME_DIR / "competitor_insights.json"

SCORE_PASS        = 6   # scroll_stop_power 최소 기준
RESONANCE_PASS    = 6   # body_signal_resonance 최소 기준
LOOP_PASS         = 6   # loop_value 최소 기준
EDITORIAL_PASS    = 6   # editor_intent_score 최소 기준
MAX_RETRY         = 2
HOOK_HISTORY_FILE = RUNTIME_DIR / "hook_history.json"
HOOK_HISTORY_MAX  = 6   # 최근 N개 hook_type 기록

# 3타입 순환 주기 (v4.0 — identity_attack 제거, recovery_design 추가)
HOOK_TYPE_CYCLE = ["myth_direct", "recovery_design", "expert_reversal"]

# 타입별 표현 후보 — {placeholder}는 Claude가 주제에 맞게 채움
HOOK_VARIANTS: dict[str, list[str]] = {
    "myth_direct": [
        "{상식}, 틀렸습니다",
        "당신이 알던 {상식}, 사실이 아닙니다",
        "모두가 믿는 {상식}, 실제로는 반대입니다",
        "{상식}? 사실은 이렇습니다",
        "평생 믿었던 {상식}, 오늘 정리합니다",
        "{상식} — 이게 왜 다른지 아세요?",
        "{상식}, 연구 결과는 달랐습니다",
        "{상식}이라고 알고 있었다면",
        "{상식} 믿고 있다면, 이 부분만 보세요",
        "30년 된 {상식}, 사실은 오해였습니다",
        "{상식}이 아니라 {진실}입니다",
    ],
    "recovery_design": [
        "{증상}이 계속된다면 몸이 보내는 신호입니다",
        "매일 {증상}한 이유, 구조에 있었습니다",
        "{습관} 때문에 몸에 생기는 변화",
        "{증상}, 그냥 피로가 아닐 수 있습니다",
        "{몸 상태}의 진짜 원인은 따로 있습니다",
        "몸이 회복을 요청하는 방식 — {증상}",
        "{증상}이 반복된다면 이것부터 보세요",
        "피로가 쌓이는 이유 — {습관} 때문입니다",
        "{몸 신호}, 무시하면 생기는 일",
        "회복이 안 되는 이유 — {원인}이었습니다",
        "{증상}을 잡는 가장 단순한 방법",
    ],
    "expert_reversal": [
        "의학 연구가 말하는 {주제}의 진실",
        "병원에서 잘 설명 안 해주는 {주제} 원리",
        "최신 연구가 바꾼 {주제} 상식",
        "{주제}, 논문에서는 이렇게 나왔습니다",
        "전문가들이 최근 바꾼 {주제} 권고사항",
        "{주제}, 연구 결과가 뒤집었습니다",
        "의대에서 가르치는 {주제}의 실제 메커니즘",
        "임상에서 확인된 {주제} 사실",
        "{주제}에 대한 기존 통념이 바뀐 이유",
        "연구로 밝혀진 {주제}의 진짜 원인",
        "{주제}, 전문가 권고가 달라진 이유",
    ],
}


def load_used() -> set:
    if not USED_FILE.exists():
        return set()
    return set(json.loads(USED_FILE.read_text(encoding="utf-8")).get("used_ids", []))


def load_hook_history() -> list:
    if not HOOK_HISTORY_FILE.exists():
        return []
    return json.loads(HOOK_HISTORY_FILE.read_text(encoding="utf-8")).get("history", [])


def save_hook_history(hook_type: str):
    history = load_hook_history()
    history.append(hook_type)
    history = history[-HOOK_HISTORY_MAX:]
    HOOK_HISTORY_FILE.write_text(
        json.dumps({"history": history}, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def get_next_hook_type() -> str:
    """3타입 엄격 순환: 마지막 사용 타입 다음 순서로 강제 지정."""
    history = load_hook_history()
    if not history:
        return HOOK_TYPE_CYCLE[0]
    last = history[-1]
    if last not in HOOK_TYPE_CYCLE:
        return HOOK_TYPE_CYCLE[0]
    next_idx = (HOOK_TYPE_CYCLE.index(last) + 1) % len(HOOK_TYPE_CYCLE)
    return HOOK_TYPE_CYCLE[next_idx]


def get_hook_expression(hook_type: str) -> str:
    """타입별 후보 중 Python random.choice()로 표현 선택 (Claude에게 선택 위임 안 함)."""
    variants = HOOK_VARIANTS.get(hook_type, HOOK_VARIANTS["myth_direct"])
    return random.choice(variants)


def save_used(used_ids: set):
    USED_FILE.write_text(
        json.dumps({"used_ids": list(used_ids)}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def load_competitor_insights() -> str:
    """competitor_insights.json에서 핵심 인사이트 텍스트 추출."""
    if not INSIGHTS_FILE.exists():
        return ""
    try:
        data = json.loads(INSIGHTS_FILE.read_text(encoding="utf-8"))
        a = data.get("analysis", {})
        stats = a.get("hook_type_stats", {})
        winning = a.get("winning_hook_type", "")
        phrases = a.get("key_phrases", [])[:6]
        top_hooks = a.get("top_hooks", [])[:3]
        recommendation = a.get("recommendation", "")
        generated = data.get("generated_at", "")[:10]

        lines = [f"━━━ 경쟁 채널 분석 인사이트 ({generated}) ━━━"]

        if winning:
            lines.append(f"🏆 최강 Hook 타입: {winning}")

        if stats:
            sorted_types = sorted(
                [(k, v) for k, v in stats.items() if v.get("count", 0) > 0],
                key=lambda x: x[1].get("avg_views", 0), reverse=True
            )
            lines.append("📊 Hook 타입별 평균 조회수:")
            for htype, stat in sorted_types[:3]:
                lines.append(f"  - {htype}: 평균 {stat['avg_views']:,}회 / 최고 {stat['max_views']:,}회")
                if stat.get("best_title"):
                    lines.append(f"    예: \"{stat['best_title']}\"")

        if top_hooks:
            lines.append("🔥 실제 고성과 Hook 예시 (참고용):")
            for h in top_hooks:
                lines.append(f"  [{h.get('views',0):,}회] \"{h.get('title','')}\" ({h.get('hook_type','')})")

        if phrases:
            lines.append(f"💡 고성과 제목 핵심 문구: {', '.join(phrases)}")

        if recommendation:
            lines.append(f"📌 적용 인사이트: {recommendation}")

        return "\n".join(lines)
    except Exception:
        return ""


def pick_topic(pool: list, used_ids: set) -> tuple:
    unused = [t for t in pool if t["id"] not in used_ids]
    if not unused:
        used_ids = set()
        save_used(used_ids)
        unused = pool
    return unused[0], used_ids


_PERSONA_TONE: dict[str, str] = {
    "senior_colleague": "선배 동료 톤: 쓸데없는 조언 말고 진짜 정리된 정보. 숫자와 원리 위주. 친근하지만 간결.",
    "honest_observer":  "솔직한 관찰자 톤: 다들 아는 척하지만 사실인 것. 판단 없이 관찰. '그렇습니다'가 아니라 '그렇더라고요'.",
    "same_boat":        "같은 처지 톤: 나도 그랬는데 알고 나서 달라졌어. 같이 겪은 경험 공유. 따뜻하되 과장 없이.",
}

_STRUCTURE_GUIDE: dict[str, str] = {
    "fact":        "사실 전달형: 핵심 수치와 메커니즘 먼저. 연구 결과를 근거로.",
    "reversal":    "반전형: 상식이라 믿던 것을 뒤집어라. 반전 타이밍이 핵심.",
    "observation": "관찰형: 일상에서 실제 벌어지는 장면 묘사. 독자가 고개 끄덕이게.",
    "question":    "질문형: 답을 알기 전에 의문이 먼저. 궁금증을 유발한 뒤 해소.",
    "story":       "스토리형: 한 장면에서 시작해 원리로 확장. 장면 → 문제 → 원인 → 해법.",
}


def _build_prompt(
    topic: dict,
    retry_feedback: str = "",
    forced_hook_type: str = "",
    expression_template: str = "",
) -> str:
    title      = topic["title"]
    theme      = topic.get("theme", "")
    myth       = topic.get("myth", "")
    scene_hint = topic.get("scene_hint", "")
    persona    = topic.get("persona", "honest_observer")
    structure  = topic.get("structure_type", "fact")

    persona_guide   = _PERSONA_TONE.get(persona, _PERSONA_TONE["honest_observer"])
    structure_guide = _STRUCTURE_GUIDE.get(structure, _STRUCTURE_GUIDE["fact"])

    scene_hint_block = f"\n일상 장면 힌트 (대본에 이 구체적 상황 녹여낼 것): {scene_hint}" if scene_hint else ""

    retry_block = ""
    if retry_feedback:
        retry_block = f"""
⚠️ 이전 버전 품질 미달 — 아래 피드백 반영해서 다시 작성:
{retry_feedback}
"""

    hook_directive = ""
    if forced_hook_type and expression_template:
        hook_directive = f"""
🔒 Hook 타입 강제 지정 (변경 금지): **{forced_hook_type}**
🔒 Hook 표현 강제 (이 틀 그대로 사용, {{placeholder}} 부분만 주제에 맞게 채울 것):
   → "{expression_template}"
   예: "{expression_template.split('{')[0]}..." 형태로 주제 단어를 대입해 완성
"""

    competitor_block = load_competitor_insights()
    if competitor_block:
        competitor_block = "\n" + competitor_block + "\n"

    return f"""너는 유튜브 쇼츠 대본 전문가. 매일의 설계 채널 — 몸의 설계 편. S급 건강 쇼츠 대본만 작성.
{retry_block}{hook_directive}{competitor_block}
주제: {title}
테마: {theme}
잘못된 상식 (반전 포인트): {myth}{scene_hint_block}

━━━ 글쓰기 방향 ━━━
페르소나: {persona_guide}
구조 방식: {structure_guide}
금지: "너는/당신은 이런 사람", 저장 강요, 구독 촉구, 가짜 통계(출처 없는 수치는 "연구에 따르면" 표현 금지)
허용: 구체적 일상 장면 묘사, "~하더라고요" 관찰 표현, 실제 메커니즘 수치

━━━ 편집자 개입 시스템 ━━━
AI가 건강 정보를 자동 요약한 영상처럼 보이면 실패다.
사람이 이 주제를 왜 골랐고, 어떤 장면을 왜 보여주는지 판단한 흔적을 남겨라.

반드시 아래 5개를 먼저 설계하고 JSON에 포함:
- editor_point_of_view: 이 건강 주제를 지금 다루는 편집자 관점 1문장
- one_argument: 이번 영상에서 딱 하나만 말할 주장 1문장
- real_scene: 시청자가 실제로 겪는 몸의 장면 1개
- visual_intention: 왜 이 이미지를 보여주는지 편집 의도 1문장
- human_pause: 자막/내레이션에서 일부러 한 박자 쉬는 위치 1개

━━━ Hook 규칙 (설명형/정보형 절대 금지) ━━━
위 🔒 강제 지정이 있으면 반드시 그 타입·표현 사용. 없으면 아래 3대 공식 중 1개 선택.

① 잘못된상식 직격형 (myth_direct)
   예: "{'{'}상식{'}'}, 틀렸습니다"
② 회복 설계형 (recovery_design)
   예: "{'{'}증상{'}'}이 반복된다면 몸이 보내는 신호입니다"
③ 전문가 반전형 (expert_reversal)
   예: "최신 연구가 바꾼 {'{'}주제{'}'} 상식"

금지 Hook: "~하면 일어나는 일" / "~의 효과" / "~알고 계셨나요?" / "매일 ~했던 당신"

━━━ 장면 구조 (총 7장면, duration은 TTS 예상 기준) ━━━
0. Hook (duration ~5): 위 3대 공식 중 하나. 2줄 이내.
1. 과학설명1 (duration ~8): 핵심 메커니즘 + 수치. "→" 기호 활용.
2. 과학설명2 (duration ~8): 추가 효과/연구. 이모지 + 수치.
3. 잘못된상식 반전 (duration ~8): "근데 대부분은..." 공감 유발.
4. 몸의 공감 (duration ~5): 일상 장면 속 이 신호를 가볍게 공감. 짧고 구체적으로.
   예: "아침에 물 안 마시고 커피부터 찾았다면, 몸이 이미 말하고 있던 거예요"
   금지: "매일 이렇게 했던 당신" / "당신의 ~는" 류 정체성 공격
5. 몸의 설계 원칙 (duration ~4): 오늘 바로 적용할 1가지. 24자 이내. 실천 원칙으로 끝맺음.
   예: "기상 후 30분 안에 물 한 잔이면 충분합니다"
   금지: "저장해두세요" / "좋아요 누르세요" / "퍼뜨려야 함" 류 CTA
6. 루프트리거 (duration ~3): Hook의 구체적 복선 언급. "첫 장면에서 {'{'}복선 내용{'}'} 이미 말했음 👀"

━━━ narration 글자수 규칙 (핵심, 반드시 준수) ━━━
한국어 TTS 발화 속도 = 약 5자/초. duration에 비례한 글자수를 엄수.
  duration ~3  → narration 15자 이내
  duration ~4  → narration 24자 이내
  duration ~5  → narration 25자 이내
  duration ~8  → narration 40자 이내
전체 7씬 narration 합계: 165자 이내 (영상 35~50초 목표)
narration은 caption 핵심 1~2문장. 불필요한 부연 설명 금지.

━━━ 루프트리거 핵심 규칙 ━━━
- "처음부터 보면 복선 있음" 금지 — 너무 추상적
- 반드시 Hook에서 언급한 내용의 구체적 복선을 명시
- 예: Hook이 "의사들이 말 안 해준 진실"이면 → "첫 장면 의사 발언, 다시 보면 이미 힌트 있었음 👀"

━━━ image_prompt + image_style 규칙 ━━━
각 씬에 "image_style" 필드를 반드시 포함. 씬 위치가 아닌 씬 내용 기준으로 최적 스타일 선택.

  "photo"   — 실사 스포츠/생활 사진 스타일
              선택 기준: 현실에서 실제로 찍을 수 있는 장면 (운동하는 사람, 음식, 생활 행동 등)
              사람은 뒷모습·실루엣·부분(손발)만 허용. 얼굴 금지.

  "digital" — sci-fi 개념 시각화 스타일
              선택 기준: 눈에 보이지 않는 내부 메커니즘 (뇌·세포·신호전달·장기·화학물질 등)
              glowing neon particles, dark background, 3D render 느낌

  "object"  — 오브젝트 전용, 사람 완전 금지 ← 몸의 공감 씬(scene5) 필수 (content_policy 방지)
              선택 기준: 부정적 감정/상황에 있는 씬 — 오브젝트로 대체
              운동화·가방·타월·음식·약 등 주제 관련 오브젝트만

추가 규칙:
  scene7 루프트리거: 반드시 scene1 Hook과 동일한 image_style 사용 (시각적 루프 연결)
    → Hook이 photo였으면 scene7도 photo, Hook이 digital이었으면 scene7도 digital

판단 예시:
  "달리기 후 도파민 분비" → digital (뇌 내부 신경물질, 눈에 안 보임)
  "커피 마시는 아침 장면" → photo (실제 생활 장면)
  "목 디스크 구조 압박" → digital (신체 내부 구조)
  "운동 포기하고 쉬는 상황" → object (사람 없이 운동화·짐가방으로 표현)
  "설계 원칙 — 실천 장면" → photo 또는 digital (긍정적 씬, 자유 선택)

공통: Flux 영문 프롬프트, 9:16 portrait orientation, NO text in image

━━━ Quality 자가 채점 (JSON에 포함) ━━━
- scroll_stop_power (1~10): Hook이 피드에서 스크롤을 멈추게 하는 힘
- body_signal_resonance (1~10): 몸의 공감 장면이 실제 일상 경험과 얼마나 공명하는가
- loop_value (1~10): 루프트리거가 실제로 다시 보게 만드는 힘
- editor_intent_score (1~10): 사람이 주제와 장면을 고른 편집 판단이 보이는가

JSON만 출력 (마크다운/설명 없이):
{{
  "title": "{title}",
  "content_type": "건강상식",
  "editor_point_of_view": "편집자가 이 주제를 고른 이유와 관점 1문장",
  "one_argument": "이번 영상에서 딱 하나만 말할 주장 1문장",
  "real_scene": "실제 몸의 신호가 나타나는 일상 장면 1개",
  "visual_intention": "왜 이 장면/이미지를 보여주는지 편집 의도 1문장",
  "human_pause": "자막/내레이션에서 일부러 쉬어갈 위치 1개",
  "hook": "Hook 문장 (15자 이내)",
  "hook_type": "myth_direct | recovery_design | expert_reversal",
  "scenes": [
    {{"duration": 5, "caption": "Hook 자막\\n두 줄 이내", "narration": "25자 이내. 핵심 1문장.", "image_style": "photo|digital 중 씬 내용에 최적인 것 선택", "image_prompt": "씬 내용에 맞는 Flux 영문 프롬프트"}},
    {{"duration": 8, "caption": "과학설명1\\n→ 수치", "narration": "40자 이내. 핵심 1~2문장.", "image_style": "photo|digital 중 씬 내용에 최적인 것 선택", "image_prompt": "씬 내용에 맞는 Flux 영문 프롬프트"}},
    {{"duration": 8, "caption": "과학설명2\\n이모지 + 수치", "narration": "40자 이내. 핵심 1~2문장.", "image_style": "photo|digital 중 씬 내용에 최적인 것 선택", "image_prompt": "씬 내용에 맞는 Flux 영문 프롬프트"}},
    {{"duration": 8, "caption": "잘못된 상식\\n반전 ⚠️", "narration": "40자 이내. 핵심 1~2문장.", "image_style": "photo|digital 중 씬 내용에 최적인 것 선택", "image_prompt": "씬 내용에 맞는 Flux 영문 프롬프트"}},
    {{"duration": 5, "caption": "몸의 공감 — 익숙한 신호", "narration": "25자 이내. 일상 장면 공감 1문장.", "image_style": "object", "image_prompt": "cinematic still life of [주제 관련 오브젝트], warm soft light, calm atmosphere, no people, no text, 9:16 vertical portrait"}},
    {{"duration": 4, "caption": "몸의 설계 원칙 📌", "narration": "24자 이내. 오늘 바로 적용할 1가지 원칙.", "image_style": "photo|digital 중 씬 내용에 최적인 것 선택", "image_prompt": "씬 내용에 맞는 Flux 영문 프롬프트"}},
    {{"duration": 3, "caption": "루프트리거 👀", "narration": "15자 이내. Hook 복선 언급.", "image_style": "scene1과 동일한 스타일", "image_prompt": "scene1 Hook 장면을 재소환하는 이미지 — 뒷모습/실루엣/개념 재현, mysterious atmosphere, no text, 9:16 vertical portrait"}}
  ],
  "total_duration": 41,
  "design_principle": "몸의 설계 원칙 문장 (24자 이내)",
  "loop_trigger": "루프트리거 문장 (Hook 복선 구체적 언급)",
  "tags_ko": ["매일의설계", "건강", "쇼츠", "건강습관", "주제태그"],
  "scroll_stop_power": 8,
  "body_signal_resonance": 7,
  "loop_value": 7,
  "editor_intent_score": 7
}}"""


def _parse_json(text: str) -> dict:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return json.loads(text.strip())


def _quality_check(script: dict) -> tuple[bool, str]:
    """Returns (passed, feedback_message)"""
    ssp       = script.get("scroll_stop_power", 0)
    bsr       = script.get("body_signal_resonance", 0)
    lv        = script.get("loop_value", 0)
    eis       = script.get("editor_intent_score", 0)
    hook_type = script.get("hook_type", "")

    issues = []
    if ssp < SCORE_PASS:
        issues.append(f"scroll_stop_power={ssp} (목표 {SCORE_PASS}+) — Hook이 설명형/정보형임. 3대 공식(myth_direct/recovery_design/expert_reversal) 중 하나로 재작성 필요")
    if bsr < RESONANCE_PASS:
        issues.append(f"body_signal_resonance={bsr} (목표 {RESONANCE_PASS}+) — 몸의 공감 장면이 약함. 일상 속 구체적 신호 장면으로 재작성 필요")
    if lv < LOOP_PASS:
        issues.append(f"loop_value={lv} (목표 {LOOP_PASS}+) — 루프트리거가 '처음부터 보면 복선 있음' 류. Hook 복선 구체적으로 명시 필요")
    if eis < EDITORIAL_PASS:
        issues.append(f"editor_intent_score={eis} (목표 {EDITORIAL_PASS}+) — 사람이 주제와 장면을 고른 편집 의도가 약함")
    if not hook_type or hook_type not in ("myth_direct", "recovery_design", "expert_reversal"):
        issues.append(f"hook_type='{hook_type}' — 3대 공식(myth_direct/recovery_design/expert_reversal) 중 하나여야 함")
    for field in ("editor_point_of_view", "one_argument", "real_scene", "visual_intention", "human_pause"):
        if not str(script.get(field, "")).strip():
            issues.append(f"{field} 비어 있음 — 편집자 개입 흔적 필수")

    if issues:
        return False, "\n".join(f"- {i}" for i in issues)
    return True, ""


def generate_script(topic: dict) -> dict:
    import anthropic
    sys.path.insert(0, str(RUNTIME_DIR))
    from config import CLAUDE_API_KEY

    client = anthropic.Anthropic(api_key=CLAUDE_API_KEY)
    retry_feedback = ""

    # 3타입 엄격 순환 — Python이 타입·표현 모두 결정, Claude에게 선택 위임 안 함
    forced_hook_type   = get_next_hook_type()
    expression_template = get_hook_expression(forced_hook_type)
    print(f"  🔄 Hook 순환: {forced_hook_type} → 표현: \"{expression_template}\"")

    if INSIGHTS_FILE.exists():
        print(f"  📈 경쟁 분석 인사이트 로드: {INSIGHTS_FILE.name}")
    else:
        print(f"  ℹ️  경쟁 분석 없음 (python3 analyze_competitor.py 실행 시 활성화)")

    for attempt in range(MAX_RETRY + 1):
        prompt = _build_prompt(
            topic, retry_feedback,
            forced_hook_type=forced_hook_type,
            expression_template=expression_template,
        )
        msg = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        )
        script = _parse_json(msg.content[0].text)

        passed, feedback = _quality_check(script)
        ssp       = script.get("scroll_stop_power", "?")
        bsr       = script.get("body_signal_resonance", "?")
        lv        = script.get("loop_value", "?")
        eis       = script.get("editor_intent_score", "?")
        hook_type = script.get("hook_type", "?")

        print(f"  📊 품질 점수 (시도 {attempt+1}): scroll_stop={ssp}, body_signal={bsr}, loop={lv}, editorial={eis}, hook_type={hook_type}")

        if passed:
            print(f"  ✅ Quality Gate 통과")
            save_hook_history(hook_type)
            return script

        if attempt < MAX_RETRY:
            print(f"  ⚠️ Quality Gate 미달 — 재시도 {attempt+1}/{MAX_RETRY}")
            print(f"     피드백: {feedback}")
            retry_feedback = feedback
        else:
            print(f"  ⚠️ Quality Gate 미달이나 최대 재시도 도달 — 현재 버전 사용")
            save_hook_history(hook_type)

    return script


def main():
    pool_file = BASE_DIR / "topics_health.json"
    if not pool_file.exists():
        print(json.dumps({"error": "no_pool_file"}, ensure_ascii=False))
        sys.exit(1)

    pool = json.loads(pool_file.read_text(encoding="utf-8"))
    used_ids = load_used()
    topic, used_ids = pick_topic(pool, used_ids)

    try:
        script = generate_script(topic)
    except Exception as e:
        print(json.dumps({"error": f"generate_failed: {e}"}, ensure_ascii=False))
        sys.exit(1)

    used_ids.add(topic["id"])
    save_used(used_ids)

    print(json.dumps({
        "topic_id": topic["id"],
        "title": topic["title"],
        "content_type": topic["content_type"],
        "script": script,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()

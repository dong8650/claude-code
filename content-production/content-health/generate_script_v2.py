"""
generate_script_v2.py
=====================
건강 상식 연구소 — S급 쇼츠 대본 생성 (Claude API 전용)

v2.5 변경사항:
- Hook 3대 공식 강제 (정체성 공격형 / 전문가 반전형 / 잘못된상식 직격형)
- Quality Gate: scroll_stop_power ≥7, emotional_attack ≥7, loop_value ≥6
- 미달 시 최대 2회 자동 재시도 (Hook 재작성 가이드 포함)
- 25초 고정 해제 — TTS 실제 길이가 영상 길이 결정
- 루프트리거: 첫 장면 구체적 복선 언급 강제
"""
import json
import re
import sys
from pathlib import Path

BASE_DIR      = Path(__file__).parent
RUNTIME_DIR   = Path("/root/content/runtime/health")
USED_FILE     = RUNTIME_DIR / "health_used.json"
INSIGHTS_FILE = RUNTIME_DIR / "competitor_insights.json"

SCORE_PASS        = 7   # scroll_stop_power / emotional_attack 최소 기준
LOOP_PASS         = 6   # loop_value 최소 기준
MAX_RETRY         = 2
HOOK_HISTORY_FILE = RUNTIME_DIR / "hook_history.json"
HOOK_HISTORY_MAX  = 3   # 최근 N개 hook_type 기록


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


def _build_prompt(topic: dict, retry_feedback: str = "", avoid_hook_type: str = "") -> str:
    title  = topic["title"]
    theme  = topic.get("theme", "")
    myth   = topic.get("myth", "")

    retry_block = ""
    if retry_feedback:
        retry_block = f"""
⚠️ 이전 버전 품질 미달 — 아래 피드백 반영해서 다시 작성:
{retry_feedback}
"""

    avoid_block = ""
    if avoid_hook_type:
        avoid_block = f"\n⚠️ Hook 타입 순환 규칙: 최근 '{avoid_hook_type}' 연속 사용됨 → 이번엔 다른 타입 선택 필수.\n"

    competitor_block = load_competitor_insights()
    if competitor_block:
        competitor_block = "\n" + competitor_block + "\n"

    return f"""너는 유튜브 쇼츠 알고리즘 전문가. 조회수 2.5k 천장을 돌파하는 S급 건강 쇼츠 대본만 작성.
{retry_block}{avoid_block}{competitor_block}
주제: {title}
테마: {theme}
잘못된 상식 (반전 포인트): {myth}

━━━ Hook 3대 공식 (반드시 1개 선택, 설명형/정보형 절대 금지) ━━━
① 정체성 공격형 (identity_attack)
   "매일 {'{'}행동{'}'}했던 당신, 사실 {'{'}충격 사실{'}'}"
   → 시청자의 현재 행동이 틀렸다는 공포. "이거 보는 사람 다 해당됨"

② 전문가 반전형 (expert_reversal)
   "의사들이 절대 말 안 해주는 {'{'}주제{'}'} 진실"
   → 전문가와 일반인 사이의 정보 격차 공포

③ 잘못된상식 직격형 (myth_direct) — 표현 반드시 아래 5가지 중 랜덤 선택, "사실 반대임" 반복 금지
   A. "{'{'}상식{'}'}, 틀렸습니다"
   B. "당신이 알던 {'{'}상식{'}'}, 사실이 아님"
   C. "모두가 믿는 {'{'}상식{'}'}, 의사들은 반대로 말해"
   D. "{'{'}상식{'}'}? 99%가 모르는 진실"
   E. "{'{'}상식{'}'}, 사실 반대임" ← 최근에 사용했으면 A~D 중 선택

금지 Hook: "~하면 일어나는 일" / "~의 효과" / "~알고 계셨나요?" / 동일 표현 2회 연속

━━━ 장면 구조 (총 7장면, duration은 TTS 예상 기준) ━━━
0. Hook (duration ~5): 위 3대 공식 중 하나. 2줄 이내.
1. 과학설명1 (duration ~8): 핵심 메커니즘 + 수치. "→" 기호 활용.
2. 과학설명2 (duration ~8): 추가 효과/연구. 이모지 + 수치.
3. 잘못된상식 반전 (duration ~8): "근데 대부분은..." 공감 유발.
4. 감정충격 (duration ~5): "매일 이렇게 {'{'}행동{'}'}했던 당신..." 😱 짧고 강하게.
5. 좋아요+저장유도 (duration ~4): "공감됐으면 좋아요 누르고 저장해둬 💾👍" — 좋아요+저장 동시 촉구.
6. 루프트리거 (duration ~3): Hook의 구체적 복선 언급. "첫 장면에서 {'{'}복선 내용{'}'} 이미 말했음 👀"

━━━ narration 글자수 규칙 (핵심, 반드시 준수) ━━━
한국어 TTS 발화 속도 = 약 5자/초. duration에 비례한 글자수를 엄수.
  duration ~3  → narration 15자 이내
  duration ~4  → narration 20자 이내
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

  "object"  — 오브젝트 전용, 사람 완전 금지 ← 감정충격 씬(scene5) 필수 (content_policy 방지)
              선택 기준: 사람이 부정적 감정/상황에 있는 씬 — DALL-E가 차단하므로 오브젝트로 대체
              운동화·가방·타월·음식·약 등 주제 관련 오브젝트만

추가 규칙:
  scene7 루프트리거: 반드시 scene1 Hook과 동일한 image_style 사용 (시각적 루프 연결)
    → Hook이 photo였으면 scene7도 photo, Hook이 digital이었으면 scene7도 digital

판단 예시:
  "달리기 후 도파민 분비" → digital (뇌 내부 신경물질, 눈에 안 보임)
  "커피 마시는 아침 장면" → photo (실제 생활 장면)
  "목 디스크 구조 압박" → digital (신체 내부 구조)
  "운동 포기하고 쉬는 상황" → object (사람 없이 운동화·짐가방으로 표현)
  "저장유도 — 동기부여 장면" → photo 또는 digital (긍정적 씬, 자유 선택)

공통: DALL-E 3 영문 프롬프트, 9:16 portrait orientation, NO text in image

━━━ Quality 자가 채점 (JSON에 포함) ━━━
- scroll_stop_power (1~10): Hook이 피드에서 스크롤을 멈추게 하는 힘
- emotional_attack (1~10): 감정충격 장면의 공감 폭발력
- loop_value (1~10): 루프트리거가 실제로 다시 보게 만드는 힘

JSON만 출력 (마크다운/설명 없이):
{{
  "title": "{title}",
  "content_type": "건강상식",
  "hook": "Hook 문장 (15자 이내)",
  "hook_type": "identity_attack | expert_reversal | myth_direct",
  "scenes": [
    {{"duration": 5, "caption": "Hook 자막\\n두 줄 이내", "narration": "25자 이내. 핵심 1문장.", "image_style": "photo|digital 중 씬 내용에 최적인 것 선택", "image_prompt": "씬 내용에 맞는 Flux 영문 프롬프트"}},
    {{"duration": 8, "caption": "과학설명1\\n→ 수치", "narration": "40자 이내. 핵심 1~2문장.", "image_style": "photo|digital 중 씬 내용에 최적인 것 선택", "image_prompt": "씬 내용에 맞는 Flux 영문 프롬프트"}},
    {{"duration": 8, "caption": "과학설명2\\n이모지 + 수치", "narration": "40자 이내. 핵심 1~2문장.", "image_style": "photo|digital 중 씬 내용에 최적인 것 선택", "image_prompt": "씬 내용에 맞는 Flux 영문 프롬프트"}},
    {{"duration": 8, "caption": "잘못된 상식\\n반전 ⚠️", "narration": "40자 이내. 핵심 1~2문장.", "image_style": "photo|digital 중 씬 내용에 최적인 것 선택", "image_prompt": "씬 내용에 맞는 Flux 영문 프롬프트"}},
    {{"duration": 5, "caption": "감정충격 😱", "narration": "25자 이내. 핵심 1문장.", "image_style": "object", "image_prompt": "cinematic still life of [주제 관련 오브젝트], dark moody atmosphere, dramatic spotlight, no people, no text, 9:16 vertical portrait"}},
    {{"duration": 4, "caption": "좋아요+저장유도 💾👍", "narration": "20자 이내. 핵심 1문장.", "image_style": "photo|digital|object 중 씬 내용에 최적인 것 선택", "image_prompt": "씬 내용에 맞는 Flux 영문 프롬프트"}},
    {{"duration": 3, "caption": "루프트리거 👀", "narration": "15자 이내. Hook 복선 언급.", "image_style": "scene1과 동일한 스타일", "image_prompt": "scene1 Hook 장면을 재소환하는 이미지 — 뒷모습/실루엣/개념 재현, mysterious atmosphere, no text, 9:16 vertical portrait"}}
  ],
  "total_duration": 41,
  "save_trigger": "저장유도 문장",
  "loop_trigger": "루프트리거 문장 (Hook 복선 구체적 언급)",
  "tags_ko": ["건강상식연구소", "건강", "쇼츠", "건강습관", "주제태그"],
  "scroll_stop_power": 8,
  "emotional_attack": 8,
  "loop_value": 7
}}"""


def _parse_json(text: str) -> dict:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return json.loads(text.strip())


def _quality_check(script: dict) -> tuple[bool, str]:
    """Returns (passed, feedback_message)"""
    ssp = script.get("scroll_stop_power", 0)
    ea  = script.get("emotional_attack", 0)
    lv  = script.get("loop_value", 0)
    hook_type = script.get("hook_type", "")
    hook = script.get("hook", "")

    issues = []
    if ssp < SCORE_PASS:
        issues.append(f"scroll_stop_power={ssp} (목표 {SCORE_PASS}+) — Hook이 설명형/정보형임. 3대 공식 중 하나로 재작성 필요")
    if ea < SCORE_PASS:
        issues.append(f"emotional_attack={ea} (목표 {SCORE_PASS}+) — 감정충격 장면이 약함. '매일 이렇게 했던 당신' 강도 높여야 함")
    if lv < LOOP_PASS:
        issues.append(f"loop_value={lv} (목표 {LOOP_PASS}+) — 루프트리거가 '처음부터 보면 복선 있음' 류. Hook 복선 구체적으로 명시 필요")
    if not hook_type or hook_type not in ("identity_attack", "expert_reversal", "myth_direct"):
        issues.append(f"hook_type='{hook_type}' — 3대 공식(identity_attack/expert_reversal/myth_direct) 중 하나여야 함")

    if issues:
        return False, "\n".join(f"- {i}" for i in issues)
    return True, ""


def generate_script(topic: dict) -> dict:
    import anthropic
    sys.path.insert(0, str(RUNTIME_DIR))
    from config import CLAUDE_API_KEY

    client = anthropic.Anthropic(api_key=CLAUDE_API_KEY)
    retry_feedback = ""

    # hook_type 순환: 최근 연속 사용된 타입 감지
    hook_history  = load_hook_history()
    avoid_hook    = ""
    if len(hook_history) >= 2 and len(set(hook_history[-2:])) == 1:
        avoid_hook = hook_history[-1]
        print(f"  🔄 Hook 순환 적용: '{avoid_hook}' 연속 사용 → 다른 타입 유도")

    if INSIGHTS_FILE.exists():
        print(f"  📈 경쟁 분석 인사이트 로드: {INSIGHTS_FILE.name}")
    else:
        print(f"  ℹ️  경쟁 분석 없음 (python3 analyze_competitor.py 실행 시 활성화)")

    for attempt in range(MAX_RETRY + 1):
        prompt = _build_prompt(topic, retry_feedback, avoid_hook_type=avoid_hook)
        msg = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        )
        script = _parse_json(msg.content[0].text)

        passed, feedback = _quality_check(script)
        ssp = script.get("scroll_stop_power", "?")
        ea  = script.get("emotional_attack", "?")
        lv  = script.get("loop_value", "?")
        hook_type = script.get("hook_type", "?")

        print(f"  📊 품질 점수 (시도 {attempt+1}): scroll_stop={ssp}, emotional={ea}, loop={lv}, hook_type={hook_type}")

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

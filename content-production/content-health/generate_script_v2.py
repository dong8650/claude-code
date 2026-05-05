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

BASE_DIR     = Path(__file__).parent
RUNTIME_DIR  = Path("/root/content/runtime/health")
USED_FILE    = RUNTIME_DIR / "health_used.json"

SCORE_PASS   = 7   # scroll_stop_power / emotional_attack 최소 기준
LOOP_PASS    = 6   # loop_value 최소 기준
MAX_RETRY    = 2


def load_used() -> set:
    if not USED_FILE.exists():
        return set()
    return set(json.loads(USED_FILE.read_text(encoding="utf-8")).get("used_ids", []))


def save_used(used_ids: set):
    USED_FILE.write_text(
        json.dumps({"used_ids": list(used_ids)}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def pick_topic(pool: list, used_ids: set) -> tuple:
    unused = [t for t in pool if t["id"] not in used_ids]
    if not unused:
        used_ids = set()
        save_used(used_ids)
        unused = pool
    return unused[0], used_ids


def _build_prompt(topic: dict, retry_feedback: str = "") -> str:
    title  = topic["title"]
    theme  = topic.get("theme", "")
    myth   = topic.get("myth", "")

    retry_block = ""
    if retry_feedback:
        retry_block = f"""
⚠️ 이전 버전 품질 미달 — 아래 피드백 반영해서 다시 작성:
{retry_feedback}
"""

    return f"""너는 유튜브 쇼츠 알고리즘 전문가. 조회수 2.5k 천장을 돌파하는 S급 건강 쇼츠 대본만 작성.
{retry_block}
주제: {title}
테마: {theme}
잘못된 상식 (반전 포인트): {myth}

━━━ Hook 3대 공식 (반드시 1개 선택, 설명형/정보형 절대 금지) ━━━
① 정체성 공격형 — "매일 {'{'}행동{'}'}했던 당신, 사실 {'{'}충격 사실{'}'}"
   → 시청자의 현재 행동이 틀렸다는 공포. "이거 보는 사람 다 해당됨"
② 전문가 반전형 — "의사들이 절대 말 안 해주는 {'{'}주제{'}'} 진실"
   → 전문가와 일반인 사이의 정보 격차 공포
③ 잘못된상식 직격형 — "{'{'}대중이 믿는 상식{'}'}, 사실 반대임"
   → 잘못된 상식을 직격. 공유 욕구 폭발

금지 Hook: "~하면 일어나는 일" / "~의 효과" / "~알고 계셨나요?"

━━━ 장면 구조 (총 7장면, duration은 TTS 예상 기준) ━━━
0. Hook (duration ~3): 위 3대 공식 중 하나. 2줄 이내.
1. 과학설명1 (duration ~5): 핵심 메커니즘 + 수치. "→" 기호 활용.
2. 과학설명2 (duration ~5): 추가 효과/연구. 이모지 + 수치.
3. 잘못된상식 반전 (duration ~5): "근데 대부분은..." 공감 유발.
4. 감정충격 (duration ~3): "매일 이렇게 {'{'}행동{'}'}했던 당신..." 😱 짧고 강하게.
5. 저장유도 (duration ~2): "저장해두고 내일부터 시작해 💾" — 구체적 행동 촉구.
6. 루프트리거 (duration ~1): Hook의 구체적 복선 언급. "첫 장면에서 {'{'}복선 내용{'}'} 이미 말했음 👀"

━━━ 루프트리거 핵심 규칙 ━━━
- "처음부터 보면 복선 있음" 금지 — 너무 추상적
- 반드시 Hook에서 언급한 내용의 구체적 복선을 명시
- 예: Hook이 "의사들이 말 안 해준 진실"이면 → "첫 장면 의사 발언, 다시 보면 이미 힌트 있었음 👀"

━━━ image_prompt 규칙 ━━━
- DALL-E 3 영문 프롬프트
- cute cartoon organ/cell character style, bright colorful
- 9:16 portrait orientation (반드시 세로형)
- NO real human faces, NO text in image

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
    {{"duration": 3, "caption": "Hook 자막\\n두 줄 이내", "narration": "TTS 나레이션 (자막보다 자연스럽게)", "image_prompt": "cute cartoon health character, bright colorful, 9:16 vertical..."}},
    {{"duration": 5, "caption": "과학설명1\\n→ 수치", "narration": "나레이션", "image_prompt": "..."}},
    {{"duration": 5, "caption": "과학설명2\\n이모지 + 수치", "narration": "나레이션", "image_prompt": "..."}},
    {{"duration": 5, "caption": "잘못된 상식\\n반전 ⚠️", "narration": "나레이션", "image_prompt": "..."}},
    {{"duration": 3, "caption": "감정충격 😱", "narration": "나레이션", "image_prompt": "..."}},
    {{"duration": 2, "caption": "저장유도 💾", "narration": "나레이션", "image_prompt": "..."}},
    {{"duration": 1, "caption": "루프트리거 👀", "narration": "", "image_prompt": "..."}}
  ],
  "total_duration": 24,
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

    for attempt in range(MAX_RETRY + 1):
        prompt = _build_prompt(topic, retry_feedback)
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
            return script

        if attempt < MAX_RETRY:
            print(f"  ⚠️ Quality Gate 미달 — 재시도 {attempt+1}/{MAX_RETRY}")
            print(f"     피드백: {feedback}")
            retry_feedback = feedback
        else:
            print(f"  ⚠️ Quality Gate 미달이나 최대 재시도 도달 — 현재 버전 사용")

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

"""
generate_script_v2.py
=====================
건강 상식 연구소 — S급 쇼츠 대본 생성 (Claude API 전용)

콘텐츠 타입:
  건강상식 — 25초: Hook → 과학설명 → 잘못된상식반전 → 감정충격 → 저장유도 → 루프트리거
"""
import json
import re
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent
USED_FILE = BASE_DIR / "health_used.json"


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


def _build_prompt(topic: dict) -> str:
    title = topic["title"]
    theme = topic.get("theme", "")
    myth = topic.get("myth", "")

    return f"""건강 상식 연구소 채널의 S급 유튜브 쇼츠 대본을 만들어줘.

주제: {title}
테마: {theme}
잘못된 상식 (반전 포인트): {myth}

S급 조건:
- 총 길이: 25초
- Hook (0~2초, duration 3): 멈추게 만드는 문장. "의사들이 매일 하는데 우리만 모름" / "이거 알면 병원 덜 가도 됨" 류.
- 과학설명1 (3~7초, duration 5): 짧고 임팩트 있는 과학적 근거. "→" 기호 + 수치 활용.
- 과학설명2 (8~13초, duration 6): 추가 효과나 메커니즘. 이모지 활용.
- 잘못된상식 반전 (14~18초, duration 5): "근데 대부분이 이렇게 한다..." 전환. 공감 유발.
- 감정충격 (19~21초, duration 3): "매일 이렇게 했던 당신..." 😱 공감 폭발.
- 저장유도 (22~23초, duration 2): "저장해두고 내일부터 해봐 💾"
- 루프트리거 (24~25초, duration 2): "처음부터 보면 복선 있음 👀"

image_prompt 요구사항:
- DALL-E 3용 영문 프롬프트
- 귀여운 장기/세포/캐릭터 스타일 (cute cartoon organ character)
- 밝고 컬러풀한 건강 인포그래픽 스타일
- 반드시 9:16 세로형 (portrait orientation)
- 실제 사람 얼굴 금지

narration: 자막과 동일한 내용을 자연스럽게 읽는 버전 (없으면 빈 문자열)
tags_ko: 5개 (건강상식연구소 포함, 주제 관련)

JSON만 출력 (마크다운/설명 없이):
{{
  "title": "{title}",
  "content_type": "건강상식",
  "hook": "Hook 문장 (15자 이내)",
  "scenes": [
    {{"duration": 3, "caption": "Hook 자막\\n두 줄로", "narration": "Hook 나레이션", "image_prompt": "cute cartoon health character, bright colorful Korean health infographic style, 9:16 vertical portrait..."}},
    {{"duration": 5, "caption": "과학설명1\\n→ 효과 수치", "narration": "나레이션", "image_prompt": "..."}},
    {{"duration": 6, "caption": "과학설명2\\n→ 추가 효과 이모지", "narration": "나레이션", "image_prompt": "..."}},
    {{"duration": 5, "caption": "잘못된 상식\\n반전 설명 ⚠️", "narration": "나레이션", "image_prompt": "..."}},
    {{"duration": 3, "caption": "감정충격 문장 😱", "narration": "나레이션", "image_prompt": "..."}},
    {{"duration": 2, "caption": "저장유도 💾", "narration": "나레이션", "image_prompt": "..."}},
    {{"duration": 2, "caption": "처음부터 보면 복선 있음 👀", "narration": "", "image_prompt": "..."}}
  ],
  "total_duration": 25,
  "save_trigger": "저장유도 문장",
  "loop_trigger": "처음부터 보면 복선 있음 👀",
  "tags_ko": ["건강상식연구소", "건강", "쇼츠", "건강습관", "주제태그"]
}}"""


def generate_script(topic: dict) -> dict:
    import anthropic
    sys.path.insert(0, str(BASE_DIR))
    from config import CLAUDE_API_KEY

    client = anthropic.Anthropic(api_key=CLAUDE_API_KEY)
    prompt = _build_prompt(topic)

    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )
    text = msg.content[0].text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return json.loads(text.strip())


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

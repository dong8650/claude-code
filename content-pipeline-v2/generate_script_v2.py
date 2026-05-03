"""
generate_script_v2.py
=====================
S급 유튜브 쇼츠 대본 생성 (Claude API 전용)

콘텐츠 타입:
  건강상식 — 25초: Hook → 과학설명 → 잘못된상식반전 → 감정충격 → 저장유도 → 루프트리거
  명대사   — 10초: Hook → 대사 → 저장유도 → 루프트리거  (드라마, 레거시)
  복선해석 — 20초: Hook → 복선설명 → 소름포인트 → 루프트리거  (드라마, 레거시)
  반전요약 — 20초: Hook → 1화vs마지막 → 반전 → 감정충격 → 루프트리거  (드라마, 레거시)
"""
import json
import re
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent
USED_FILE = BASE_DIR / "drama_used.json"


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


def _build_health_prompt(topic: dict) -> str:
    title = topic["title"]
    theme = topic.get("theme", "")
    myth = topic.get("myth", "")

    return f"""건강 상식 연구소 채널의 S급 유튜브 쇼츠 대본을 만들어줘.

주제: {title}
테마: {theme}
잘못된 상식 (반전 포인트): {myth}

S급 조건:
- 총 길이: 25초
- Hook (0~2초): "의사들이 매일 하는데 우리만 모르는" 또는 "이거 알면 병원 덜 가도 됨" 류. 멈추게 만드는 문장.
- 과학설명 (3~12초): 짧고 임팩트 있는 과학적 근거 2~3개. 자막에 "→" 기호와 수치 적극 활용.
- 잘못된상식 반전 (13~17초): "근데 대부분이 이렇게 한다..." 또는 "반대로 하면?" 전환
- 감정충격 (18~20초): "매일 이렇게 했던 당신..." 공감 유발
- 저장유도 (21~23초): "저장해두고 내일부터 해봐" 류
- 루프트리거 (24~25초): "처음부터 보면 이미 알고 있었음 👀" 류
- image_prompt: DALL-E용 영문. 귀여운 장기 캐릭터 또는 건강 인포그래픽 스타일. 밝고 컬러풀.
- narration: 각 장면 나레이션 (간결하게)
- tags_ko: 5개 (건강상식연구소 포함)

JSON만 출력 (마크다운/설명 없이):
{{
  "title": "{title}",
  "content_type": "건강상식",
  "hook": "Hook 문장 (15자 이내)",
  "scenes": [
    {{"duration": 2, "caption": "Hook 자막", "narration": "Hook 나레이션", "image_prompt": "cute cartoon health character, bright colorful Korean health infographic style, 9:16 vertical..."}},
    {{"duration": 5, "caption": "과학설명1\\n→ 효과1", "narration": "나레이션", "image_prompt": "..."}},
    {{"duration": 5, "caption": "과학설명2\\n→ 효과2 💧", "narration": "나레이션", "image_prompt": "..."}},
    {{"duration": 5, "caption": "잘못된 상식\\n반전 설명 ⚠️", "narration": "나레이션", "image_prompt": "..."}},
    {{"duration": 3, "caption": "감정충격 문장 😱", "narration": "나레이션", "image_prompt": "..."}},
    {{"duration": 3, "caption": "저장유도 💾", "narration": "나레이션", "image_prompt": "..."}},
    {{"duration": 2, "caption": "루프트리거 👀", "narration": "", "image_prompt": "..."}}
  ],
  "total_duration": 25,
  "save_trigger": "저장유도 문장",
  "loop_trigger": "루프트리거 문장",
  "tags_ko": ["건강상식연구소", "건강", "쇼츠", "건강습관", "건강상식"]
}}"""


def _build_prompt(topic: dict) -> str:
    if topic.get("content_type") == "건강상식":
        return _build_health_prompt(topic)

    drama = topic["drama"]
    content_type = topic["content_type"]
    mood = topic["mood"]
    theme = topic["theme"]

    mood_guide = {
        "dark_intense":    "어둡고 강렬한, 긴장감 있는",
        "emotional_warm":  "감성적이고 따뜻한, 눈물 유발",
        "warm_inspiring":  "따뜻하고 영감을 주는",
        "quiet_deep":      "조용하고 깊은, 여운 남는",
        "nostalgic_youth": "청춘의 아련함, 추억 자극",
        "dark_thriller":   "어둡고 스릴 있는",
        "epic_emotional":  "웅장하고 감동적인",
        "healing_warm":    "치유되는, 따뜻한",
        "romantic_warm":   "설레는, 로맨틱한",
        "emotional_heavy": "무겁고 진한 감정",
        "healing_quiet":   "조용히 위로해주는",
        "romantic_epic":   "운명적이고 로맨틱한",
        "dark_action":     "강렬하고 액션 있는",
        "dark_historical": "역사적 긴장감, 어두운",
        "warm_cozy":       "포근하고 아늑한",
        "sharp_empathy":   "날카롭고 공감되는",
        "historical_epic": "역사 서사, 웅장한",
        "witty_deep":      "위트 있고 깊은",
        "realistic_quiet": "현실적이고 담담한",
    }.get(mood, "감성적인")

    if content_type == "명대사":
        return f"""드라마 '{drama}' 의 S급 유튜브 쇼츠 대본을 만들어줘.

콘텐츠 타입: 명대사 (10초)
테마: {theme}
분위기: {mood_guide}

S급 조건:
- Hook (0~2초): 시청자가 "나도!" 또는 "맞아!" 를 외치게 만드는 문장. 질문형 또는 공감형.
- 핵심 대사 (3~6초): 드라마 실제 명대사 또는 그 분위기의 임팩트 있는 문장 (2줄 이내)
- 저장유도 (7~9초): "저장해두고 힘들 때 꺼내봐요" 류의 감성 문장
- 루프트리거 (10초): "처음부터 다시 보면 소름 돋음 👀" 류 — 반복 시청 유발
- image_prompt: DALL-E용 영문 프롬프트. 실제 배우/캐릭터 이름 절대 금지. 분위기/감정만 묘사.
- narration: 감정을 실어 읽는 짧은 나레이션 (없으면 빈 문자열)
- tags_ko: 5개 (드라마명 포함)

JSON만 출력 (마크다운/설명 없이):
{{
  "drama": "{drama}",
  "content_type": "명대사",
  "hook": "Hook 문장 (12자 이내)",
  "scenes": [
    {{"duration": 2, "caption": "Hook 자막", "narration": "", "image_prompt": "cinematic Korean drama atmosphere, ..."}},
    {{"duration": 4, "caption": "핵심 대사\\n(2줄)", "narration": "나레이션", "image_prompt": "..."}},
    {{"duration": 3, "caption": "저장유도 문장", "narration": "나레이션", "image_prompt": "..."}},
    {{"duration": 1, "caption": "루프트리거 👀", "narration": "", "image_prompt": "..."}}
  ],
  "total_duration": 10,
  "save_trigger": "저장유도 문장",
  "loop_trigger": "루프트리거 문장",
  "tags_ko": ["{drama.replace(' ', '')}", "명대사", "쇼츠", "드라마", "공감"]
}}"""

    elif content_type == "복선해석":
        return f"""드라마 '{drama}' 의 S급 유튜브 쇼츠 대본을 만들어줘.

콘텐츠 타입: 복선해석 (20초)
테마: {theme}
분위기: {mood_guide}

S급 조건:
- Hook (0~2초): "이 장면이 복선인 거 아무도 말 안 해줬음" 류. 멈추게 만들기.
- 복선1 (3~8초): 초반부 장면 묘사 + 왜 복선인지 설명
- 복선2 (9~14초): "그런데 알고보면..." 전환 + 결말과의 연결
- 소름포인트 (15~17초): "복선이었다..." 감정 극대화
- 저장유도 (18~19초): "저장 안 하면 다시 못 찾음"
- 루프트리거 (20초): "1초에 힌트 숨겨져 있음 👀"
- image_prompt: 실제 배우 금지, 분위기/감정 묘사만

JSON만 출력:
{{
  "drama": "{drama}",
  "content_type": "복선해석",
  "hook": "Hook 문장 (15자 이내)",
  "scenes": [
    {{"duration": 2, "caption": "Hook", "narration": "", "image_prompt": "..."}},
    {{"duration": 6, "caption": "복선 장면 설명", "narration": "나레이션", "image_prompt": "..."}},
    {{"duration": 6, "caption": "그런데 알고보면...\\n결말 연결", "narration": "나레이션", "image_prompt": "..."}},
    {{"duration": 3, "caption": "복선이었다...", "narration": "나레이션", "image_prompt": "..."}},
    {{"duration": 2, "caption": "저장유도", "narration": "", "image_prompt": "..."}},
    {{"duration": 1, "caption": "루프트리거 👀", "narration": "", "image_prompt": "..."}}
  ],
  "total_duration": 20,
  "save_trigger": "저장유도 문장",
  "loop_trigger": "루프트리거 문장",
  "tags_ko": ["{drama.replace(' ', '')}", "복선해석", "쇼츠", "드라마", "소름"]
}}"""

    else:  # 반전요약
        return f"""드라마 '{drama}' 의 S급 유튜브 쇼츠 대본을 만들어줘.

콘텐츠 타입: 반전요약 (20초)
테마: {theme}
분위기: {mood_guide}

S급 조건:
- Hook (0~2초): "이 드라마 1화 vs 마지막화, 같은 장면인데 의미가 다름" 류
- 1화 장면 (3~7초): 초반부 장면 설명 (짧고 빠르게)
- 반전포인트 (8~13초): "그런데 알고보면..." BGM 전환 느낌
- 감정충격 (14~17초): "복선이었다..." 슬로우모션 느낌
- 저장유도 (18~19초)
- 루프트리거 (20초)

JSON만 출력:
{{
  "drama": "{drama}",
  "content_type": "반전요약",
  "hook": "Hook 문장 (15자 이내)",
  "scenes": [
    {{"duration": 2, "caption": "Hook", "narration": "", "image_prompt": "..."}},
    {{"duration": 5, "caption": "1화 장면 설명", "narration": "나레이션", "image_prompt": "..."}},
    {{"duration": 6, "caption": "그런데 알고보면...", "narration": "나레이션", "image_prompt": "..."}},
    {{"duration": 4, "caption": "감정충격 문장", "narration": "나레이션", "image_prompt": "..."}},
    {{"duration": 2, "caption": "저장유도", "narration": "", "image_prompt": "..."}},
    {{"duration": 1, "caption": "루프트리거 👀", "narration": "", "image_prompt": "..."}}
  ],
  "total_duration": 20,
  "save_trigger": "저장유도 문장",
  "loop_trigger": "루프트리거 문장",
  "tags_ko": ["{drama.replace(' ', '')}", "반전요약", "쇼츠", "드라마", "소름"]
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
    pool_file = BASE_DIR / "topics_drama.json"
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
        "drama": topic["drama"],
        "content_type": topic["content_type"],
        "script": script,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()

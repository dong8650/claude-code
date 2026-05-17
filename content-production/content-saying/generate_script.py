"""
generate_script.py
==================
명언 선택 → Claude가 원문(독일어)에서 직접 번역 + echo(여운) 한마디 생성

저작권 정책:
  원문(독일어)은 공개 도메인이지만 기존 한국어 출판 번역본은 저작권 있음.
  매 에피소드마다 Claude가 원문에서 새로 의역 → 출판사 번역본 미사용.
"""
import json
import os
import random
import sys
from pathlib import Path

import anthropic

sys.path.insert(0, "/root/content/runtime/saying")
from config import CLAUDE_API_KEY, RUNTIME_DIR

TOPICS_FILE = Path(RUNTIME_DIR) / "topics_saying.json"
USED_FILE   = Path(RUNTIME_DIR) / "saying_used.json"

_TRANSLATE_PROMPT = """\
다음 철학자 명언을 한국어로 재창작해줘.

철학자: {philosopher} (책: {book_en})
원문: "{original}"
테마: {theme}

재창작 규칙:
- 기존 출판된 한국어 번역본 표현을 그대로 사용하지 말 것 (저작권)
- 원문의 핵심 의미를 살리되, Dark Academia 스타일로 재창작 — 웅장하고 선언적인 문장
- 2~3문장, 80자 이내
- 첫 문장: 충격적 선언 / 둘째 문장: 구체적 전개나 이유 / 셋째 문장(선택): 반전 또는 귀결
- 각 문장이 독립적으로 강렬하고, 전체가 하나의 흐름을 이룰 것
- 번역체·문어체·수동형 금지 — 직접적이고 능동적인 현재형
- "우리는", "그들은"보다 "당신은", "나는" 등 2인칭/1인칭 선호
- 따옴표 없이 재창작 문장만 출력"""

_INTRO_PATTERNS = {
    "니체": [
        "니체가 말했다",
        "철학자 니체가 남긴 말",
        "니체는 이렇게 말했다",
        "프리드리히 니체가 말했다",
    ],
    "쇼펜하우어": [
        "쇼펜하우어가 말했다",
        "철학자 쇼펜하우어가 남긴 말",
        "쇼펜하우어는 이렇게 말했다",
        "아르투르 쇼펜하우어가 말했다",
    ],
}

_ECHO_PROMPT = """\
철학자 {philosopher}의 다음 명언을 보고, 인스타그램·유튜브에서 스크롤을 멈추게 하는 여운 한마디를 만들어줘.

명언: "{quote_ko}"
테마: {theme}

규칙:
- 15자 이내, 완전한 문장
- 아래 3가지 패턴 중 하나 선택:
  1. 공격형 (도발 — 반박 불가): "편안함이 당신을 죽이고 있다"
  2. 공감형 (나 얘기다): "혼자가 편한 게 잘못이 아니다"
  3. 질문형 (불편한 거울): "당신은 지금 생각하고 있나"
- Dark Academia 톤 — 웅장하고 선언적, 감상적 금지
- "저장", "좋아요", "공유" 유도 금지
- 추상적 철학 용어 금지 — 일상 언어로
- 스크린샷 찍고 싶을 만큼 강렬할 것

여운 한마디만 출력 (따옴표 없이):"""


def _load_used() -> list:
    if USED_FILE.exists():
        return json.loads(USED_FILE.read_text())
    return []


def _save_used(used: list):
    USED_FILE.write_text(json.dumps(used, ensure_ascii=False, indent=2))


def _pick_topic(philosopher: str = None) -> dict:
    topics = json.loads(TOPICS_FILE.read_text())
    used   = _load_used()

    pool = [t for t in topics if t["id"] not in used]
    if philosopher:
        pool = [t for t in pool if t["philosopher"] == philosopher]

    if not pool:
        print("⚠️  사용된 명언 전부 소진 — 리셋 후 재시작")
        used_ids = _load_used()
        if philosopher:
            reset_ids = [t["id"] for t in topics if t["philosopher"] == philosopher]
        else:
            reset_ids = [t["id"] for t in topics]
        new_used = [i for i in used_ids if i not in reset_ids]
        _save_used(new_used)
        pool = [t for t in topics if t["id"] not in new_used]
        if philosopher:
            pool = [t for t in pool if t["philosopher"] == philosopher]

    return random.choice(pool)


def _translate_quote(topic: dict) -> str:
    """원문(독일어)에서 직접 AI 의역 — 출판사 번역본 미사용."""
    client = anthropic.Anthropic(api_key=CLAUDE_API_KEY)
    prompt = _TRANSLATE_PROMPT.format(
        philosopher=topic["philosopher"],
        book_en=topic["book_en"],
        original=topic["original"],
        theme=topic["theme"],
    )
    msg = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=200,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text.strip().strip('"').strip("'")


def _generate_echo(topic: dict) -> str:
    client = anthropic.Anthropic(api_key=CLAUDE_API_KEY)
    prompt = _ECHO_PROMPT.format(
        philosopher=topic["philosopher"],
        quote_ko=topic["quote_ko"],
        theme=topic["theme"],
    )
    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=100,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text.strip().strip('"').strip("'")


def generate_script(philosopher: str = None, ep_dir: str = None) -> dict:
    topic     = _pick_topic(philosopher)
    quote_ko  = _translate_quote(topic)       # 원문에서 직접 AI 의역
    topic_for_echo = dict(topic, quote_ko=quote_ko)
    echo      = _generate_echo(topic_for_echo)
    intro     = random.choice(_INTRO_PATTERNS.get(topic["philosopher"], [topic["philosopher"]]))

    script = {
        "ep_id":          ep_dir,
        "topic_id":       topic["id"],
        "philosopher":    topic["philosopher"],
        "philosopher_en": topic["philosopher_en"],
        "book":           topic["book"],
        "book_en":        topic["book_en"],
        "original":       topic["original"],
        "theme":          topic["theme"],
        "image_set":      topic["image_set"],
        "intro_ko":       intro,
        "quote_ko":       quote_ko,
        "echo_ko":        echo,
    }

    if ep_dir:
        Path(ep_dir).mkdir(parents=True, exist_ok=True)
        (Path(ep_dir) / "script.json").write_text(
            json.dumps(script, ensure_ascii=False, indent=2)
        )

    used = _load_used()
    used.append(topic["id"])
    _save_used(used)

    print(f"  📖 [{topic['philosopher']}] {quote_ko[:30]}...")
    print(f"  ✨ echo: {echo}")
    return script


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--philosopher", choices=["니체", "쇼펜하우어"])
    p.add_argument("--ep", default="/tmp/saying_test")
    args = p.parse_args()
    s = generate_script(philosopher=args.philosopher, ep_dir=args.ep)
    print(json.dumps(s, ensure_ascii=False, indent=2))

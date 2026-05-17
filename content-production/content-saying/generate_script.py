"""
generate_script.py
==================
명언 선택 → Claude가 echo(여운) 한마디 생성
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

_INTRO_PATTERNS = {
    "니체":       ["니체가 말했다", "니체의 말", "프리드리히 니체"],
    "쇼펜하우어": ["쇼펜하우어가 말했다", "쇼펜하우어의 말", "아르투르 쇼펜하우어"],
}

_ECHO_PROMPT = """\
철학자 {philosopher}의 다음 명언을 보고, 30~40대 직장인이 오늘 하루를 돌아볼 수 있는 여운 한마디를 만들어줘.

명언: "{quote_ko}"
테마: {theme}

규칙:
- 15자 이내, 완전한 문장
- 질문형 또는 선언형 (택1)
- "저장", "좋아요", "공유" 유도 금지
- 추상적 철학 용어 금지 — 일상 언어로
- 예시 (질문형): "당신의 혼돈은 무엇인가"
- 예시 (선언형): "지금 이 순간, 충분하다"

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
    topic  = _pick_topic(philosopher)
    echo   = _generate_echo(topic)
    intro  = random.choice(_INTRO_PATTERNS.get(topic["philosopher"], [topic["philosopher"]]))

    script = {
        "ep_id":        ep_dir,
        "topic_id":     topic["id"],
        "philosopher":  topic["philosopher"],
        "philosopher_en": topic["philosopher_en"],
        "book":         topic["book"],
        "book_en":      topic["book_en"],
        "original":     topic["original"],
        "theme":        topic["theme"],
        "image_set":    topic["image_set"],
        "intro_ko":     intro,
        "quote_ko":     topic["quote_ko"],
        "echo_ko":      echo,
    }

    if ep_dir:
        Path(ep_dir).mkdir(parents=True, exist_ok=True)
        (Path(ep_dir) / "script.json").write_text(
            json.dumps(script, ensure_ascii=False, indent=2)
        )

    used = _load_used()
    used.append(topic["id"])
    _save_used(used)

    print(f"  📖 [{topic['philosopher']}] {topic['quote_ko'][:30]}...")
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

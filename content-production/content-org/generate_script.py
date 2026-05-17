"""
generate_script.py
==================
주제 선택 → Claude 대본 생성 (재창작 + echo 여운)

TODO: 아래 항목 채널에 맞게 수정
  - CHANNEL_ID
  - INTRO_PATTERNS
  - _MAIN_PROMPT
  - _ECHO_PROMPT
"""
import json
import os
import random
import sys
from pathlib import Path

import anthropic

# TODO: 채널명으로 변경
CHANNEL_ID = "org"

sys.path.insert(0, f"/root/content/runtime/{CHANNEL_ID}")
from config import CLAUDE_API_KEY, RUNTIME_DIR

TOPICS_FILE = Path(RUNTIME_DIR) / f"topics_{CHANNEL_ID}.json"
USED_FILE   = Path(RUNTIME_DIR) / f"{CHANNEL_ID}_used.json"

# ── 대본 생성 프롬프트 ─────────────────────────────────────
# TODO: 채널 포맷에 맞게 수정
# 현재: Dark Academia 재창작 스타일 (content-saying 기반)
_MAIN_PROMPT = """\
다음 원문을 한국어로 재창작해줘.

주제: {subject} ({title_en})
원문: "{original}"
테마: {theme}

재창작 규칙:
- 기존 출판 번역본 표현을 그대로 사용하지 말 것 (저작권)
- 원문의 핵심 의미를 살리되, Dark Academia 스타일로 재창작
- 웅장하고 선언적인 문장 — 직접적이고 능동적인 현재형
- "우리는"보다 "당신은", "나는" 등 2인칭/1인칭 선호
- 1~2문장, 40자 이내로 간결하게
- 영상 자막으로 읽혔을 때 충격이 있을 것
- 따옴표 없이 재창작 문장만 출력"""

# ── 여운 생성 프롬프트 ─────────────────────────────────────
# TODO: 채널 톤에 맞게 수정
# 현재: 바이럴 3패턴 — 공격형/공감형/질문형
_ECHO_PROMPT = """\
다음 명언을 보고, 인스타그램·유튜브에서 스크롤을 멈추게 하는 여운 한마디를 만들어줘.

명언: "{main_ko}"
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
- 따옴표 없이 출력"""

# ── 도입부 패턴 ────────────────────────────────────────────
# TODO: 채널 화자/주제에 맞게 수정
# key: topics JSON의 subject 값과 일치시킬 것
INTRO_PATTERNS = {
    "기본": [
        "오늘의 이야기",
        "이런 말이 있다",
        "잠깐 들어봐",
    ],
    # 예시: 철학자 채널
    # "니체": ["니체가 말했다", "프리드리히 니체가 남긴 말"],
    # 예시: 역사 채널
    # "링컨": ["에이브러햄 링컨이 말했다", "링컨의 말"],
}


def _load_used() -> list:
    if USED_FILE.exists():
        return json.loads(USED_FILE.read_text())
    return []


def _save_used(used: list):
    USED_FILE.write_text(json.dumps(used, ensure_ascii=False, indent=2))


def _pick_topic(subject: str = None) -> dict:
    topics = json.loads(TOPICS_FILE.read_text())
    used   = _load_used()

    pool = [t for t in topics if t["id"] not in used and not t.get("_comment")]
    if subject:
        pool = [t for t in pool if t["subject"] == subject]

    if not pool:
        print("⚠️  사용된 항목 전부 소진 — 리셋 후 재시작")
        used_ids = _load_used()
        if subject:
            reset_ids = [t["id"] for t in topics if t["subject"] == subject]
        else:
            reset_ids = [t["id"] for t in topics if not t.get("_comment")]
        new_used = [i for i in used_ids if i not in reset_ids]
        _save_used(new_used)
        pool = [t for t in topics if t["id"] not in new_used and not t.get("_comment")]
        if subject:
            pool = [t for t in pool if t["subject"] == subject]

    return random.choice(pool)


def _generate_main(topic: dict) -> str:
    """원문 → AI 재창작."""
    client = anthropic.Anthropic(api_key=CLAUDE_API_KEY)
    prompt = _MAIN_PROMPT.format(
        subject=topic["subject"],
        title_en=topic["title_en"],
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
        main_ko=topic["main_ko"],
        theme=topic["theme"],
    )
    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=100,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text.strip().strip('"').strip("'")


def generate_script(subject: str = None, ep_dir: str = None) -> dict:
    topic   = _pick_topic(subject)
    main_ko = _generate_main(topic)

    topic_for_echo = dict(topic, main_ko=main_ko)
    echo  = _generate_echo(topic_for_echo)

    patterns = INTRO_PATTERNS.get(topic["subject"], INTRO_PATTERNS.get("기본", [topic["subject"]]))
    intro = random.choice(patterns)

    script = {
        "ep_id":      ep_dir,
        "topic_id":   topic["id"],
        "subject":    topic["subject"],
        "subject_en": topic["subject_en"],
        "title":      topic["title"],
        "title_en":   topic["title_en"],
        "original":   topic["original"],
        "theme":      topic["theme"],
        "image_set":  topic["image_set"],
        # make_video.py / generate_tts.py 공통 필드명 유지
        "intro_ko":   intro,
        "quote_ko":   main_ko,
        "echo_ko":    echo,
    }

    if ep_dir:
        Path(ep_dir).mkdir(parents=True, exist_ok=True)
        (Path(ep_dir) / "script.json").write_text(
            json.dumps(script, ensure_ascii=False, indent=2)
        )

    used = _load_used()
    used.append(topic["id"])
    _save_used(used)

    print(f"  📖 [{topic['subject']}] {main_ko[:30]}...")
    print(f"  ✨ echo: {echo}")
    return script


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--subject")
    p.add_argument("--ep", default="/tmp/org_test")
    args = p.parse_args()
    s = generate_script(subject=args.subject, ep_dir=args.ep)
    print(json.dumps(s, ensure_ascii=False, indent=2))

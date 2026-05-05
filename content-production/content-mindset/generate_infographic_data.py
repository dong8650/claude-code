"""
generate_infographic_data.py
============================
매일 새로운 인포그래픽 주제를 선정하고 Claude API로 데이터를 생성.
- infographic_topic_pool.json에서 미사용 주제 선택 (전부 사용하면 리셋 후 재순환)
- Claude API로 랭킹/표 데이터 생성
- data_YYYYMMDD.json으로 저장
- stdout에 JSON 출력 (n8n SSH 노드 전용)
"""
import json
import re
import sys
from datetime import datetime
from pathlib import Path

BASE_DIR     = Path(__file__).parent
RUNTIME_DIR  = Path("/root/content/runtime/mindset")
POOL_FILE    = BASE_DIR / "infographic_data/infographic_topic_pool.json"
USED_FILE    = RUNTIME_DIR / "infographic_used.json"


def load_used() -> set:
    if not USED_FILE.exists():
        return set()
    return set(json.loads(USED_FILE.read_text(encoding="utf-8")).get("used_ids", []))


def save_used(used_ids: set):
    USED_FILE.write_text(
        json.dumps(
            {"used_ids": list(used_ids), "last_updated": datetime.now().strftime("%Y-%m-%d")},
            ensure_ascii=False, indent=2,
        ),
        encoding="utf-8",
    )


def pick_topic(pool: list, used_ids: set) -> tuple:
    unused = [t for t in pool if t["id"] not in used_ids]
    if not unused:
        used_ids = set()
        save_used(used_ids)
        unused = pool
    return unused[0], used_ids


def generate_data(topic: dict) -> dict:
    import anthropic
    sys.path.insert(0, str(BASE_DIR))
    from config import CLAUDE_API_KEY

    client = anthropic.Anthropic(api_key=CLAUDE_API_KEY)
    title = topic["title"]
    topic_type = topic.get("type", "ranking")

    if topic_type == "ranking":
        prompt = f"""한국 직장인/30~40대가 공감할 수 있는 인포그래픽 랭킹 데이터를 만들어줘.

주제: {title}

요구사항:
- items 정확히 8개, rank 1이 가장 공감/충격적인 항목
- label 12자 이내, value 수치나 짧은 표현 8자 이내, detail 공감 부연설명 20자 이내
- source 신뢰감 있는 출처 (직장인 설문, 통계청, 연구소 등 — 가상 가능)
- tags_ko 5개 (채널 성격: 매일의설계, 직장인, 쇼츠 포함)

JSON만 출력 (마크다운 블록, 설명 없이):
{{
  "title": "{title}",
  "subtitle": "임팩트 한 줄 문구 20자 이내",
  "type": "ranking",
  "items": [
    {{"rank": 1, "label": "항목명", "value": "수치", "detail": "부연설명"}},
    {{"rank": 2, "label": "항목명", "value": "수치", "detail": "부연설명"}},
    {{"rank": 3, "label": "항목명", "value": "수치", "detail": "부연설명"}},
    {{"rank": 4, "label": "항목명", "value": "수치", "detail": "부연설명"}},
    {{"rank": 5, "label": "항목명", "value": "수치", "detail": "부연설명"}},
    {{"rank": 6, "label": "항목명", "value": "수치", "detail": "부연설명"}},
    {{"rank": 7, "label": "항목명", "value": "수치", "detail": "부연설명"}},
    {{"rank": 8, "label": "항목명", "value": "수치", "detail": "부연설명"}}
  ],
  "source": "출처",
  "tags_ko": ["매일의설계", "직장인", "쇼츠", "태그4", "태그5"]
}}"""
    else:
        prompt = f"""한국 직장인/30~40대가 공감할 수 있는 인포그래픽 표 데이터를 만들어줘.

주제: {title}

요구사항:
- rows 6~8행, 각 셀 15자 이내
- source 신뢰감 있는 출처 (가상 가능)
- tags_ko 5개

JSON만 출력 (마크다운 블록, 설명 없이):
{{
  "title": "{title}",
  "subtitle": "임팩트 한 줄 문구 20자 이내",
  "type": "table",
  "headers": ["항목", "수치", "한마디"],
  "rows": [
    ["항목1", "수치1", "설명1"],
    ["항목2", "수치2", "설명2"]
  ],
  "source": "출처",
  "tags_ko": ["매일의설계", "직장인", "쇼츠", "태그4", "태그5"]
}}"""

    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    text = msg.content[0].text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return json.loads(text.strip())


def main():
    if not POOL_FILE.exists():
        print(json.dumps({"error": "no_pool_file"}, ensure_ascii=False))
        sys.exit(1)

    pool = json.loads(POOL_FILE.read_text(encoding="utf-8"))
    used_ids = load_used()
    topic, used_ids = pick_topic(pool, used_ids)

    try:
        data = generate_data(topic)
    except Exception as e:
        print(json.dumps({"error": f"generate_failed: {e}"}, ensure_ascii=False))
        sys.exit(1)

    today = datetime.now().strftime("%Y%m%d")
    out_file = f"data_{today}.json"
    out_path = RUNTIME_DIR / out_file
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    used_ids.add(topic["id"])
    save_used(used_ids)

    print(json.dumps({
        "data_file": str(out_path),
        "topic_id": topic["id"],
        "title": data.get("title", topic["title"]),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()

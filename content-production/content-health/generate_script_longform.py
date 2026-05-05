"""
generate_script_longform.py
============================
건강 상식 연구소 — 롱폼 상세 대본 생성 (Claude API)
씬 15~20개, 시간 제한 없음 (목표 2~5분), 정보 전달 최우선
세로형 9:16 (make_video_v2.py 그대로 사용)
"""
import json
import re
import sys
from pathlib import Path

BASE_DIR    = Path(__file__).parent
RUNTIME_DIR = Path("/root/content/runtime/health")


def _build_prompt(topic: dict) -> str:
    title = topic["title"]
    theme = topic.get("theme", "")
    myth  = topic.get("myth", "")

    return f"""너는 유튜브 건강 교육 전문가. 시청자가 처음부터 끝까지 보는 정보 밀도 높은 세로형 롱폼 영상 대본 작성.
모바일 세로 영상 (9:16), 총 길이 2~5분 목표.

주제: {title}
테마: {theme}
잘못된 상식 (반전 포인트): {myth}

━━━ 롱폼 구조 (총 15~20장면) ━━━
①  Hook (1씬, ~4초)             — 강한 질문 또는 충격 사실. 끝까지 보게 만드는 약속
②  문제 제기 (2씬, ~10초)       — 왜 이게 중요한가. 일상 속 실제 상황 공감 유발
③  핵심 메커니즘 (5~7씬, ~40초) — 과학적 설명. 씬마다 수치·근거 1개씩. 쉬운 비유 활용
④  잘못된 상식 반전 (2~3씬, ~20초) — 대중이 믿는 것 vs 실제. "근데 대부분은..."
⑤  실용 팁 (3~4씬, ~25초)      — 오늘 바로 적용할 수 있는 구체적 방법 (수치 포함)
⑥  감정 마무리 (1씬, ~4초)      — "이걸 알았으니 당신은 이제 다르다" 승리감
⑦  좋아요+저장유도 (1씬, ~3초)  — "공감됐으면 좋아요 누르고 저장해둬 💾👍"
⑧  루프트리거 (1씬, ~2초)       — Hook 복선 재언급. "첫 장면에서 ..." 구체적으로

━━━ caption 규칙 ━━━
- 3줄 이내, 핵심만
- → 기호로 인과관계 표현
- 수치 필수 (신뢰감)

━━━ narration 규칙 ━━━
- 자연스러운 대화체
- caption 내용 빠짐없이 포함
- 씬당 1~2문장 (duration에 맞게)
- 큰따옴표(") 사용 금지 — 작은따옴표(') 또는 다른 표현으로 대체

━━━ JSON 출력 규칙 (필수) ━━━
- 문자열 내 줄바꿈은 반드시 \\n 으로 표현 (리터럴 줄바꿈 금지)
- 문자열 내 큰따옴표 사용 금지
- 이모지 사용 금지 (텍스트만)

━━━ image_style 규칙 (쇼츠와 동일) ━━━
"photo"   — 현실에서 찍을 수 있는 장면 (운동, 생활, 행동). 사람은 뒷모습·실루엣만.
"digital" — 눈에 보이지 않는 내부 메커니즘 (뇌·세포·신호·장기·화학물질). neon glow 스타일.
"object"  — 사람 없이 오브젝트로 상황 암시. 감정충격·부정씬 필수.
공통: DALL-E 3 영문 프롬프트, 9:16 portrait, NO text in image, NO real human faces

JSON만 출력 (마크다운/설명 없이):
{{
  "title": "{title}",
  "video_type": "longform",
  "content_type": "건강상식",
  "hook": "Hook 문장",
  "scenes": [
    {{"duration": 4, "caption": "자막\\n2~3줄", "narration": "자연스러운 대화체 나레이션", "pexels_query": "2-3 English keywords for Pexels photo search (simple nouns, e.g. runner road, brain neurons, phone neck, sleeping person)"}}
  ],
  "total_duration": 180,
  "save_trigger": "저장유도 문장",
  "loop_trigger": "루프트리거 문장 (Hook 복선 구체적 언급)",
  "tags_ko": ["건강상식연구소", "건강", "태그들"]
}}"""


def generate_longform_script(topic: dict) -> dict:
    import anthropic
    sys.path.insert(0, str(RUNTIME_DIR))
    from config import CLAUDE_API_KEY

    client = anthropic.Anthropic(api_key=CLAUDE_API_KEY)
    prompt = _build_prompt(topic)

    print(f"  📝 롱폼 대본 생성 중... (목표 15~20씬, 2~5분)")
    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=8192,
        messages=[{"role": "user", "content": prompt}],
    )

    text = msg.content[0].text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    text = text.strip()

    try:
        script = json.loads(text)
    except json.JSONDecodeError:
        # 문자열 내 이스케이프 안 된 줄바꿈 수정 후 재시도
        cleaned = re.sub(r'(?<=["\w])\n(?=[^{}\[\]]*["\w])', r'\\n', text)
        script = json.loads(cleaned)

    n_scenes = len(script.get("scenes", []))
    total    = script.get("total_duration", 0)
    print(f"  ✅ 롱폼 대본 완성 — {n_scenes}씬, 예상 {total}초 ({total//60}분 {total%60}초)")
    return script

"""
analyze_competitor.py
=====================
경쟁 채널 쇼츠 분석 — yt-dlp + Claude API

1. yt-dlp로 한국 건강 쇼츠 상위 영상 메타데이터 수집
2. Claude로 Hook 패턴 분류 (정체성공격 / 전문가반전 / 잘못된상식직격)
3. competitor_insights.json 생성 → generate_script_v2.py가 참고

실행:
  cd /root/claude-code/content-production/content-health
  python3 analyze_competitor.py              # 분석 + 저장
  python3 analyze_competitor.py --report     # 저장된 분석 결과만 출력

권장: 매주 1회 실행 (n8n 주간 트리거 또는 수동)
"""
import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

BASE_DIR    = Path(__file__).parent
RUNTIME_DIR = Path("/root/content/runtime/health")
INSIGHTS_FILE = RUNTIME_DIR / "competitor_insights.json"

# 검색 쿼리 — 한국 건강 쇼츠 상위권 크롤링 대상
SEARCH_QUERIES = [
    "잘못된 건강 상식 쇼츠",
    "의사가 알려주는 건강 쇼츠",
    "건강 습관 쇼츠 충격",
    "건강 상식 반전 쇼츠",
    "매일 이렇게 했던 건강",
]
VIDEOS_PER_QUERY = 15   # 쿼리당 수집 영상 수
MIN_VIEWS       = 5000  # 최소 조회수 필터
MAX_DURATION    = 65    # 쇼츠 최대 길이(초)
TOP_N           = 50    # 분석 대상 상위 N개


def _fetch_videos(query: str, count: int) -> list:
    """yt-dlp로 검색 결과 메타데이터 수집."""
    print(f"  🔍 검색: '{query}' ({count}개)...")
    cmd = [
        "yt-dlp", f"ytsearch{count}:{query}",
        "--dump-json", "--no-warnings", "-q", "--skip-download",
    ]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    except subprocess.TimeoutExpired:
        print(f"  ⚠️ 타임아웃: '{query}' 건너뜀")
        return []

    videos = []
    for line in r.stdout.strip().split("\n"):
        if not line.strip():
            continue
        try:
            v = json.loads(line)
            videos.append({
                "id":          v.get("id", ""),
                "title":       v.get("title", ""),
                "view_count":  int(v.get("view_count") or 0),
                "duration":    float(v.get("duration") or 0),
                "upload_date": v.get("upload_date", ""),
                "channel":     v.get("channel", ""),
                "url":         f"https://youtube.com/shorts/{v.get('id', '')}",
            })
        except (json.JSONDecodeError, ValueError):
            pass
    print(f"    → {len(videos)}개 수집")
    return videos


def collect_videos() -> list:
    """모든 쿼리 통합 수집 → 중복제거 → 필터링 → 상위 N개 반환."""
    all_videos = {}
    for q in SEARCH_QUERIES:
        for v in _fetch_videos(q, VIDEOS_PER_QUERY):
            vid_id = v["id"]
            if vid_id and vid_id not in all_videos:
                all_videos[vid_id] = v

    filtered = [
        v for v in all_videos.values()
        if v["view_count"] >= MIN_VIEWS and 0 < v["duration"] <= MAX_DURATION
    ]
    filtered.sort(key=lambda x: x["view_count"], reverse=True)
    result = filtered[:TOP_N]
    print(f"\n  📊 수집 완료: 전체 {len(all_videos)}개 → 필터 후 {len(filtered)}개 → 상위 {len(result)}개 분석")
    return result


def _analyze_with_claude(videos: list) -> dict:
    """Claude로 Hook 패턴 분류 및 인사이트 생성."""
    sys.path.insert(0, str(RUNTIME_DIR))
    from config import CLAUDE_API_KEY
    import anthropic

    client = anthropic.Anthropic(api_key=CLAUDE_API_KEY)

    # 영상 목록 텍스트 구성
    video_list = "\n".join(
        f"{i+1}. [{v['view_count']:,}회] \"{v['title']}\" ({v['duration']:.0f}초)"
        for i, v in enumerate(videos)
    )

    prompt = f"""아래는 한국 유튜브 건강 쇼츠 상위 {len(videos)}개 영상의 제목과 조회수야.

{video_list}

이 데이터를 분석해서 아래 JSON 형식으로 반환해줘.

분류 기준:
- identity_attack: "매일 이렇게 했던 당신..." 등 시청자 행동 공격
- expert_reversal: "의사가 말 안 해주는..." 등 전문가 정보 격차
- myth_direct: "사실 반대임", "알고 있었나요" 등 잘못된 상식 직격
- curiosity_gap: "이것만 알면..." 등 정보 격차 유발
- shock_number: 수치/통계 충격 ("하루 10분이면...")
- other: 위 분류에 해당 없음

JSON만 출력 (마크다운 없이):
{{
  "hook_type_stats": {{
    "identity_attack":  {{"count": 0, "avg_views": 0, "max_views": 0, "best_title": ""}},
    "expert_reversal":  {{"count": 0, "avg_views": 0, "max_views": 0, "best_title": ""}},
    "myth_direct":      {{"count": 0, "avg_views": 0, "max_views": 0, "best_title": ""}},
    "curiosity_gap":    {{"count": 0, "avg_views": 0, "max_views": 0, "best_title": ""}},
    "shock_number":     {{"count": 0, "avg_views": 0, "max_views": 0, "best_title": ""}},
    "other":            {{"count": 0, "avg_views": 0, "max_views": 0, "best_title": ""}}
  }},
  "top_hooks": [
    {{"rank": 1, "title": "", "views": 0, "hook_type": "", "why_works": ""}}
  ],
  "key_phrases": ["고성과 제목에서 자주 나오는 문구 10개"],
  "winning_hook_type": "가장 평균 조회수 높은 hook_type",
  "recommendation": "우리 채널 Hook 작성에 적용할 핵심 인사이트 3줄"
}}"""

    print("  🤖 Claude 분석 중...")
    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )
    text = msg.content[0].text.strip()
    import re
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


def run_analysis() -> dict:
    print("\n[1/3] 📡 경쟁 채널 영상 수집...")
    videos = collect_videos()
    if not videos:
        print("❌ 수집된 영상 없음")
        sys.exit(1)

    print("\n[2/3] 🤖 Hook 패턴 분석 (Claude)...")
    analysis = _analyze_with_claude(videos)

    print("\n[3/3] 💾 인사이트 저장...")
    insights = {
        "generated_at":     datetime.now().isoformat(),
        "total_analyzed":   len(videos),
        "top_videos":       videos[:20],      # 상위 20개 원본 데이터
        "analysis":         analysis,
    }

    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    INSIGHTS_FILE.write_text(
        json.dumps(insights, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"  ✅ 저장: {INSIGHTS_FILE}")
    return insights


def print_report(insights: dict):
    a = insights.get("analysis", {})
    stats = a.get("hook_type_stats", {})

    print("\n" + "=" * 55)
    print("📊 경쟁 채널 Hook 패턴 분석 리포트")
    print(f"   수집일: {insights.get('generated_at', '')[:10]}")
    print(f"   분석 영상: {insights.get('total_analyzed', 0)}개")
    print("=" * 55)

    print("\n▶ Hook 타입별 성과:")
    for htype, stat in sorted(stats.items(), key=lambda x: x[1].get("avg_views", 0), reverse=True):
        if stat.get("count", 0) == 0:
            continue
        print(f"  {htype:<20} | {stat['count']:>3}개 | 평균 {stat['avg_views']:>8,}회 | 최고 {stat['max_views']:>9,}회")
        if stat.get("best_title"):
            print(f"  {'':20}   └ \"{stat['best_title']}\"")

    print(f"\n▶ 최강 Hook 타입: {a.get('winning_hook_type', '?')}")

    print("\n▶ 고성과 제목 핵심 문구:")
    for phrase in a.get("key_phrases", []):
        print(f"  • {phrase}")

    print("\n▶ 우리 채널 적용 인사이트:")
    print(f"  {a.get('recommendation', '')}")

    print("\n▶ 상위 5개 Hook:")
    for item in a.get("top_hooks", [])[:5]:
        print(f"  #{item.get('rank','')} [{item.get('views',0):,}회] {item.get('hook_type','')}")
        print(f"     \"{item.get('title','')}\"")
        print(f"     → {item.get('why_works','')}")
    print("=" * 55)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", action="store_true", help="저장된 분석 결과 출력만")
    args = parser.parse_args()

    if args.report:
        if not INSIGHTS_FILE.exists():
            print("❌ 분석 결과 없음. 먼저 python3 analyze_competitor.py 실행")
            sys.exit(1)
        insights = json.loads(INSIGHTS_FILE.read_text(encoding="utf-8"))
        print_report(insights)
        return

    insights = run_analysis()
    print_report(insights)


if __name__ == "__main__":
    main()

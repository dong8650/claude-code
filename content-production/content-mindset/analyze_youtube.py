"""
analyze_youtube.py — YouTube Analytics 자동 분석
=================================================
채널 영상별 완시율·좋아요율·트래픽 소스 분석 → Claude API 패턴 분석

첫 실행:
  python3 analyze_youtube.py
  → 브라우저 URL 출력 → 인증코드 붙여넣기 → token 저장

이후 실행:
  python3 analyze_youtube.py          # 분석 실행
  python3 analyze_youtube.py --report # 저장된 결과만 출력 (API 호출 없음)
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# pipeline-core
_CORE = Path(__file__).parent.parent / "content-pipeline-core"
sys.path.insert(0, str(_CORE))

RUNTIME_DIR   = Path("/root/content/runtime/mindset")
CLIENT_SECRET = RUNTIME_DIR / "youtube_client_secret.json"
TOKEN_FILE    = RUNTIME_DIR / "youtube_analytics_token.json"
OUTPUT_FILE   = RUNTIME_DIR / "youtube_insights.json"

SCOPES = [
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
]


# ── 인증 ───────────────────────────────────────────────────

def get_credentials():
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request

    creds = None
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            print("✅ 토큰 갱신 완료")
        else:
            if not CLIENT_SECRET.exists():
                print(f"❌ {CLIENT_SECRET} 없음")
                print("   scp youtube_client_secret.json root@서버:/root/content/runtime/mindset/")
                sys.exit(1)

            flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRET), SCOPES)
            flow.redirect_uri = "urn:ietf:wg:oauth:2.0:oob"
            auth_url, _ = flow.authorization_url(prompt="consent", access_type="offline")

            print("\n" + "─" * 60)
            print("🔗 아래 URL을 브라우저에서 열어 Google 계정 인증:")
            print(auth_url)
            print("─" * 60)
            code = input("\n인증 코드 붙여넣기: ").strip()
            flow.fetch_token(code=code)
            creds = flow.credentials

        TOKEN_FILE.write_text(creds.to_json())
        print(f"✅ 인증 저장: {TOKEN_FILE}")

    return creds


# ── 데이터 수집 ─────────────────────────────────────────────

def get_channel_id(youtube):
    res = youtube.channels().list(part="id,snippet", mine=True).execute()
    ch  = res["items"][0]
    print(f"📺 채널: {ch['snippet']['title']}  ({ch['id']})")
    return ch["id"]


def get_all_videos(youtube, channel_id):
    videos, token = [], None
    while True:
        res = youtube.search().list(
            part="id,snippet", channelId=channel_id,
            type="video", maxResults=50, order="date", pageToken=token
        ).execute()
        for item in res.get("items", []):
            videos.append({
                "video_id":     item["id"]["videoId"],
                "title":        item["snippet"]["title"],
                "published_at": item["snippet"]["publishedAt"][:10],
            })
        token = res.get("nextPageToken")
        if not token:
            break
    print(f"📹 영상 {len(videos)}개 발견")
    return videos


def get_analytics(analytics, channel_id, video_ids, start_date, end_date):
    # YouTube Analytics API는 한 번에 200개 제한
    ids_str = ",".join(video_ids[:200])
    try:
        return analytics.reports().query(
            ids=f"channel=={channel_id}",
            startDate=start_date,
            endDate=end_date,
            metrics=(
                "views,estimatedMinutesWatched,"
                "averageViewDuration,averageViewPercentage,"
                "likes,subscribersGained"
            ),
            dimensions="video",
            filters=f"video=={ids_str}",
            maxResults=200,
        ).execute()
    except Exception as e:
        print(f"⚠️ Analytics 오류: {e}")
        return None


# ── Claude 분석 ────────────────────────────────────────────

def analyze_with_claude(video_data: list) -> str:
    try:
        spec = __import__("importlib.util", fromlist=["util"]).util
        m    = spec.spec_from_file_location("config", RUNTIME_DIR / "config.py")
        cfg  = spec.module_from_spec(m); m.loader.exec_module(cfg)
        api_key = cfg.ANTHROPIC_API_KEY
    except Exception:
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")

    if not api_key:
        return "(ANTHROPIC_API_KEY 없음 — Claude 분석 스킵)"

    import anthropic
    client = anthropic.Anthropic(api_key=api_key)

    ranked = sorted(video_data, key=lambda x: x["averageViewPercentage"], reverse=True)
    summary = {
        "total_videos": len(video_data),
        "channel_avg_completion_pct": round(
            sum(v["averageViewPercentage"] for v in video_data) / max(len(video_data), 1), 1
        ),
        "top5": [
            {
                "title":      v["title"],
                "completion": v["averageViewPercentage"],
                "views":      v["views"],
                "likes":      v["likes"],
            }
            for v in ranked[:5]
        ],
        "bottom5": [
            {
                "title":      v["title"],
                "completion": v["averageViewPercentage"],
                "views":      v["views"],
            }
            for v in ranked[-5:]
        ],
    }

    res = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1200,
        messages=[{
            "role": "user",
            "content": (
                "유튜브 쇼츠 채널 '매일의 설계' (@life-architecture) Analytics 데이터야.\n\n"
                f"{json.dumps(summary, ensure_ascii=False, indent=2)}\n\n"
                "아래 4가지를 분석해줘 (한국어, 실무 조언 수준으로 간결하게):\n"
                "1. 완시율 높은 영상의 공통점 (제목 패턴·콘텐츠 타입)\n"
                "2. 완시율 낮은 영상의 문제점\n"
                "3. S급(10만뷰) 달성을 위한 구체적 액션 3가지\n"
                "4. 다음에 만들어야 할 영상 타입 추천 (이유 포함)"
            ),
        }],
    )
    return res.content[0].text


# ── 리포트 출력 ────────────────────────────────────────────

def print_report(video_data: list, claude_analysis: str, period: str):
    avg = sum(v["averageViewPercentage"] for v in video_data) / max(len(video_data), 1)
    ranked = sorted(video_data, key=lambda x: x["averageViewPercentage"], reverse=True)

    print("\n" + "═" * 62)
    print(f"📊 완시율 랭킹  ({period})")
    print("═" * 62)
    for i, v in enumerate(ranked, 1):
        pct  = v["averageViewPercentage"]
        bar  = "█" * int(pct / 4)
        flag = " ← S급 후보 🔥" if pct >= 85 else ""
        print(f"{i:2}. {pct:5.1f}% {bar}{flag}")
        print(f"    {v['title'][:45]}")
        print(f"    조회수 {v['views']:,}  좋아요 {v['likes']:,}  구독 +{v['subscribersGained']}")
        print()

    print("─" * 62)
    delta = avg - 85
    sign  = "+" if delta >= 0 else ""
    print(f"채널 평균 완시율: {avg:.1f}%   (목표 85% 대비 {sign}{delta:.1f}%p)")
    print()

    if claude_analysis:
        print("═" * 62)
        print("🎯 Claude S급 전략 분석")
        print("═" * 62)
        print(claude_analysis)


# ── main ───────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", action="store_true", help="저장된 결과만 출력 (API 호출 없음)")
    parser.add_argument("--days",   type=int, default=90, help="분석 기간 (기본 90일)")
    args = parser.parse_args()

    # --report: 저장된 JSON만 출력
    if args.report:
        if not OUTPUT_FILE.exists():
            print("❌ 저장된 분석 없음. 먼저 python3 analyze_youtube.py 실행")
            sys.exit(1)
        data = json.loads(OUTPUT_FILE.read_text())
        print_report(data["videos"], data.get("claude_analysis", ""), data["period"])
        return

    # ── 실제 분석 실행 ──
    from googleapiclient.discovery import build

    print("📊 YouTube Analytics 분석 시작...\n")
    creds     = get_credentials()
    youtube   = build("youtube",          "v3", credentials=creds)
    analytics = build("youtubeAnalytics", "v2", credentials=creds)

    channel_id = get_channel_id(youtube)
    videos     = get_all_videos(youtube, channel_id)
    if not videos:
        print("❌ 영상 없음"); return

    end_date   = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=args.days)).strftime("%Y-%m-%d")
    period     = f"{start_date} ~ {end_date}"
    print(f"\n📈 Analytics 조회 중 ({period})...")

    video_ids      = [v["video_id"] for v in videos]
    analytics_data = get_analytics(analytics, channel_id, video_ids, start_date, end_date)

    # Analytics ↔ 영상 정보 합치기
    analytics_map = {}
    if analytics_data and "rows" in analytics_data:
        cols = [h["name"] for h in analytics_data["columnHeaders"]]
        for row in analytics_data["rows"]:
            d   = dict(zip(cols, row))
            vid = d.pop("video", "")
            analytics_map[vid] = d

    video_data = []
    for v in videos:
        m = analytics_map.get(v["video_id"], {})
        video_data.append({
            **v,
            "url":                   f"https://youtube.com/watch?v={v['video_id']}",
            "views":                 int(float(m.get("views", 0))),
            "averageViewPercentage": round(float(m.get("averageViewPercentage", 0)), 1),
            "averageViewDuration":   round(float(m.get("averageViewDuration", 0)), 1),
            "likes":                 int(float(m.get("likes", 0))),
            "subscribersGained":     int(float(m.get("subscribersGained", 0))),
        })

    print("\n🤖 Claude 패턴 분석 중...")
    claude_analysis = analyze_with_claude(video_data)

    # 결과 저장
    result = {
        "generated_at":            datetime.now().isoformat(),
        "period":                  period,
        "channel_avg_completion":  round(
            sum(v["averageViewPercentage"] for v in video_data) / max(len(video_data), 1), 1
        ),
        "videos":         video_data,
        "claude_analysis": claude_analysis,
    }
    OUTPUT_FILE.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"✅ 저장: {OUTPUT_FILE}\n")

    print_report(video_data, claude_analysis, period)


if __name__ == "__main__":
    main()

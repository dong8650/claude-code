# ════════════════════════════════════════════════════════
# KIS 모의투자 + 슬랙 알림 설정
# 이 파일을 secret_config.py 로 복사 후 값 입력
# ⚠️ secret_config.py 는 절대 git 에 올리지 말 것 (.gitignore 에 포함됨)
# ════════════════════════════════════════════════════════

KIS_CONFIG = {
    # KIS Developers 에서 발급받은 '모의투자' 앱키/시크릿
    "app_key"   : "여기에_모의투자_APP_KEY",
    "app_secret": "여기에_모의투자_APP_SECRET",

    # HTS 로그인 ID (KIS Developers 고객 ID)
    "hts_id"    : "여기에_HTS_ID",

    # 모의계좌번호 (형식: 00000000-01)
    "account"   : "00000000-01",

    # 모의투자 여부 (모의=True). 검증 전엔 절대 False 금지
    "virtual"   : True,
}

# 슬랙 Incoming Webhook URL (NEAI 봇과 동일 방식)
# 만드는 법: Slack → 앱 "Incoming Webhooks" → 채널(#trading-bot) 선택 → URL 복사
SLACK_WEBHOOK_URL = "https://hooks.slack.com/services/여기에_WEBHOOK_경로"

# 매일 상태 요약 알림 받을지 (매매 없는 날도 '봇 살아있음' 확인용)
SLACK_DAILY_STATUS = True

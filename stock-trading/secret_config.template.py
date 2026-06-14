# KIS 모의투자 + 슬랙 설정. secret_config.py 로 복사 후 입력. git 금지.
# python-kis는 모의투자라도 '실전 앱키'가 필수 (시세용). 주문은 모의계좌로만.

KIS_CONFIG = {
    "app_key"            : "실전_APP_KEY",
    "app_secret"         : "실전_APP_SECRET",
    "hts_id"             : "HTS_ID",
    "virtual_app_key"    : "모의_APP_KEY",
    "virtual_app_secret" : "모의_APP_SECRET",
    "account"            : "50193225-01",
    "virtual"            : True,
}

SLACK_WEBHOOK_URL = "https://hooks.slack.com/services/..."
SLACK_DAILY_STATUS = True

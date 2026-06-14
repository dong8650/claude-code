#!/usr/bin/env python3
"""
notifier.py — 슬랙 알림 모듈 (Incoming Webhook)
────────────────────────────────────────────────────────────
NEAI 봇과 동일한 방식(Incoming Webhook). 토큰 만료 없음.
secret_config.py 에 SLACK_WEBHOOK_URL 추가해서 사용.
매수=초록 / 매도=파랑 / 손절=빨강 / 익절=보라 / 에러=빨강 으로 색상 구분.
"""

import json
import urllib.request
import datetime as dt


# 액션별 색상 (슬랙 attachment color)
COLOR = {
    "BUY"        : "#2eb886",  # 초록
    "SELL"       : "#3aa3e3",  # 파랑
    "STOP_LOSS"  : "#d50200",  # 빨강
    "TAKE_PROFIT": "#9b59b6",  # 보라
    "ERROR"      : "#d50200",  # 빨강
    "INFO"       : "#cccccc",  # 회색
}

ICON = {
    "BUY": "🟢", "SELL": "🔵", "STOP_LOSS": "🔴",
    "TAKE_PROFIT": "🟣", "ERROR": "⚠️", "INFO": "ℹ️",
}


class SlackNotifier:
    def __init__(self, webhook_url: str, enabled: bool = True):
        self.url = webhook_url
        self.enabled = enabled and bool(webhook_url) and "hooks.slack.com" in (webhook_url or "")

    def _post(self, payload: dict):
        if not self.enabled:
            print(f"[알림-비활성] {payload.get('text','')}")
            return
        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                self.url, data=data,
                headers={"Content-Type": "application/json"},
            )
            urllib.request.urlopen(req, timeout=10)
        except Exception as e:
            # 알림 실패가 매매를 막으면 안 됨 — 로그만 남기고 통과
            print(f"[알림 실패] {e}")

    def trade(self, action: str, ticker: str, qty: int, price: float, reason: str = ""):
        """매매 알림 (색상 구분)"""
        ts = dt.datetime.now().strftime("%m-%d %H:%M")
        icon = ICON.get(action, "")
        title = f"{icon} {action}  {ticker}"
        fields = [
            {"title": "수량", "value": f"{qty}주", "short": True},
            {"title": "가격", "value": f"{price:,.0f}원", "short": True},
        ]
        if reason:
            fields.append({"title": "사유", "value": reason, "short": False})
        payload = {
            "attachments": [{
                "color": COLOR.get(action, "#cccccc"),
                "title": title,
                "fields": fields,
                "footer": f"모의투자 봇 · {ts}",
            }]
        }
        self._post(payload)

    def status(self, signal: int, price: float, held_qty: int, cash: float):
        """일일 상태 요약 (매매 없어도 '봇 살아있음' 확인용)"""
        sig_txt = {1: "매수신호", -1: "매도신호", 0: "관망"}.get(signal, "?")
        ts = dt.datetime.now().strftime("%m-%d %H:%M")
        payload = {
            "attachments": [{
                "color": COLOR["INFO"],
                "title": f"ℹ️ 일일 점검 — {sig_txt}",
                "fields": [
                    {"title": "현재가", "value": f"{price:,.0f}원", "short": True},
                    {"title": "보유", "value": f"{held_qty}주", "short": True},
                    {"title": "현금", "value": f"{cash:,.0f}원", "short": True},
                ],
                "footer": f"모의투자 봇 · {ts}",
            }]
        }
        self._post(payload)

    def error(self, msg: str):
        """에러 알림"""
        ts = dt.datetime.now().strftime("%m-%d %H:%M")
        payload = {
            "attachments": [{
                "color": COLOR["ERROR"],
                "title": "⚠️ 봇 에러 발생",
                "text": f"```{msg}```",
                "footer": f"모의투자 봇 · {ts}",
            }]
        }
        self._post(payload)

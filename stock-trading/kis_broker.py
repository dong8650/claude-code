#!/usr/bin/env python3
"""
kis_broker.py — 한국투자증권 모의투자 연동 (python-kis 2.x 기반)
────────────────────────────────────────────────────────────
역할: 토큰 발급 / 현재가·일봉 조회 / 시장가 매수·매도 / 잔고 조회
주의: virtual=True 인 모의계좌 전용. 실전 전환은 검증 완료 후 신중히.
"""

from pykis import PyKis, KisAuth


class KisBroker:
    def __init__(self, cfg: dict):
        """
        cfg: secret_config.py 의 KIS_CONFIG
        """
        self.virtual = cfg.get("virtual", True)
        auth = KisAuth(
            id=cfg["hts_id"],
            appkey=cfg["app_key"],
            secretkey=cfg["app_secret"],
            account=cfg["account"],
            virtual=self.virtual,
        )
        self.kis = PyKis(auth, keep_token=True)
        mode = "모의투자" if self.virtual else "⚠️실전투자⚠️"
        print(f"[KIS] 연결 완료 — {mode} | 계좌 {cfg['account']}")

    # ── 시세 조회 ───────────────────────────────
    def get_price(self, ticker: str) -> float:
        """현재가 조회"""
        stock = self.kis.stock(ticker)
        quote = stock.quote()
        return float(quote.price)

    def get_daily(self, ticker: str, days: int = 120):
        """
        일봉 조회 → pandas DataFrame (Open/High/Low/Close/Volume, Date 인덱스)
        v2.1 의 calc_indicators 가 그대로 먹도록 컬럼명 맞춤
        """
        import pandas as pd
        stock = self.kis.stock(ticker)
        # python-kis: 일봉 차트
        chart = stock.chart(period="day").df()  # 최근 데이터
        df = chart.rename(columns={
            "open": "Open", "high": "High", "low": "Low",
            "close": "Close", "volume": "Volume",
        })
        keep = ["Open", "High", "Low", "Close", "Volume"]
        df = df[[c for c in keep if c in df.columns]].copy()
        df.index = pd.to_datetime(df.index)
        return df.tail(days)

    # ── 잔고 ───────────────────────────────────
    def get_balance(self):
        """예수금(현금) + 보유종목 반환"""
        account = self.kis.account()
        bal = account.balance()
        cash = float(bal.deposit) if hasattr(bal, "deposit") else float(getattr(bal, "withdrawable", 0))
        holdings = {}
        for s in bal.stocks:
            holdings[s.symbol] = {
                "qty": int(s.qty),
                "avg_price": float(s.price) if hasattr(s, "price") else 0.0,
            }
        return cash, holdings

    def get_holding_qty(self, ticker: str) -> int:
        _, holdings = self.get_balance()
        return holdings.get(ticker, {}).get("qty", 0)

    # ── 주문 (시장가) ──────────────────────────
    def buy_market(self, ticker: str, qty: int):
        """시장가 매수"""
        if qty <= 0:
            print(f"[주문] 매수 수량 0 — 건너뜀")
            return None
        stock = self.kis.stock(ticker)
        order = stock.buy(qty=qty)  # 시장가 (지정가는 price= 지정)
        print(f"[주문] ✅ 시장가 매수 {ticker} {qty}주")
        return order

    def sell_market(self, ticker: str, qty: int):
        """시장가 매도"""
        if qty <= 0:
            print(f"[주문] 매도 수량 0 — 건너뜀")
            return None
        stock = self.kis.stock(ticker)
        order = stock.sell(qty=qty)
        print(f"[주문] ✅ 시장가 매도 {ticker} {qty}주")
        return order

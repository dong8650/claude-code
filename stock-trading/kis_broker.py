#!/usr/bin/env python3
"""
kis_broker.py — 한국투자증권 모의투자 연동 (python-kis 2.x 기반)
모의투자도 '실전 앱키'가 필수 (시세 조회용). 주문은 모의계좌로만 나감.
"""

from pykis import PyKis


class KisBroker:
    def __init__(self, cfg: dict):
        self.virtual = cfg.get("virtual", True)
        if self.virtual:
            self.kis = PyKis(
                id=cfg["hts_id"],
                account=cfg["account"],
                appkey=cfg["app_key"],
                secretkey=cfg["app_secret"],
                virtual_id=cfg["hts_id"],
                virtual_appkey=cfg["virtual_app_key"],
                virtual_secretkey=cfg["virtual_app_secret"],
                keep_token=True,
            )
            mode = "모의투자"
        else:
            self.kis = PyKis(
                id=cfg["hts_id"],
                account=cfg["account"],
                appkey=cfg["app_key"],
                secretkey=cfg["app_secret"],
                keep_token=True,
            )
            mode = "실전투자"
        print(f"[KIS] 연결 완료 — {mode} | 계좌 {cfg['account']}")

    def get_price(self, ticker: str) -> float:
        quote = self.kis.stock(ticker).quote()
        return float(quote.close)

    def get_daily(self, ticker: str, days: int = 120):
        import pandas as pd
        chart = self.kis.stock(ticker).chart(period="day")
        records = []
        for bar in chart.bars:
            records.append({
                "Date": pd.to_datetime(bar.time),
                "Open": float(bar.open), "High": float(bar.high),
                "Low": float(bar.low), "Close": float(bar.close),
                "Volume": float(bar.volume),
            })
        df = pd.DataFrame(records).set_index("Date").sort_index()
        return df.tail(days)

    def get_balance(self):
        bal = self.kis.account().balance()
        cash = 0.0
        try:
            cash = float(bal.deposit("KRW").amount)
        except Exception:
            for dep in getattr(bal, "deposits", {}).values():
                if getattr(dep, "currency", "") == "KRW":
                    cash = float(dep.amount); break
        holdings = {}
        for s in bal.stocks:
            holdings[s.symbol] = {"qty": int(s.qty),
                                  "avg_price": float(getattr(s, "price", 0))}
        return cash, holdings

    def get_holding_qty(self, ticker: str) -> int:
        _, holdings = self.get_balance()
        return holdings.get(ticker, {}).get("qty", 0)

    def buy_market(self, ticker: str, qty: int):
        if qty <= 0:
            print("[주문] 매수 수량 0 — 건너뜀"); return None
        order = self.kis.stock(ticker).buy(qty=qty)
        print(f"[주문] 시장가 매수 {ticker} {qty}주")
        return order

    def sell_market(self, ticker: str, qty: int):
        if qty <= 0:
            print("[주문] 매도 수량 0 — 건너뜀"); return None
        order = self.kis.stock(ticker).sell(qty=qty)
        print(f"[주문] 시장가 매도 {ticker} {qty}주")
        return order

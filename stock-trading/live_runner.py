#!/usr/bin/env python3
"""
live_runner.py — 모의투자 자동매매 실행기 (하루 1회) + 슬랙 알림
────────────────────────────────────────────────────────────
흐름: 일봉 조회 → 신호 계산(v2.1 재사용) → 모의주문 → 슬랙 알림 → 로그
권장: 평일 장 마감 후(16:00) systemd timer/crontab 으로 하루 1회

안전장치: virtual 강제확인 / 하루1회 가드 / max_position 상한 / 전 과정 슬랙+CSV
"""

import sys
import traceback
import datetime as dt
import pandas as pd

from trading_v2_1 import CONFIG, calc_indicators, combine_signals, kelly_from_trades
from kis_broker import KisBroker
from notifier import SlackNotifier

try:
    from secret_config import KIS_CONFIG, SLACK_WEBHOOK_URL
    try:
        from secret_config import SLACK_DAILY_STATUS
    except ImportError:
        SLACK_DAILY_STATUS = True
except ImportError:
    print("❌ secret_config.py 가 없습니다. 템플릿 복사 후 키 입력하세요.")
    sys.exit(1)

TICKER     = CONFIG["ticker"]
LOG_FILE   = "trade_log_live.csv"
GUARD_FILE = ".last_run_date"

notifier = SlackNotifier(SLACK_WEBHOOK_URL)


def already_ran_today() -> bool:
    today = dt.date.today().isoformat()
    try:
        with open(GUARD_FILE) as f:
            return f.read().strip() == today
    except FileNotFoundError:
        return False

def mark_ran_today():
    with open(GUARD_FILE, "w") as f:
        f.write(dt.date.today().isoformat())


def log_trade(action, ticker, qty, price, reason, pnl_pct=None):
    row = {
        "time": dt.datetime.now().isoformat(timespec="seconds"),
        "action": action, "ticker": ticker, "qty": qty,
        "price": price, "reason": reason, "pnl_pct": pnl_pct,
    }
    try:
        df = pd.read_csv(LOG_FILE)
        df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    except FileNotFoundError:
        df = pd.DataFrame([row])
    df.to_csv(LOG_FILE, index=False, encoding="utf-8-sig")
    print(f"[로그] {action} {ticker} {qty}주 @ {price} ({reason})")


def load_closed_pnls():
    try:
        df = pd.read_csv(LOG_FILE)
        if "pnl_pct" in df.columns:
            sells = df[df["action"].isin(["SELL","STOP_LOSS","TAKE_PROFIT"])]
            return sells["pnl_pct"].dropna().tolist()
    except FileNotFoundError:
        pass
    return []


def run():
    # 1. 모의투자 강제 확인
    if not KIS_CONFIG.get("virtual", True):
        print("🛑 virtual=False (실전). 검증 전이면 중단.")
        if input("정말 실전? (yes): ").strip().lower() != "yes":
            print("중단."); return

    # 2. 하루 1회 가드
    if already_ran_today():
        print("[가드] 오늘 이미 실행됨 — 종료")
        return

    # 3. KIS 연결
    broker = KisBroker(KIS_CONFIG)

    # 4. 일봉 + 신호
    raw = broker.get_daily(TICKER, days=120)
    if len(raw) < CONFIG["long_ma"] + 5:
        print("[중단] 데이터 부족"); return
    df = calc_indicators(raw, CONFIG)
    rows = list(df.iterrows())
    today_row, prev_row = rows[-1][1], rows[-2][1]
    signal = combine_signals(today_row, prev_row, CONFIG)

    price = broker.get_price(TICKER)
    cash, holdings = broker.get_balance()
    held_qty = holdings.get(TICKER, {}).get("qty", 0)
    entry    = holdings.get(TICKER, {}).get("avg_price", 0)

    print(f"\n[상태] 신호={signal:+d} | 현재가={price:,.0f} | 보유={held_qty}주 | 현금={cash:,.0f}")

    traded = False

    # 5. 손절/익절 우선
    if held_qty > 0 and entry > 0:
        pct = (price - entry) / entry
        if pct <= CONFIG["stop_loss_pct"]:
            broker.sell_market(TICKER, held_qty)
            log_trade("STOP_LOSS", TICKER, held_qty, price, f"{pct*100:.1f}%", pct*100)
            notifier.trade("STOP_LOSS", TICKER, held_qty, price, f"손실 {pct*100:.1f}%")
            mark_ran_today(); return
        if pct >= CONFIG["take_profit_pct"]:
            broker.sell_market(TICKER, held_qty)
            log_trade("TAKE_PROFIT", TICKER, held_qty, price, f"{pct*100:.1f}%", pct*100)
            notifier.trade("TAKE_PROFIT", TICKER, held_qty, price, f"이익 +{pct*100:.1f}%")
            mark_ran_today(); return

    # 6. 신호 매매
    if signal == 1 and held_qty == 0:
        kelly_pct = kelly_from_trades(load_closed_pnls(), CONFIG)
        qty = int((cash * kelly_pct) / price)
        if qty > 0:
            broker.buy_market(TICKER, qty)
            log_trade("BUY", TICKER, qty, price, f"kelly={kelly_pct:.3f}")
            notifier.trade("BUY", TICKER, qty, price, f"비중 {kelly_pct*100:.1f}%")
            traded = True
        else:
            print("[주문] 매수 가능 수량 0 — 자금 부족")
    elif signal == -1 and held_qty > 0:
        pct = (price - entry) / entry if entry else 0
        broker.sell_market(TICKER, held_qty)
        log_trade("SELL", TICKER, held_qty, price, "signal", pct*100)
        notifier.trade("SELL", TICKER, held_qty, price, "신호 매도")
        traded = True
    else:
        print("[대기] 조건 미충족")

    # 7. 매매 없는 날 상태 요약 (옵션)
    if not traded and SLACK_DAILY_STATUS:
        notifier.status(signal, price, held_qty, cash)

    mark_ran_today()
    print("\n✅ 오늘 실행 완료")


def main():
    try:
        run()
    except Exception as e:
        # 어떤 에러든 슬랙으로 즉시 알림 (봇이 조용히 죽는 것 방지)
        err = f"{type(e).__name__}: {e}\n{traceback.format_exc()[-500:]}"
        print("[에러]", err)
        try:
            notifier.error(err)
        except Exception:
            pass
        sys.exit(1)


if __name__ == "__main__":
    main()

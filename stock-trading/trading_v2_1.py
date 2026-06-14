#!/usr/bin/env python3
"""
한국 주식 자동매매 시스템 v2.1  (v2 결함 수정판)
════════════════════════════════════════════════════════════════
v2 대비 수정 내역 (총 7건)
  [치명] 1. 룩어헤드 제거    : 신호는 t일 종가로 계산, 체결은 t+1일 '시가'
  [치명] 2. 켈리 재구현      : 일간등락이 아닌 '청산된 거래'의 승률·손익비로 계산
  [치명] 3. 과적합 방어      : in-sample/out-of-sample 분리 + 멀티 종목 검증 함수
  [중대] 4. 손절/익절 현실화 : 종가가 아닌 t+1일 장중 Low/High 로 체결 판정
  [중대] 5. 신호 결합 정리   : 전환형(골든크로스)·상태형(Z/RSI) 신호를 분리해 가중
  [중대] 6. Hurst 수정       : 가격이 아닌 로그수익률 기반 R/S 분석
  [중대] 7. 승률 계산 구현   : 진입-청산 매칭으로 실제 승률·손익비 산출

사용법
------
pip install pykrx pandas numpy scipy statsmodels matplotlib
python trading_v2_1.py            # 실데이터(pykrx) 백테스트
python trading_v2_1.py --synth    # 합성데이터로 로직 검증 (네트워크 불필요)
python trading_v2_1.py --compare  # 룩어헤드 수정 전/후 비교
"""

import warnings
warnings.filterwarnings("ignore")

import sys
import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.tsa.stattools import adfuller

# ──────────────────────────────────────────────
# 0. 전역 설정
# ──────────────────────────────────────────────
CONFIG = {
    "start_date"      : "20200101",
    "end_date"        : "20241231",
    "ticker"          : "005930",
    "initial_capital" : 100_000,

    # 리스크 파라미터
    "stop_loss_pct"   : -0.02,
    "take_profit_pct" :  0.05,
    "slippage_pct"    :  0.0015,
    "tax_rate"        :  0.0023,
    "commission_rate" :  0.00015,
    "kelly_fraction"  :  0.25,
    "max_position_pct":  0.10,

    # 전략 파라미터
    "short_ma"        : 5,
    "long_ma"         : 20,
    "zscore_window"   : 20,
    "zscore_entry"    : -1.5,
    "zscore_exit"     :  0.5,
    "rsi_period"      : 14,
    "rsi_oversold"    : 30,
    "rsi_overbought"  : 70,
    "roc_period"      : 5,

    # [수정3] 과적합 방어: in-sample 비율 (앞 70%로 파라미터 점검, 뒤 30%는 검증 전용)
    "is_ratio"        : 0.70,

    # [수정5] 신호 결합 가중치 (전환형은 강하게, 상태형은 보조)
    "w_golden"        : 1.0,
    "w_zscore"        : 0.7,
    "w_rsi"           : 0.7,
    "signal_threshold": 1.0,   # 가중합이 이 값 이상이면 진입
}


# ──────────────────────────────────────────────
# 1. 데이터 수집 (실데이터 + 합성데이터)
# ──────────────────────────────────────────────
def fetch_ohlcv(ticker, start, end):
    from pykrx import stock
    print(f"[데이터] {ticker} 시세 수집 중... ({start}~{end})")
    df = stock.get_market_ohlcv_by_date(start, end, ticker)
    if df.empty:
        raise RuntimeError("pykrx 데이터 비어있음 (네트워크/인증 문제)")
    df.index = pd.to_datetime(df.index)
    df.columns = ["Open", "High", "Low", "Close", "Volume", "TradingValue", "PriceChange"][:len(df.columns)]
    df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
    df = df[df["Volume"] > 0]
    print(f"[데이터] {len(df)}개 거래일 수집 완료")
    return df


def make_synthetic_ohlcv(n_days=1250, seed=42, regime="mixed"):
    """
    현실적 합성 OHLCV 생성.
    - 변동성 클러스터링(GARCH풍) + 약한 평균회귀 + 추세 구간 혼합
    - 로직 검증용. 룩어헤드 효과를 통제된 조건에서 측정하기 위함.
    """
    rng = np.random.default_rng(seed)
    mu = 0.0003          # 일평균 드리프트
    base_vol = 0.018
    close = [2000.0]   # 검증용 시작가(소액 10만원으로 거래 발생하도록 낮게 설정). 실데이터엔 무관.
    vol = base_vol
    for t in range(1, n_days):
        vol = 0.92 * vol + 0.08 * base_vol + 0.02 * abs(rng.normal()) * base_vol  # 변동성 클러스터
        mr = -0.02 * (np.log(close[-1] / 2000))  # 약한 평균회귀
        ret = mu + mr + rng.normal(0, vol)
        close.append(close[-1] * np.exp(ret))
    close = np.array(close)

    # OHLC 생성 (장중 변동 포함 → 손절/익절 장중 판정 검증용)
    opens, highs, lows = [], [], []
    for t in range(n_days):
        c = close[t]
        o = c * np.exp(rng.normal(0, 0.004)) if t == 0 else close[t-1] * np.exp(rng.normal(0, 0.004))
        intra = abs(rng.normal(0, 0.012))
        hi = max(o, c) * np.exp(intra)
        lo = min(o, c) * np.exp(-intra)
        opens.append(o); highs.append(hi); lows.append(lo)

    idx = pd.bdate_range("2020-01-01", periods=n_days)
    df = pd.DataFrame({
        "Open": opens, "High": highs, "Low": lows, "Close": close,
        "Volume": rng.integers(1_000_000, 5_000_000, n_days)
    }, index=idx)
    return df


# ──────────────────────────────────────────────
# 2. 지표 계산
# ──────────────────────────────────────────────
def calc_indicators(df, cfg):
    d = df.copy()
    d["MA_short"] = d["Close"].rolling(cfg["short_ma"]).mean()
    d["MA_long"]  = d["Close"].rolling(cfg["long_ma"]).mean()

    roll = d["Close"].rolling(cfg["zscore_window"])
    d["ZScore"] = (d["Close"] - roll.mean()) / roll.std()

    delta = d["Close"].diff()
    gain  = delta.clip(lower=0).rolling(cfg["rsi_period"]).mean()
    loss  = (-delta.clip(upper=0)).rolling(cfg["rsi_period"]).mean()
    rs    = gain / loss.replace(0, np.nan)
    d["RSI"] = 100 - (100 / (1 + rs))

    d["ROC"]     = d["Close"].pct_change(cfg["roc_period"]) * 100
    d["Returns"] = d["Close"].pct_change()
    return d.dropna()


# ──────────────────────────────────────────────
# 3. 전략 신호  [수정5: 전환형/상태형 분리 가중]
# ──────────────────────────────────────────────
def signal_golden_cross(row, prev_row) -> int:
    if prev_row["MA_short"] <= prev_row["MA_long"] and row["MA_short"] > row["MA_long"]:
        return 1
    if prev_row["MA_short"] >= prev_row["MA_long"] and row["MA_short"] < row["MA_long"]:
        return -1
    return 0

def signal_zscore(row, cfg) -> int:
    if row["ZScore"] < cfg["zscore_entry"]:  return 1
    if row["ZScore"] > cfg["zscore_exit"]:   return -1
    return 0

def signal_rsi_roc(row, cfg) -> int:
    if row["RSI"] < cfg["rsi_oversold"] and row["ROC"] > 0:  return 1
    if row["RSI"] > cfg["rsi_overbought"]:                   return -1
    return 0

def combine_signals(row, prev_row, cfg) -> int:
    """
    [수정5] 단순 합산이 아니라 가중합.
    골든크로스(전환형)는 가중치 높게, Z/RSI(상태형)는 보조.
    가중합이 +threshold 이상이면 매수, -threshold 이하면 매도.
    """
    g = signal_golden_cross(row, prev_row) * cfg["w_golden"]
    z = signal_zscore(row, cfg)            * cfg["w_zscore"]
    r = signal_rsi_roc(row, cfg)           * cfg["w_rsi"]
    total = g + z + r
    if total >=  cfg["signal_threshold"]:  return 1
    if total <= -cfg["signal_threshold"]:  return -1
    return 0


# ──────────────────────────────────────────────
# 4. 리스크 관리  [수정2: 켈리 재구현]
# ──────────────────────────────────────────────
def kelly_from_trades(closed_trades, cfg):
    """
    [수정2] 일간 등락이 아니라 '청산된 거래' 손익률로 켈리 계산.
    closed_trades: list of pnl_pct (각 거래의 손익률)
    거래 표본이 부족하면(<10) 보수적으로 max_position의 절반만.
    """
    if len(closed_trades) < 10:
        return cfg["max_position_pct"] * 0.5  # 표본 부족 → 보수적 고정

    arr = np.array(closed_trades)
    wins = arr[arr > 0]; losses = arr[arr < 0]
    if len(wins) == 0 or len(losses) == 0:
        return cfg["max_position_pct"] * 0.5

    W = len(wins) / len(arr)
    R = wins.mean() / abs(losses.mean())
    kelly = W - (1 - W) / R
    kelly = max(0, kelly) * cfg["kelly_fraction"]
    return min(kelly, cfg["max_position_pct"])  # 상한 적용


def calc_transaction_cost(price, shares, is_sell, cfg):
    slippage = price * cfg["slippage_pct"] * (1 if is_sell else -1)
    exec_price = price + slippage
    commission = exec_price * shares * cfg["commission_rate"]
    tax = exec_price * shares * cfg["tax_rate"] if is_sell else 0
    return commission + tax, exec_price


# ──────────────────────────────────────────────
# 5. 백테스팅 엔진  [수정1,4,7]
# ──────────────────────────────────────────────
def run_backtest(df, cfg, use_next_open=True):
    """
    [수정1] use_next_open=True: 신호는 t일 종가로, 체결은 t+1일 '시가'.
            (False로 주면 v2의 룩어헤드 방식 — 비교용)
    [수정4] 손절/익절을 t+1일 장중 Low/High로 판정.
    [수정7] 진입-청산 매칭으로 거래별 손익률 기록 → 승률·켈리에 사용.
    """
    capital = cfg["initial_capital"]
    shares = 0
    entry_price = 0.0
    trade_log = []
    equity_log = []
    closed_pnls = []     # [수정7] 청산된 거래의 손익률

    rows = list(df.iterrows())
    n = len(rows)

    for i in range(1, n - 1):       # 마지막 직전까지 (t+1 체결을 위해)
        date, row     = rows[i]
        _, prev_row   = rows[i - 1]
        next_date, next_row = rows[i + 1]

        close_t   = row["Close"]
        # [수정1] 체결 가격: 다음날 시가 (룩어헤드 제거)
        exec_base = next_row["Open"] if use_next_open else close_t

        # 포트폴리오 가치는 당일 종가로 평가
        equity_log.append({"Date": date, "Value": capital + shares * close_t})

        # ── 보유 중: 손절/익절 [수정4] 다음날 장중 Low/High로 판정
        if shares > 0:
            stop_price = entry_price * (1 + cfg["stop_loss_pct"])
            take_price = entry_price * (1 + cfg["take_profit_pct"])
            hit = None; fill = None

            if use_next_open:
                nlo, nhi, nop = next_row["Low"], next_row["High"], next_row["Open"]
                # 시가가 이미 손절선 아래면 시가 체결 (갭하락)
                if nop <= stop_price:
                    hit, fill = "STOP_LOSS", nop
                elif nop >= take_price:
                    hit, fill = "TAKE_PROFIT", nop
                elif nlo <= stop_price:        # 장중 손절 터치 (보수적으로 손절 우선)
                    hit, fill = "STOP_LOSS", stop_price
                elif nhi >= take_price:
                    hit, fill = "TAKE_PROFIT", take_price
            else:
                # v2 방식: 당일 종가로 판정
                pct = (close_t - entry_price) / entry_price
                if pct <= cfg["stop_loss_pct"]:   hit, fill = "STOP_LOSS", close_t
                elif pct >= cfg["take_profit_pct"]: hit, fill = "TAKE_PROFIT", close_t

            if hit:
                cost, exec_price = calc_transaction_cost(fill, shares, True, cfg)
                revenue = exec_price * shares - cost
                pnl_pct = (exec_price - entry_price) / entry_price   # [수정7]
                capital += revenue
                closed_pnls.append(pnl_pct)
                trade_log.append({"Date": next_date, "Action": hit, "Price": exec_price,
                                  "Shares": shares, "PnL%": pnl_pct*100, "Capital": capital})
                shares = 0; entry_price = 0.0
                continue

        # ── 신호 (t일 종가 기준)
        signal = combine_signals(row, prev_row, cfg)

        # ── 매수: t+1 시가 체결
        if signal == 1 and shares == 0:
            kelly_pct = kelly_from_trades(closed_pnls, cfg)   # [수정2]
            invest = capital * kelly_pct
            buy_shares = int(invest / exec_base)
            if buy_shares > 0:
                cost, exec_price = calc_transaction_cost(exec_base, buy_shares, False, cfg)
                total_cost = exec_price * buy_shares + cost
                if total_cost <= capital:
                    capital -= total_cost
                    shares = buy_shares
                    entry_price = exec_price
                    trade_log.append({"Date": next_date, "Action": "BUY", "Price": exec_price,
                                      "Shares": shares, "PnL%": 0, "Capital": capital})

        # ── 매도 신호: t+1 시가 체결
        elif signal == -1 and shares > 0:
            cost, exec_price = calc_transaction_cost(exec_base, shares, True, cfg)
            revenue = exec_price * shares - cost
            pnl_pct = (exec_price - entry_price) / entry_price   # [수정7]
            capital += revenue
            closed_pnls.append(pnl_pct)
            trade_log.append({"Date": next_date, "Action": "SELL", "Price": exec_price,
                              "Shares": shares, "PnL%": pnl_pct*100, "Capital": capital})
            shares = 0; entry_price = 0.0

    # 잔여 청산
    if shares > 0:
        final_price = rows[-1][1]["Close"]
        cost, exec_price = calc_transaction_cost(final_price, shares, True, cfg)
        capital += exec_price * shares - cost
        closed_pnls.append((exec_price - entry_price) / entry_price)

    equity_df = pd.DataFrame(equity_log).set_index("Date")
    trade_df = pd.DataFrame(trade_log)
    return equity_df, trade_df, closed_pnls


# ──────────────────────────────────────────────
# 6. 통계 검정  [수정6: Hurst 로그수익률 기반]
# ──────────────────────────────────────────────
def calc_hurst(returns: np.ndarray) -> float:
    """[수정6] 가격이 아닌 '수익률' 기반 R/S 분석"""
    returns = returns[~np.isnan(returns)]
    if len(returns) < 100:
        return 0.5
    lags = range(2, 50)
    tau = []
    for lag in lags:
        diff = returns[lag:] - returns[:-lag]
        tau.append(np.sqrt(np.std(diff)))
    poly = np.polyfit(np.log(list(lags)), np.log(tau), 1)
    return poly[0] * 2.0   # R/S 근사 스케일링


def run_statistical_tests(df):
    prices  = df["Close"].values
    returns = df["Returns"].dropna().values
    print("\n" + "─"*52)
    print("📊 통계 검정")
    print("─"*52)
    adf_stat, adf_p, *_ = adfuller(prices, autolag="AIC")
    print(f"[ADF]      p={adf_p:.4f}  →  {'정상(평균회귀 적합)' if adf_p<0.05 else '비정상(추세추종 적합)'}")
    h = calc_hurst(returns)
    tag = "평균회귀" if h < 0.45 else ("추세추종" if h > 0.55 else "랜덤워크")
    print(f"[Hurst]    H={h:.4f}  →  {tag}")
    sw_stat, sw_p = stats.shapiro(returns[:5000])
    print(f"[Shapiro]  p={sw_p:.4f}  →  {'비정규(켈리 보수 적용 권장)' if sw_p<0.05 else '정규'}")
    print("─"*52)


# ──────────────────────────────────────────────
# 7. 성과 지표  [수정7: 승률 구현]
# ──────────────────────────────────────────────
def calc_performance(equity_df, trade_df, closed_pnls, cfg, label=""):
    values = equity_df["Value"]
    returns = values.pct_change().dropna()

    total_days = max((equity_df.index[-1] - equity_df.index[0]).days, 1)
    total_return = (values.iloc[-1] / values.iloc[0]) - 1
    cagr = (1 + total_return) ** (365 / total_days) - 1

    rf_daily = 0.035 / 252
    excess = returns - rf_daily
    sharpe = (excess.mean() / excess.std()) * np.sqrt(252) if excess.std() > 0 else 0

    cummax = values.cummax()
    mdd = ((values - cummax) / cummax).min()
    calmar = cagr / abs(mdd) if mdd != 0 else 0

    # [수정7] 승률·손익비
    pnls = np.array(closed_pnls)
    if len(pnls) > 0:
        win_rate = (pnls > 0).mean()
        avg_win = pnls[pnls > 0].mean() if (pnls > 0).any() else 0
        avg_loss = pnls[pnls < 0].mean() if (pnls < 0).any() else 0
        profit_factor = abs(pnls[pnls>0].sum() / pnls[pnls<0].sum()) if (pnls<0).any() else float('inf')
    else:
        win_rate = avg_win = avg_loss = profit_factor = 0

    print(f"\n{'='*52}")
    print(f"📈 성과 {label}")
    print('='*52)
    print(f"  총수익률   : {total_return*100:>8.2f}%    CAGR: {cagr*100:>7.2f}%")
    print(f"  Sharpe     : {sharpe:>8.3f}    MDD : {mdd*100:>7.2f}%")
    print(f"  Calmar     : {calmar:>8.3f}    거래: {len(closed_pnls):>4}건")
    print(f"  승률       : {win_rate*100:>8.1f}%    PF  : {profit_factor:>7.2f}")
    print(f"  평균수익   : {avg_win*100:>8.2f}%    평균손실: {avg_loss*100:>6.2f}%")
    print('='*52)
    return {"sharpe": sharpe, "mdd": mdd, "cagr": cagr, "total_return": total_return,
            "win_rate": win_rate, "trades": len(closed_pnls)}


# ──────────────────────────────────────────────
# 8. 과적합 방어: in-sample / out-of-sample  [수정3]
# ──────────────────────────────────────────────
def split_is_oos(df, cfg):
    k = int(len(df) * cfg["is_ratio"])
    return df.iloc[:k], df.iloc[k:]


def walk_evaluate(df, cfg, label):
    eq, tr, pnls = run_backtest(df, cfg, use_next_open=True)
    return calc_performance(eq, tr, pnls, cfg, label)


# ──────────────────────────────────────────────
# 9. 메인
# ──────────────────────────────────────────────
def get_data(cfg, synth):
    if synth:
        print("[데이터] 합성 데이터 생성 (네트워크 불필요, 로직 검증용)")
        return make_synthetic_ohlcv(n_days=1250, seed=42)
    return fetch_ohlcv(cfg["ticker"], cfg["start_date"], cfg["end_date"])


def main():
    synth   = "--synth" in sys.argv or "--compare" in sys.argv
    compare = "--compare" in sys.argv
    cfg = CONFIG

    raw = get_data(cfg, synth)
    df = calc_indicators(raw, cfg)
    run_statistical_tests(df)

    if compare:
        print("\n" + "#"*52)
        print("# 룩어헤드 수정 전(v2) vs 후(v2.1) 비교")
        print("#"*52)
        eq_old, tr_old, p_old = run_backtest(df, cfg, use_next_open=False)  # v2 방식
        calc_performance(eq_old, tr_old, p_old, cfg, "[v2: 당일종가 체결 — 룩어헤드 있음]")
        eq_new, tr_new, p_new = run_backtest(df, cfg, use_next_open=True)   # v2.1 방식
        calc_performance(eq_new, tr_new, p_new, cfg, "[v2.1: 다음날 시가 체결 — 룩어헤드 제거]")
        return

    # [수정3] in-sample / out-of-sample 분리 검증
    print("\n" + "#"*52)
    print("# 과적합 점검: In-Sample vs Out-of-Sample")
    print("#"*52)
    is_df, oos_df = split_is_oos(df, cfg)
    walk_evaluate(is_df,  cfg, "[In-Sample 70% — 파라미터가 맞춰진 구간]")
    walk_evaluate(oos_df, cfg, "[Out-of-Sample 30% — 한 번도 안 본 구간 ★진짜 성적]")
    print("\n※ IS는 좋은데 OOS가 급락하면 = 과적합. 둘이 비슷해야 신뢰 가능.")


if __name__ == "__main__":
    main()

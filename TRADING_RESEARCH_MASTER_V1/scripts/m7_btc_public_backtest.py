#!/usr/bin/env python3
"""
M7 BTC public strategy reproduction (research only).

ADOPTED=NO LIVE_ORDER_ENABLED=NO PRODUCTION_CHANGE_ALLOWED=NO

Faithful-enough engine of Freqtrade-style:
- signal on closed bar t
- enter at open of t+1
- max 1 open position
- ROI / stoploss checked on subsequent bars' high/low
- exit signal -> fill at next bar open
- same-bar ROI+SL conflict: CONSERVATIVE = stoploss first (flagged)

Fee assumption: 0.0005 each side (round-trip 0.10% comparison ASSUMPTION).
"""
from __future__ import annotations

import gzip
import hashlib
import json
from dataclasses import dataclass, asdict
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def resolve_csv(stem: str) -> Path:
    raw = ROOT / f"data/btc/{stem}.csv"
    gz = ROOT / f"data/btc/{stem}.csv.gz"
    if raw.exists():
        return raw
    if gz.exists():
        return gz
    raise FileNotFoundError(stem)


DATA_1M = resolve_csv("BTCUSDT_1m_binance_vision_public")
DATA_5M = resolve_csv("BTCUSDT_5m_binance_vision_public")
OUT_LEDGER = ROOT / "ledgers"
OUT_REPORT = ROOT / "reports"
OUT_LOG = ROOT / "logs"
FEE_SIDE = 0.0005  # ASSUMPTION


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def load_ohlcv(path: Path) -> pd.DataFrame:
    if str(path).endswith(".gz"):
        with gzip.open(path, "rt") as f:
            df = pd.read_csv(f)
    else:
        df = pd.read_csv(path)
    df["open_time"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)
    for c in ("open", "high", "low", "close", "volume"):
        df[c] = df[c].astype(float)
    return df.sort_values("open_time").reset_index(drop=True)


def bollinger(series: pd.Series, window: int, stds: float = 2.0):
    mid = series.rolling(window).mean()
    sd = series.rolling(window).std(ddof=0)  # qtpylib uses population-ish; note in SPEC
    lower = mid - stds * sd
    upper = mid + stds * sd
    return mid, lower, upper


def ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()


def sma(series: pd.Series, window: int) -> pd.Series:
    return series.rolling(window).mean()


def rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    up = delta.clip(lower=0)
    down = -delta.clip(upper=0)
    ma_up = up.ewm(alpha=1 / period, adjust=False).mean()
    ma_down = down.ewm(alpha=1 / period, adjust=False).mean()
    rs = ma_up / ma_down.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def adx(high, low, close, period=14):
    plus_dm = high.diff()
    minus_dm = -low.diff()
    plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0.0)
    minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0.0)
    tr = pd.concat(
        [
            (high - low),
            (high - close.shift()).abs(),
            (low - close.shift()).abs(),
        ],
        axis=1,
    ).max(axis=1)
    atr = tr.ewm(alpha=1 / period, adjust=False).mean()
    plus_di = 100 * (plus_dm.ewm(alpha=1 / period, adjust=False).mean() / atr)
    minus_di = 100 * (minus_dm.ewm(alpha=1 / period, adjust=False).mean() / atr)
    dx = (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan) * 100
    return dx.ewm(alpha=1 / period, adjust=False).mean()


def stochf(high, low, close, k_period=5, d_period=3):
    lowest = low.rolling(k_period).min()
    highest = high.rolling(k_period).max()
    k = 100 * (close - lowest) / (highest - lowest).replace(0, np.nan)
    d = k.rolling(d_period).mean()
    return k, d


def mfi(high, low, close, volume, period=14):
    tp = (high + low + close) / 3.0
    rmf = tp * volume
    delta = tp.diff()
    pos = rmf.where(delta > 0, 0.0)
    neg = rmf.where(delta < 0, 0.0)
    pos_sum = pos.rolling(period).sum()
    neg_sum = neg.rolling(period).sum()
    mr = pos_sum / neg_sum.replace(0, np.nan)
    return 100 - (100 / (1 + mr))


def cci(high, low, close, period=20):
    tp = (high + low + close) / 3.0
    sma_tp = tp.rolling(period).mean()
    mad = tp.rolling(period).apply(lambda x: np.mean(np.abs(x - x.mean())), raw=True)
    return (tp - sma_tp) / (0.015 * mad.replace(0, np.nan))


def crossed_above(a: pd.Series, b) -> pd.Series:
    if isinstance(b, (int, float)):
        b = pd.Series(b, index=a.index)
    return (a > b) & (a.shift(1) <= b.shift(1))


@dataclass
class Trade:
    strategy: str
    entry_time: str
    exit_time: str
    entry_price: float
    exit_price: float
    reason: str
    hold_bars: int
    ret_gross: float
    ret_net: float
    same_bar_conflict: bool


def simulate(
    name: str,
    df: pd.DataFrame,
    enter: pd.Series,
    exit_sig: pd.Series,
    roi: float,
    stoploss: float,
) -> list[Trade]:
    """
    enter/exit_sig aligned to df index; True on signal bar (closed).
    Entry fill = next bar open. Exit signal fill = next bar open.
    """
    o = df["open"].to_numpy()
    h = df["high"].to_numpy()
    l = df["low"].to_numpy()
    t = df["open_time"].astype(str).to_numpy()
    ent = enter.fillna(False).to_numpy(dtype=bool)
    exs = exit_sig.fillna(False).to_numpy(dtype=bool)
    n = len(df)
    trades: list[Trade] = []
    i = 0
    while i < n - 1:
        if not ent[i]:
            i += 1
            continue
        entry_i = i + 1
        if entry_i >= n:
            break
        entry_px = float(o[entry_i])
        entry_t = t[entry_i]
        conflict = False
        exit_i = None
        exit_px = None
        reason = None
        j = entry_i
        while j < n:
            # ROI / SL on bar j (including entry bar)
            stop_px = entry_px * (1.0 + stoploss)
            roi_px = entry_px * (1.0 + roi)
            hit_sl = l[j] <= stop_px
            hit_roi = h[j] >= roi_px
            if hit_sl and hit_roi:
                conflict = True
                exit_i = j
                exit_px = stop_px  # conservative
                reason = "stoploss_samebar_conflict"
                break
            if hit_sl:
                # gap through stop: exit at open if open already below stop
                exit_i = j
                exit_px = min(float(o[j]), stop_px) if float(o[j]) < stop_px else stop_px
                reason = "stoploss"
                break
            if hit_roi:
                exit_i = j
                exit_px = max(float(o[j]), roi_px) if float(o[j]) > roi_px else roi_px
                reason = "roi"
                break
            # exit signal on closed bar j -> fill next open
            if exs[j] and j + 1 < n:
                exit_i = j + 1
                exit_px = float(o[j + 1])
                reason = "exit_signal"
                break
            j += 1
        if exit_i is None:
            # force flat at last close for research completeness
            exit_i = n - 1
            exit_px = float(df["close"].iloc[-1])
            reason = "end_of_data"
        ret_g = (exit_px / entry_px) - 1.0
        ret_n = (exit_px * (1 - FEE_SIDE)) / (entry_px * (1 + FEE_SIDE)) - 1.0
        trades.append(
            Trade(
                strategy=name,
                entry_time=str(entry_t),
                exit_time=str(t[exit_i]),
                entry_price=entry_px,
                exit_price=float(exit_px),
                reason=reason,
                hold_bars=int(exit_i - entry_i),
                ret_gross=float(ret_g),
                ret_net=float(ret_n),
                same_bar_conflict=conflict,
            )
        )
        i = exit_i + 1  # no overlapping; next search after exit
    return trades


def prep_binhv45(df: pd.DataFrame) -> tuple[pd.Series, pd.Series, float, float]:
    mid, lower, upper = bollinger(df["close"], 40, 2)
    bbdelta = (mid - lower).abs()
    closedelta = (df["close"] - df["close"].shift()).abs()
    tail = (df["close"] - df["low"]).abs()
    # buy_params from source
    buy_bbdelta, buy_closedelta, buy_tail = 7, 17, 25
    enter = (
        lower.shift().gt(0)
        & bbdelta.gt(df["close"] * buy_bbdelta / 1000)
        & closedelta.gt(df["close"] * buy_closedelta / 1000)
        & tail.lt(bbdelta * buy_tail / 1000)
        & df["close"].lt(lower.shift())
        & df["close"].le(df["close"].shift())
    )
    exit_sig = pd.Series(False, index=df.index)
    return enter, exit_sig, 0.0125, -0.05


def prep_cluc(df5: pd.DataFrame) -> tuple[pd.Series, pd.Series, float, float]:
    tp = (df5["high"] + df5["low"] + df5["close"]) / 3.0
    mid, lower, upper = bollinger(tp, 20, 2)
    ema100 = ema(df5["close"], 50)  # source: named ema100, period 50
    vol_ma = df5["volume"].rolling(30).mean().shift(1)
    enter = (
        (df5["close"] < ema100)
        & (df5["close"] < 0.985 * lower)
        & (df5["volume"] < (vol_ma * 20))
    )
    exit_sig = df5["close"] > mid
    return enter, exit_sig, 0.01, -0.05


def prep_scalp(df: pd.DataFrame) -> tuple[pd.Series, pd.Series, float, float]:
    ema_high = ema(df["high"], 5)
    ema_low = ema(df["low"], 5)
    fastk, fastd = stochf(df["high"], df["low"], df["close"], 5, 3)
    adx_v = adx(df["high"], df["low"], df["close"], 14)
    enter = (
        (df["open"] < ema_low)
        & (adx_v > 30)
        & (fastk < 30)
        & (fastd < 30)
        & crossed_above(fastk, fastd)
    )
    exit_sig = (df["open"] >= ema_high) | crossed_above(fastk, 70) | crossed_above(fastd, 70)
    return enter, exit_sig, 0.01, -0.04


def prep_reinforced(df: pd.DataFrame) -> tuple[pd.Series, pd.Series, float, float]:
    # resample 5m SMA50 onto 1m (no time-interpolate into future: ffill only after 5m close)
    df5 = (
        df.set_index("open_time")
        .resample("5min", label="left", closed="left")
        .agg({"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"})
        .dropna()
    )
    df5["sma50"] = sma(df5["close"], 50)
    # merge as-of: 5m bar available only after it completes -> shift 1 then ffill
    sma_avail = df5["sma50"].shift(1)
    sma_1m = sma_avail.reindex(df.set_index("open_time").index, method="ffill").to_numpy()
    ema_high = ema(df["high"], 5)
    ema_low = ema(df["low"], 5)
    fastk, fastd = stochf(df["high"], df["low"], df["close"], 5, 3)
    adx_v = adx(df["high"], df["low"], df["close"], 14)
    mfi_v = mfi(df["high"], df["low"], df["close"], df["volume"], 14)
    cci_v = cci(df["high"], df["low"], df["close"], 20)
    # defaults from IntParameter/BooleanParameter in source
    enter = (
        (mfi_v < 22)
        & (fastd < 30)
        & (adx_v > 32)
        & crossed_above(fastk, fastd)
        & (sma_1m < df["close"].to_numpy())
        & (df["volume"] > 0)
    )
    exit_sig = (
        (df["open"] > ema_high)
        & (cci_v > 183)
        & (fastd > 79)
        & (fastk > 70)
        & (df["volume"] > 0)
    )
    return enter, exit_sig, 0.02, -0.10


def summarize(trades: list[Trade]) -> dict:
    if not trades:
        return {
            "n": 0,
            "mean_net": None,
            "median_net": None,
            "winrate": None,
            "sum_net": None,
            "max_dd_equity": None,
            "mean_hold_bars": None,
            "reasons": {},
            "same_bar_conflicts": 0,
        }
    rets = np.array([t.ret_net for t in trades], dtype=float)
    equity = np.cumprod(1 + rets)
    peak = np.maximum.accumulate(equity)
    dd = (equity / peak) - 1.0
    reasons: dict[str, int] = {}
    for t in trades:
        reasons[t.reason] = reasons.get(t.reason, 0) + 1
    return {
        "n": len(trades),
        "mean_net": float(rets.mean()),
        "median_net": float(np.median(rets)),
        "winrate": float((rets > 0).mean()),
        "sum_net_compound_minus1": float(equity[-1] - 1),
        "max_dd_equity": float(dd.min()),
        "mean_hold_bars": float(np.mean([t.hold_bars for t in trades])),
        "worst_trade": float(rets.min()),
        "best_trade": float(rets.max()),
        "reasons": reasons,
        "same_bar_conflicts": int(sum(1 for t in trades if t.same_bar_conflict)),
        "fee_side_assumption": FEE_SIDE,
    }


def main():
    OUT_LEDGER.mkdir(parents=True, exist_ok=True)
    OUT_REPORT.mkdir(parents=True, exist_ok=True)
    OUT_LOG.mkdir(parents=True, exist_ok=True)

    df1 = load_ohlcv(DATA_1M)
    df5 = load_ohlcv(DATA_5M)

    configs = [
        ("BinHV45", df1, prep_binhv45, "1m"),
        ("ClucMay72018", df5, prep_cluc, "5m"),
        ("Scalp", df1, prep_scalp, "1m"),
        ("ReinforcedSmoothScalp", df1, prep_reinforced, "1m"),
    ]

    all_summary = {
        "flags": {
            "ADOPTED": "NO",
            "LIVE_ORDER_ENABLED": "NO",
            "PRODUCTION_CHANGE_ALLOWED": "NO",
        },
        "data": {
            "1m": str(DATA_1M),
            "5m": str(DATA_5M),
            "sha256_1m": sha256_file(DATA_1M),
            "sha256_5m": sha256_file(DATA_5M),
            "start_1m": str(df1["open_time"].iloc[0]),
            "end_1m": str(df1["open_time"].iloc[-1]),
            "bars_1m": int(len(df1)),
            "bars_5m": int(len(df5)),
        },
        "engine_notes": [
            "Entry at next bar open after signal close.",
            "ROI/SL on bar high/low; same-bar conflict -> stoploss first (flagged).",
            "Exit signal fills next open.",
            "max_open_trades=1; no leverage; spot long only.",
            "Indicator libs: pandas ewm/rolling approximations of TA-Lib; not bit-identical to Freqtrade/TA-Lib.",
            "Fee 0.0005/side is ASSUMPTION for comparison, not account fee.",
            "NOT an adoption recommendation.",
        ],
        "strategies": {},
    }

    for name, df, prep, tf in configs:
        enter, exit_sig, roi, sl = prep(df)
        trades = simulate(name, df, enter, exit_sig, roi, sl)
        ledger_path = OUT_LEDGER / f"M7_{name}_trades.csv"
        pd.DataFrame([asdict(t) for t in trades]).to_csv(ledger_path, index=False)
        summary = summarize(trades)
        summary.update(
            {
                "timeframe": tf,
                "minimal_roi": roi,
                "stoploss": sl,
                "entry_signals": int(enter.fillna(False).sum()),
                "exit_signals": int(exit_sig.fillna(False).sum()),
                "ledger": str(ledger_path),
                "ledger_sha256": sha256_file(ledger_path) if ledger_path.exists() else None,
            }
        )
        all_summary["strategies"][name] = summary
        print(name, json.dumps({k: summary[k] for k in ("n", "mean_net", "winrate", "max_dd_equity", "reasons")}, default=str))

    out_json = OUT_REPORT / "M7_BTC_PUBLIC_SUMMARY.json"
    out_json.write_text(json.dumps(all_summary, indent=2))
    print("Wrote", out_json)


if __name__ == "__main__":
    main()

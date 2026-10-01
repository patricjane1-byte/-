#!/usr/bin/env python3
"""
KR FLOW TO INTRADAY HIGH — runnable analysis (research only).

ADOPTED=NO LIVE_ORDER_ENABLED=NO PRODUCTION_CHANGE_ALLOWED=NO

If point-in-time investor flow (C) is missing → BLOCKED_MISSING_POINT_IN_TIME_FLOW.
Does not modify MAIN-H1 / collectors / RAW.
Does not treat daily settled flow as intraday.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SPEC_PATH = ROOT / "SPEC_BEFORE_RUN.json"


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def load_spec() -> dict:
    return json.loads(SPEC_PATH.read_text(encoding="utf-8"))


@dataclass
class Paths:
    watchlist: Path | None = None
    bars_1m: Path | None = None
    flow_investor: Path | None = None
    flow_program: Path | None = None
    flow_window: Path | None = None


def resolve_paths(data_dir: Path) -> Paths:
    """Expected filenames when PC/server data is mounted read-only."""
    candidates = {
        "watchlist": ["watchlist.csv", "hiki_watchlist.csv", "사전감시명단.csv"],
        "bars_1m": ["HI_KI_1MIN_60D_ALL.csv", "bars_1m.csv", "krx_1m.csv"],
        "flow_investor": [
            "investor_trend_estimate_pit.csv",
            "flow_investor_intraday.csv",
            "기관외국인_가집계.csv",
        ],
        "flow_program": ["program_trading_pit.csv", "flow_program.csv"],
        "flow_window": ["broker_window_pit.csv", "flow_broker_window.csv"],
    }
    out = Paths()
    for attr, names in candidates.items():
        hit = None
        for n in names:
            p = data_dir / n
            if p.exists():
                hit = p
                break
        setattr(out, attr, hit)
    return out


def build_5m(df1: pd.DataFrame) -> pd.DataFrame:
    """Aggregate exact 5 completed positive-volume 1m bars; no interpolation."""
    need = {"date", "time", "code", "open", "high", "low", "close", "volume"}
    missing = need - set(df1.columns)
    if missing:
        raise ValueError(f"bars_1m missing columns: {missing}")
    d = df1.copy()
    d["ts"] = pd.to_datetime(d["date"].astype(str) + " " + d["time"].astype(str))
    d = d.sort_values(["code", "ts"])
    d["volume"] = d["volume"].astype(float)
    rows = []
    for code, g in d.groupby("code", sort=False):
        g = g.reset_index(drop=True)
        # group into consecutive 5-minute wall buckets only if 5 rows present
        g["bucket"] = g["ts"].dt.floor("5min")
        for bkt, gb in g.groupby("bucket", sort=True):
            if len(gb) != 5:
                continue
            if not (gb["volume"] > 0).all():
                continue
            # ensure exact 1-minute spacing
            diffs = gb["ts"].sort_values().diff().dropna()
            if not (diffs == pd.Timedelta(minutes=1)).all():
                continue
            rows.append(
                {
                    "code": code,
                    "date": gb["date"].iloc[0],
                    "bucket": bkt,
                    "open": float(gb["open"].iloc[0]),
                    "high": float(gb["high"].max()),
                    "low": float(gb["low"].min()),
                    "close": float(gb["close"].iloc[-1]),
                    "volume": float(gb["volume"].sum()),
                    "complete_ts": gb["ts"].iloc[-1],
                }
            )
    return pd.DataFrame(rows)


def first_P_events(bars5: pd.DataFrame, session_open_hhmm: str = "09:00") -> pd.DataFrame:
    """Emit first P per code-date after +15m and before 14:00 KST."""
    events = []
    for (code, date), g in bars5.groupby(["code", "date"], sort=False):
        g = g.sort_values("bucket").reset_index(drop=True)
        open_ts = pd.Timestamp(f"{date} {session_open_hhmm}")
        earliest = open_ts + pd.Timedelta(minutes=15)
        deadline = pd.Timestamp(f"{date} 14:00")
        found = None
        for i in range(2, len(g)):
            A, B, C = g.iloc[i - 2], g.iloc[i - 1], g.iloc[i]
            if C["complete_ts"] < earliest or C["complete_ts"] > deadline:
                continue
            if not (B["low"] > A["low"] and B["close"] < A["close"] and C["close"] > max(A["high"], B["high"])):
                continue
            found = {
                "code": code,
                "date": date,
                "signal_ts": C["complete_ts"],
                "entry_proxy_rule": "next_1m_open_PRICE_PROXY",
                "A_bucket": A["bucket"],
                "B_bucket": B["bucket"],
                "C_bucket": C["bucket"],
                "C_close": C["close"],
                "exclude_reason": "",
            }
            break
        if found is None:
            events.append(
                {
                    "code": code,
                    "date": date,
                    "signal_ts": pd.NaT,
                    "entry_proxy_rule": "",
                    "A_bucket": pd.NaT,
                    "B_bucket": pd.NaT,
                    "C_bucket": pd.NaT,
                    "C_close": np.nan,
                    "exclude_reason": "NO_P_IN_WINDOW",
                }
            )
        else:
            events.append(found)
    return pd.DataFrame(events)


def attach_flow_flags(events: pd.DataFrame, flow: pd.DataFrame | None) -> pd.DataFrame:
    """
    Expected flow columns:
      code, available_at, round_id, revision, foreign_net_qty, inst_net_qty, session_date
    As-of latest three distinct rounds with available_at <= signal_ts same day.
    """
    out = events.copy()
    for col in (
        "F",
        "I",
        "flow_status",
        "n_rounds",
        "age_min",
        "foreign_N0",
        "foreign_N1",
        "foreign_N2",
        "inst_N0",
        "inst_N1",
        "inst_N2",
    ):
        out[col] = "UNKNOWN" if col in ("F", "I", "flow_status") else np.nan

    if flow is None or flow.empty or out.empty:
        out["flow_status"] = "MISSING_FLOW_FILE"
        return out

    flow = flow.copy()
    flow["available_at"] = pd.to_datetime(flow["available_at"])
    for idx, ev in out.iterrows():
        if pd.isna(ev.get("signal_ts")):
            out.at[idx, "flow_status"] = "NO_SIGNAL"
            continue
        sig = pd.to_datetime(ev["signal_ts"])
        sub = flow[
            (flow["code"].astype(str) == str(ev["code"]))
            & (flow["available_at"] <= sig)
            & (flow["available_at"].dt.strftime("%Y-%m-%d") == str(ev["date"]))
        ].sort_values("available_at")
        # distinct rounds: last observation per round_id
        if "round_id" in sub.columns:
            sub = sub.groupby("round_id", as_index=False).tail(1).sort_values("available_at")
        if len(sub) < 3:
            out.at[idx, "flow_status"] = "FEWER_THAN_3_ROUNDS"
            out.at[idx, "n_rounds"] = len(sub)
            continue
        last3 = sub.tail(3).reset_index(drop=True)
        age = (sig - last3.iloc[-1]["available_at"]).total_seconds() / 60.0
        out.at[idx, "age_min"] = age
        out.at[idx, "n_rounds"] = 3
        if age > 90:
            out.at[idx, "flow_status"] = "STALE_GT_90M"
            continue
        fvals = last3["foreign_net_qty"].astype(float).tolist()
        ivals = last3["inst_net_qty"].astype(float).tolist()
        out.at[idx, "foreign_N0"] = fvals[0]
        out.at[idx, "foreign_N1"] = fvals[1]
        out.at[idx, "foreign_N2"] = fvals[2]
        out.at[idx, "inst_N0"] = ivals[0]
        out.at[idx, "inst_N1"] = ivals[1]
        out.at[idx, "inst_N2"] = ivals[2]
        F = fvals[2] > 0 and (fvals[1] - fvals[0]) > 0 and (fvals[2] - fvals[1]) > 0
        I = ivals[2] > 0 and (ivals[1] - ivals[0]) > 0 and (ivals[2] - ivals[1]) > 0
        out.at[idx, "F"] = bool(F)
        out.at[idx, "I"] = bool(I)
        out.at[idx, "flow_status"] = "OK"
    return out


def eval_barriers(events: pd.DataFrame, bars1: pd.DataFrame) -> pd.DataFrame:
    """PRICE_PROXY entry = next 1m open after signal_ts; +3%/-2%/30m."""
    bars1 = bars1.copy()
    bars1["ts"] = pd.to_datetime(bars1["date"].astype(str) + " " + bars1["time"].astype(str))
    bars1 = bars1.sort_values(["code", "ts"])
    rows = []
    for _, ev in events.iterrows():
        base = {k: ev.get(k) for k in ev.index}
        if pd.isna(ev.get("signal_ts")) or ev.get("exclude_reason") == "NO_P_IN_WINDOW":
            base.update(
                {
                    "entry_model": "",
                    "entry_px": np.nan,
                    "outcome": "NO_SIGNAL",
                    "ret_stopfirst": np.nan,
                    "ambiguous_same_bar": False,
                }
            )
            rows.append(base)
            continue
        sig = pd.to_datetime(ev["signal_ts"])
        g = bars1[(bars1["code"].astype(str) == str(ev["code"])) & (bars1["ts"] > sig)]
        if g.empty:
            base.update(
                {
                    "entry_model": "PRICE_PROXY",
                    "entry_px": np.nan,
                    "outcome": "NO_NEXT_BAR",
                    "ret_stopfirst": np.nan,
                    "ambiguous_same_bar": False,
                }
            )
            rows.append(base)
            continue
        entry = g.iloc[0]
        entry_px = float(entry["open"])
        end = entry["ts"] + pd.Timedelta(minutes=30)
        path = g[(g["ts"] >= entry["ts"]) & (g["ts"] <= end)]
        target = entry_px * 1.03
        stop = entry_px * 0.98
        outcome = "no_hit"
        ret = float(path.iloc[-1]["close"]) / entry_px - 1.0 if len(path) else np.nan
        ambiguous = False
        for _, bar in path.iterrows():
            hit_t = float(bar["high"]) >= target
            hit_s = float(bar["low"]) <= stop
            if hit_t and hit_s:
                ambiguous = True
                outcome = "stop_first_ambiguous"
                ret = float(bar["low"]) / entry_px - 1.0  # stop-first primary
                break
            if hit_s:
                outcome = "stop"
                # gap through stop: use observable low/open
                px = min(float(bar["open"]), stop) if float(bar["open"]) < stop else stop
                # if open already through, use open
                if float(bar["open"]) < stop:
                    px = float(bar["open"])
                ret = px / entry_px - 1.0
                break
            if hit_t:
                outcome = "target"
                px = max(float(bar["open"]), target) if float(bar["open"]) > target else target
                ret = px / entry_px - 1.0
                break
        base.update(
            {
                "entry_model": "PRICE_PROXY",
                "entry_px": entry_px,
                "entry_ts": entry["ts"],
                "outcome": outcome,
                "ret_stopfirst": ret,
                "ambiguous_same_bar": ambiguous,
                "price_proxy_disclaimer": "NOT_A_FILL_GUARANTEE",
            }
        )
        rows.append(base)
    return pd.DataFrame(rows)


def summarize(df: pd.DataFrame, mask: pd.Series, name: str) -> dict:
    sub = df[mask].copy()
    n = len(sub)
    if n == 0:
        return {"model": name, "n": 0}
    # success prob keeps no_hit in denominator; exclude only NO_SIGNAL/NO_NEXT_BAR
    tradable = sub[sub["outcome"].isin(["target", "stop", "no_hit", "stop_first_ambiguous"])]
    nt = len(tradable)
    p_target = (tradable["outcome"] == "target").mean() if nt else np.nan
    return {
        "model": name,
        "n": int(n),
        "n_tradable": int(nt),
        "p_target_before_stop_30m": float(p_target) if nt else None,
        "mean_ret_stopfirst": float(tradable["ret_stopfirst"].mean()) if nt else None,
        "median_ret_stopfirst": float(tradable["ret_stopfirst"].median()) if nt else None,
        "ambiguous_rate": float(tradable["ambiguous_same_bar"].mean()) if nt else None,
        "note": "NUMERICS_ONLY_IF_DATA_PRESENT",
    }


def write_blocked_artifacts(reason: str, paths: Paths, inputs_hash: dict):
    (ROOT / "FLOW_AVAILABILITY.csv").write_text(
        "status,detail\n"
        f"BLOCKED_MISSING_POINT_IN_TIME_FLOW,{reason}\n"
        f"watchlist,{paths.watchlist}\n"
        f"bars_1m,{paths.bars_1m}\n"
        f"flow_investor,{paths.flow_investor}\n",
        encoding="utf-8",
    )
    # SIGNAL / MODEL comparison: headers only + blocked row — no fake 0% strategy failure
    pd.DataFrame(
        columns=[
            "code",
            "date",
            "signal_ts",
            "exclude_reason",
            "F",
            "I",
            "flow_status",
            "entry_model",
            "outcome",
            "ret_stopfirst",
        ]
    ).to_csv(ROOT / "SIGNAL_LEDGER.csv", index=False)
    pd.DataFrame(
        [
            {
                "model": "P",
                "n": None,
                "status": "NOT_RUN",
                "reason": reason,
            },
            {
                "model": "P+F",
                "n": None,
                "status": "NOT_RUN",
                "reason": reason,
            },
            {
                "model": "P+I",
                "n": None,
                "status": "NOT_RUN",
                "reason": reason,
            },
            {
                "model": "P+F+I",
                "n": None,
                "status": "NOT_RUN",
                "reason": "BLOCKED_MISSING_POINT_IN_TIME_FLOW",
            },
        ]
    ).to_csv(ROOT / "MODEL_COMPARISON.csv", index=False)
    pd.DataFrame(columns=["date", "model", "n", "p_target", "mean_ret"]).to_csv(
        ROOT / "DAILY_RESULTS.csv", index=False
    )
    (ROOT / "logs" / "run_status.json").write_text(
        json.dumps(
            {
                "DATA_STATUS": "BLOCKED_MISSING_POINT_IN_TIME_FLOW",
                "reason": reason,
                "paths": {k: str(v) if v else None for k, v in paths.__dict__.items()},
                "spec_sha256": sha256(SPEC_PATH),
                "inputs_hash": inputs_hash,
                "ADOPTED": "NO",
                "LIVE_ORDER_ENABLED": "NO",
                "planning": "DONE",
                "code": "DONE",
                "backtest_execution": "NOT_RUN_BLOCKED",
                "validation": "NOT_APPLICABLE_NO_FLOW",
                "adoption": "NO",
                "deploy": "NO",
                "finished_at_utc": datetime.now(timezone.utc).isoformat(),
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--data-dir",
        type=Path,
        default=ROOT / "data_mount",
        help="Read-only mount of watchlist/1m/flow CSVs",
    )
    args = ap.parse_args()
    spec = load_spec()
    assert spec["ADOPTED"] == "NO"
    paths = resolve_paths(args.data_dir)
    inputs_hash = {}
    for k, v in paths.__dict__.items():
        if v and Path(v).exists():
            inputs_hash[k] = {"path": str(v), "sha256": sha256(Path(v))}

    if paths.flow_investor is None:
        write_blocked_artifacts(
            "investor intraday point-in-time flow CSV not found under data_dir",
            paths,
            inputs_hash,
        )
        print("DATA_STATUS=BLOCKED_MISSING_POINT_IN_TIME_FLOW")
        return

    if paths.bars_1m is None:
        write_blocked_artifacts("bars_1m not found (flow present but price missing)", paths, inputs_hash)
        print("DATA_STATUS=BLOCKED_MISSING_PRICE_BARS")
        return

    bars1 = pd.read_csv(paths.bars_1m)
    flow = pd.read_csv(paths.flow_investor)
    bars5 = build_5m(bars1)
    events = first_P_events(bars5)
    events = attach_flow_flags(events, flow)
    scored = eval_barriers(events, bars1)
    scored.to_csv(ROOT / "SIGNAL_LEDGER.csv", index=False)

    flow_ok = scored["flow_status"] == "OK"
    comps = [
        summarize(scored, scored["outcome"].notna(), "P_full_population"),
        summarize(scored, flow_ok, "P_on_flow_observable"),
        summarize(scored, flow_ok & (scored["F"] == True), "P+F"),  # noqa: E712
        summarize(scored, flow_ok & (scored["I"] == True), "P+I"),  # noqa: E712
        summarize(
            scored,
            flow_ok & (scored["F"] == True) & (scored["I"] == True),  # noqa: E712
            "P+F+I",
        ),
    ]
    pd.DataFrame(comps).to_csv(ROOT / "MODEL_COMPARISON.csv", index=False)
    scored.assign(date=scored["date"]).groupby(["date"]).size().reset_index(name="n").to_csv(
        ROOT / "DAILY_RESULTS.csv", index=False
    )
    scored["flow_status"].value_counts().rename_axis("flow_status").reset_index(name="n").to_csv(
        ROOT / "FLOW_AVAILABILITY.csv", index=False
    )
    (ROOT / "logs" / "run_status.json").write_text(
        json.dumps(
            {
                "DATA_STATUS": "RAN_WITH_PIT_FLOW",
                "spec_sha256": sha256(SPEC_PATH),
                "inputs_hash": inputs_hash,
                "ADOPTED": "NO",
                "LIVE_ORDER_ENABLED": "NO",
                "comparisons": comps,
            },
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )
    print(json.dumps(comps, indent=2, default=str))


if __name__ == "__main__":
    main()

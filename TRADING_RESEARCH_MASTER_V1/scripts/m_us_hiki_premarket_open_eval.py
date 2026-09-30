#!/usr/bin/env python3
"""
US HI-KI PREMARKET → OPEN CAPTURE evaluator (research only).

ADOPTED=NO LIVE_ORDER_ENABLED=NO PRODUCTION_CHANGE_ALLOWED=NO

If required inputs are missing, writes NOT_LOCATED status and exits 0.
When inputs exist, builds entry×exit grid ledgers without peeking post-open
when labeling selection features.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "us_hiki_premarket_open"
OUT_LEDGER = ROOT / "ledgers"
OUT_REPORT = ROOT / "reports"
OUT_LOG = ROOT / "logs"

REQUIRED = {
    "candidates": DATA / "hiki_prev_day_candidates.csv",
    "premarket": DATA / "us_premarket_1m.csv",
    "official_open": DATA / "us_official_open.csv",
}
OPTIONAL = {
    "seconds": DATA / "us_open_seconds.csv",
    "imbalance": DATA / "us_noii_or_imbalance.csv",
    "premarket_1s": DATA / "us_premarket_1s.csv",
}

ENTRY_TIMES = ("09:20", "09:25", "09:28", "09:29")
# exit_id -> (kind, offset_seconds or None)
EXITS = {
    "X_AUCTION": ("opening_cross", None),
    "X_OPEN_5s": ("second", 5),
    "X_OPEN_15s": ("second", 15),
    "X_OPEN_30s": ("second", 30),
    "X_OPEN_60s": ("second", 60),
    "X_OPEN_5m": ("minute_proxy", 300),
}


def locate_inputs() -> dict:
    found = {}
    missing = {}
    for k, p in REQUIRED.items():
        if p.exists():
            found[k] = str(p)
        else:
            missing[k] = str(p)
    optional = {}
    for k, p in OPTIONAL.items():
        if p.exists():
            optional[k] = str(p)
    return {"found": found, "missing_required": missing, "optional_found": optional}


def nearest_bar_price(pm: pd.DataFrame, symbol: str, date, hhmm: str):
    """Return last available premarket close at or before date+hhmm ET."""
    # expects columns: ts_et, symbol, close, dollar_volume, volume, high
    sub = pm[(pm["symbol"] == symbol) & (pm["date"] == date)].copy()
    if sub.empty:
        return None
    sub = sub.sort_values("ts_et")
    target = pd.Timestamp(f"{date} {hhmm}:00")
    # ts_et may be tz-aware; compare as string HH:MM if needed
    if pd.api.types.is_datetime64_any_dtype(sub["ts_et"]):
        sub["hhmm"] = sub["ts_et"].dt.strftime("%H:%M")
        eligible = sub[sub["ts_et"] <= target]
    else:
        sub["hhmm"] = sub["ts_et"].astype(str).str[11:16]
        eligible = sub[sub["hhmm"] <= hhmm]
    if eligible.empty:
        return None
    row = eligible.iloc[-1]
    return {
        "entry_ts": str(row["ts_et"]),
        "entry_px": float(row["close"]),
        "pm_high": float(sub["high"].max()) if "high" in sub else None,
        "dollar_volume": float(sub["dollar_volume"].sum()) if "dollar_volume" in sub else None,
    }


def run_grid(cands: pd.DataFrame, pm: pd.DataFrame, opens: pd.DataFrame, seconds: pd.DataFrame | None):
    """
    Baseline selection: within each date, take HI-KI rank<=3 as RESEARCH_PROXY
    for '1~3 picks' until feature score model is supplied.
    Contrast C0: top PM return among HI-KI20 at 09:25.
    """
    rows = []
    opens = opens.copy()
    opens["date"] = opens["date"].astype(str)
    cands = cands.copy()
    cands["date"] = cands["date"].astype(str)
    pm = pm.copy()
    pm["date"] = pm["date"].astype(str) if "date" in pm.columns else pd.to_datetime(pm["ts_et"]).dt.strftime("%Y-%m-%d")

    for date, g in cands.groupby("date"):
        g = g.sort_values("rank")
        picks_hiki = g.head(3)
        # C0 contrast needs pm returns — compute at 09:25
        c0_rows = []
        for _, r in g.iterrows():
            snap = nearest_bar_price(pm, r["symbol"], date, "09:25")
            if not snap or pd.isna(r.get("prior_close")):
                continue
            ret = snap["entry_px"] / float(r["prior_close"]) - 1.0
            c0_rows.append((ret, r["symbol"], r["rank"], snap))
        c0_rows.sort(reverse=True, key=lambda x: x[0])
        picks_c0 = c0_rows[:3]

        for book, picks in (
            ("HIKI_RANK_PROXY", [(None, r["symbol"], r["rank"], None) for _, r in picks_hiki.iterrows()]),
            ("C0_PM_RETURN_TOP", picks_c0),
        ):
            for _, symbol, rank, snap_pref in picks:
                o = opens[(opens["date"] == date) & (opens["symbol"] == symbol)]
                if o.empty:
                    official = None
                else:
                    official = float(o.iloc[0]["official_open"])
                for entry in ENTRY_TIMES:
                    snap = (
                        snap_pref
                        if (snap_pref is not None and entry == "09:25")
                        else nearest_bar_price(pm, symbol, date, entry)
                    )
                    if not snap:
                        for exit_id in EXITS:
                            rows.append(
                                {
                                    "date": date,
                                    "symbol": symbol,
                                    "book": book,
                                    "hiki_rank": rank,
                                    "entry": entry,
                                    "exit_id": exit_id,
                                    "status": "NO_ENTRY_BAR",
                                    "ret_gross": None,
                                }
                            )
                        continue
                    for exit_id, (kind, off) in EXITS.items():
                        status = "OK"
                        exit_px = None
                        exit_model = kind
                        if kind == "opening_cross":
                            if official is None:
                                status = "NO_OFFICIAL_OPEN"
                            else:
                                exit_px = official
                        elif kind == "second":
                            if seconds is None or seconds.empty:
                                status = "NOT_LOCATED_SECONDS"
                                exit_model = "second"
                            else:
                                # expect ts at/after 09:30:00 + off
                                status = "SECONDS_PRESENT_BUT_JOIN_TODO"
                                # conservative: leave unset until join implemented on real schema
                                exit_px = None
                        elif kind == "minute_proxy":
                            # 09:35 from premarket file won't exist; need regular session 1m
                            status = "NOT_LOCATED_REG_1M_FOR_0935"
                        ret = None
                        if exit_px is not None and snap["entry_px"] > 0:
                            ret = exit_px / snap["entry_px"] - 1.0
                        rows.append(
                            {
                                "date": date,
                                "symbol": symbol,
                                "book": book,
                                "hiki_rank": rank,
                                "entry": entry,
                                "entry_ts": snap["entry_ts"],
                                "entry_px": snap["entry_px"],
                                "exit_id": exit_id,
                                "exit_model": exit_model,
                                "exit_px": exit_px,
                                "status": status,
                                "ret_gross": ret,
                                "fee_assumption": "NOT_APPLIED_UNTIL_BROKER_FEE_KNOWN",
                            }
                        )
    return pd.DataFrame(rows)


def main():
    OUT_LEDGER.mkdir(parents=True, exist_ok=True)
    OUT_REPORT.mkdir(parents=True, exist_ok=True)
    OUT_LOG.mkdir(parents=True, exist_ok=True)
    DATA.mkdir(parents=True, exist_ok=True)

    loc = locate_inputs()
    status_path = OUT_REPORT / "M_US_HIKI_PREMARKET_OPEN_STATUS.json"
    if loc["missing_required"]:
        payload = {
            "module": "US_HI-KI_PREMARKET_OPEN_CAPTURE",
            "state": "SPEC_READY_NOT_TESTED",
            "reason": "REQUIRED_INPUTS_NOT_LOCATED",
            "flags": {
                "ADOPTED": "NO",
                "LIVE_ORDER_ENABLED": "NO",
                "PRODUCTION_CHANGE_ALLOWED": "NO",
            },
            "inputs": loc,
            "spec": str(ROOT / "specs/M_US_HIKI_PREMARKET_OPEN_CAPTURE_SPEC.md"),
            "note": "Not a negative-PnL failure. Place CSVs under data/us_hiki_premarket_open/ and re-run.",
        }
        status_path.write_text(json.dumps(payload, indent=2))
        print(json.dumps(payload, indent=2))
        return

    cands = pd.read_csv(REQUIRED["candidates"])
    pm = pd.read_csv(REQUIRED["premarket"])
    opens = pd.read_csv(REQUIRED["official_open"])
    seconds = pd.read_csv(OPTIONAL["seconds"]) if OPTIONAL["seconds"].exists() else None
    ledger = run_grid(cands, pm, opens, seconds)
    ledger_path = OUT_LEDGER / "M_US_HIKI_PREMARKET_OPEN_grid.csv"
    ledger.to_csv(ledger_path, index=False)

    ok = ledger[ledger["status"] == "OK"]
    summary = {
        "module": "US_HI-KI_PREMARKET_OPEN_CAPTURE",
        "state": "PARTIAL_OR_COMPLETE",
        "n_rows": int(len(ledger)),
        "n_ok": int(len(ok)),
        "mean_ret_by_exit": ok.groupby("exit_id")["ret_gross"].mean().dropna().to_dict() if len(ok) else {},
        "ledger": str(ledger_path),
        "flags": {"ADOPTED": "NO", "LIVE_ORDER_ENABLED": "NO"},
        "inputs": loc,
    }
    status_path.write_text(json.dumps(summary, indent=2, default=str))
    print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    main()

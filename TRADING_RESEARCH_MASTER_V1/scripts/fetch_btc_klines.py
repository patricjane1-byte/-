#!/usr/bin/env python3
"""Re-fetch BTCUSDT public klines from data-api.binance.vision (research sample)."""
from __future__ import annotations

import argparse
import hashlib
import json
import time
import urllib.request
from pathlib import Path

UA = {"User-Agent": "Mozilla/5.0 research-bot"}


def fetch(symbol: str, interval: str, start_ms: int, end_ms: int, limit: int = 1000):
    url = (
        f"https://data-api.binance.vision/api/v3/klines?symbol={symbol}"
        f"&interval={interval}&startTime={start_ms}&endTime={end_ms}&limit={limit}"
    )
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=45) as r:
        return json.loads(r.read().decode())


def pull(symbol: str, interval: str, start_ms: int, end_ms: int, step_ms: int):
    rows = []
    cur = start_ms
    while cur < end_ms:
        batch = []
        for attempt in range(5):
            try:
                batch = fetch(symbol, interval, cur, end_ms)
                break
            except Exception as e:
                print("retry", interval, attempt, e)
                time.sleep(1.2 * (attempt + 1))
        if not batch:
            break
        rows.extend(batch)
        cur = batch[-1][0] + step_ms
        time.sleep(0.08)
        if len(batch) < 1000:
            break
    seen = set()
    uniq = []
    for b in rows:
        if b[0] not in seen:
            seen.add(b[0])
            uniq.append(b)
    uniq.sort(key=lambda x: x[0])
    return uniq


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=180)
    ap.add_argument("--out", type=Path, default=Path(__file__).resolve().parents[1] / "data/btc")
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    end = int(time.time() * 1000)
    start = end - args.days * 24 * 60 * 60 * 1000
    u1 = pull("BTCUSDT", "1m", start, end, 60_000)
    u5 = pull("BTCUSDT", "5m", start, end, 5 * 60_000)

    def write(path: Path, uniq):
        with path.open("w") as f:
            f.write(
                "open_time,open,high,low,close,volume,close_time,quote_volume,trades,taker_buy_base,taker_buy_quote\n"
            )
            for b in uniq:
                f.write(",".join(str(b[i]) for i in range(11)) + "\n")

    p1 = args.out / "BTCUSDT_1m_binance_vision_public.csv"
    p5 = args.out / "BTCUSDT_5m_binance_vision_public.csv"
    write(p1, u1)
    write(p5, u5)
    meta = {
        "source": "https://data-api.binance.vision/api/v3/klines",
        "symbol": "BTCUSDT",
        "days": args.days,
        "bars_1m": len(u1),
        "bars_5m": len(u5),
        "start_1m_ms": u1[0][0] if u1 else None,
        "end_1m_ms": u1[-1][0] if u1 else None,
        "sha256_1m": hashlib.sha256(p1.read_bytes()).hexdigest(),
        "sha256_5m": hashlib.sha256(p5.read_bytes()).hexdigest(),
        "disclaimer": "RESEARCH_SAMPLE; fee separate ASSUMPTION",
    }
    (args.out / "DATA_META.json").write_text(json.dumps(meta, indent=2))
    print(json.dumps(meta, indent=2))


if __name__ == "__main__":
    main()

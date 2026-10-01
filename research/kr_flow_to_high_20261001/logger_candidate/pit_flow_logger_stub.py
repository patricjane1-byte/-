#!/usr/bin/env python3
"""Dry-run stub for PIT flow logging. Default: no network, no service install."""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

FIELDS = [
    "source",
    "code",
    "venue",
    "event_at",
    "available_at",
    "received_at",
    "update_id",
    "revision",
    "buy_qty",
    "sell_qty",
    "net_qty",
    "unit",
    "raw_response_redacted",
    "status",
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=Path(__file__).with_name("schema_sample.csv"))
    ap.add_argument("--live-poll", action="store_true", help="DISABLED in research default; refuse unless later approved")
    args = ap.parse_args()
    if args.live_poll:
        raise SystemExit("LIVE_POLL_REFUSED: research stub only; no API calls without separate approval")
    with args.out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerow(
            {
                "source": "investor_trend_estimate",
                "code": "EXAMPLE",
                "venue": "KRX",
                "event_at": "",
                "available_at": "",
                "received_at": "",
                "update_id": "",
                "revision": "",
                "buy_qty": "",
                "sell_qty": "",
                "net_qty": "",
                "unit": "shares",
                "raw_response_redacted": "",
                "status": "SCHEMA_ONLY",
            }
        )
    print("wrote", args.out)


if __name__ == "__main__":
    main()

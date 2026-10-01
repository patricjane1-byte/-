# P0 Inventory — CURSOR_SCALP_CLOSE research

Run flags: `ADOPTED=NO` `LIVE_ORDER_ENABLED=NO` `PRODUCTION_CHANGE_ALLOWED=NO`

## Attachment / MASTER status

| Item | Status | Notes |
|------|--------|-------|
| `CURSOR_SCALP_CLOSE_MASTER_V1.txt` | **NOT_LOCATED** | Not in workspace, assets, uploads, /tmp, PC worker |
| `TRADING_RESEARCH_MASTER_V1/` ZIP | **NOT_LOCATED** | Same |
| Self-hosted PC worker | **NOT_CONNECTED** | `list-self-hosted-workers` empty |
| Connected git repo | `github.com/patricjane1-byte/-` | Web-novel Streamlit app only; no market RAW |
| Existing MAIN-H1 / HI-KI / KIS / systemd / OOS | **NOT_LOCATED** (this VM) | Will not modify; not present here |

Execution brief used: user message body dated 2026-09-30 (full module checklist). Marked as `EXECUTION_BRIEF_FROM_USER_MESSAGE.txt` — not a substitute for the missing MASTER file hash.

## Data inventory by market

| Market | Resolution | Located? | Action |
|--------|------------|----------|--------|
| KR equities | daily / minute / ticks / book | NOT_LOCATED | M4/M5/M6 → NOT_TESTED |
| US equities | daily / minute / premarket / extended | NOT_LOCATED | M1/M2/M3/M6 → NOT_TESTED |
| BTC spot | 1m / 5m public klines | **FETCHABLE** (Binance public API) | M7 runnable with RESEARCH sample |
| Official open / first observed price ledgers | NOT_LOCATED | — |
| Supply/demand (기관·외국인) | NOT_LOCATED | M4 NOT_TESTED |
| News timestamps / themes | NOT_LOCATED | M4 C4 NOT_TESTED |

## Work queue

| Module | Status | Plan |
|--------|--------|------|
| P0 | IN_PROGRESS | This inventory |
| M1 US TOP20 | NOT_TESTED / NOT_LOCATED | Needs US universe minute panel |
| M2 US premarket video | NOT_TESTED / NOT_LOCATED | Needs premarket volume + second bars |
| M3 Open scalp paths | NOT_TESTED / NOT_LOCATED | Needs second/minute US/KR |
| M4 KR close supply | NOT_TESTED / NOT_LOCATED | Needs KR daily + supply |
| M5 HIGHLOCK H0/H1 | NOT_TESTED / NOT_LOCATED | Needs KR minute + next official open |
| M6 Session exits | NOT_TESTED / NOT_LOCATED | Needs session calendars + fills |
| M7 BTC public 4 | **RUN** | Fetch strategies + public BTC sample + reproduce |
| M_US_HIKI_PREMARKET_OPEN | **SPEC_READY / NOT_TESTED** | Separate axis from Gap-and-Go; inputs NOT_LOCATED on this VM |
| Hummingbot MM | DEFERRED | Needs book/queue/inventory — separate study |
| M8 Report | UPDATED | FINAL_REPORT + premkt-open note |

## Rules preserved

- Do not treat ChatGPT "file not found" as proof server has no data — here the connected VM truly lacks market RAW.
- NOT_LOCATED ≠ negative PnL failure.
- Do not halt other modules for one missing dataset.
- No production / collector / RAW mutation.
- No live orders.

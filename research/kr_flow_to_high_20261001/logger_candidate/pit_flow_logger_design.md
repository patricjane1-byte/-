# Point-in-time flow logger candidate (NOT installed / NOT started)

ADOPTED=NO · LIVE_ORDER_ENABLED=NO · 본 문서는 서비스 설치·재시작 지시가 아니다.

## Goal
Append-only capture of provisional investor / program / broker-window updates with proven `available_at`/`received_at`, without modifying existing MAIN collectors, auth ownership, or systemd units.

## Streams (keep separate — never merge into one score)
1. `investor_trend_estimate` (institution + foreign provisional)
2. program trading per symbol
3. broker-window / foreign desk (≠ foreign account confirmation)

## Suggested record schema (CSV/JSONL)
`source,code,venue,event_at,available_at,received_at,update_id,revision,buy_qty,sell_qty,net_qty,unit,raw_response_redacted,status`

- `UNKNOWN` vs `0` must remain distinct (`status=MISSING` vs numeric zero).
- `raw_response_redacted`: strip secrets, account numbers, tokens before append.
- Deduplicate: same `update_id`+`revision`+payload hash → not a new round.

## Integration constraints
- Do not take over existing KIS token refresh ownership.
- Respect API rate limits; poll schedules must be documented; no burst that starves MAIN.
- Write under a **new** path e.g. `research_data/pit_flow/` — never rewrite historical RAW.
- Prefer optional side process / manual cron candidate — **no** `systemctl enable/restart` in this research.

## Reference docs (re-check before any future API use)
- https://github.com/koreainvestment/open-trading-api/blob/main/examples_llm/domestic_stock/investor_trend_estimate/investor_trend_estimate.py
- https://securities.koreainvestment.com/pro_help/6441.html
- https://securities.koreainvestment.com/force_help/6469.html

## Candidate stub
See `pit_flow_logger_stub.py` — dry-run only, writes schema sample, performs no network I/O unless explicitly passed `--live-poll` (default off; still research-only and disabled here).

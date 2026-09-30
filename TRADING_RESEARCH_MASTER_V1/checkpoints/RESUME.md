# Resume checkpoint

## Flags
ADOPTED=NO  
LIVE_ORDER_ENABLED=NO  
PRODUCTION_CHANGE_ALLOWED=NO  

## Done
- P0 inventory written (`inventory/P0_INVENTORY.md`)
- M7 strategy sources fetched + hashed
- BTCUSDT 180d 1m/5m public sample fetched (Vision API)
- M7 backtest engine + ledgers + summary JSON
- M1–M6 marked NOT_LOCATED on this VM

## Next when data arrives
1. Attach `CURSOR_SCALP_CLOSE_MASTER_V1.txt` / ZIP or connect PC worker
2. Run M5 HIGHLOCK H0/H1 if KR minute + next official open present
3. Run M1 US TOP20 only on audited full-universe minute panel
4. Do not re-run M7 unless comparing same hashes / longer window
5. Hummingbot MM remains separate (book/queue/inventory)

## Reproduce M7
```bash
# if only .gz present, script reads gzip directly
python3 TRADING_RESEARCH_MASTER_V1/scripts/m7_btc_public_backtest.py
# or re-fetch
python3 TRADING_RESEARCH_MASTER_V1/scripts/fetch_btc_klines.py --days 180
```

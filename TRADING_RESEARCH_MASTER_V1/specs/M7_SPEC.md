# M7 SPEC — BTC public strategies (research)

## Flags
ADOPTED=NO · LIVE_ORDER_ENABLED=NO · PRODUCTION_CHANGE_ALLOWED=NO

## Sources
- Strategy files: `freqtrade/freqtrade-strategies` `user_data/strategies/berlinguyinca/`
  - BinHV45.py / ClucMay72018.py / Scalp.py / ReinforcedSmoothScalp.py
  - SHA256 recorded in `specs/STRATEGY_SOURCE_HASHES.txt`
- Price data: Binance Vision public klines (`data-api.binance.vision`) BTCUSDT 1m/5m
  - `api.binance.com` returned HTTP 451 in this VM → Vision used
  - Meta: `data/btc/DATA_META.json`

## Preserved original settings

| Strategy | TF | ROI | SL | Exit signal |
|----------|----|-----|----|-------------|
| BinHV45 | 1m | +1.25% | −5% | none (ROI/SL only) |
| ClucMay72018 | 5m | +1% | −5% | close > BB mid |
| Scalp | 1m | +1% | −4% | open≥EMA_high or stoch cross 70 |
| ReinforcedSmoothScalp | 1m (+5m SMA) | +2% | −10% | open>EMA_high & CCI/fastd/fastk filters |

### Implementation notes matching source
- ClucMay72018: `ema100 = EMA(50)` (name ≠ period).
- Cluc volume: `volume < rolling(30).mean().shift(1) * 20` (upper bound).
- BinHV45 hyperopt defaults used: bbdelta=7, closedelta=17, tail=25 from `buy_params`.
- ReinforcedSmoothScalp: 5m SMA50 merged with **shift(1)+ffill** (no time interpolate into future).
- Default BooleanParameter/IntParameter values from source used for ReinforcedSmoothScalp.

## Engine assumptions (explicit)
1. Signal on closed bar → entry next open.
2. max_open_trades = 1; spot long only; no leverage/pyramiding.
3. Fee ASSUMPTION 0.0005 per side (round-trip 0.10%).
4. Same-bar ROI+SL → stoploss first, flagged `same_bar_conflict`.
5. Indicators via pandas approximations — **not bit-identical** to TA-Lib/Freqtrade.
6. This is **not** a claim of live fill quality or other-exchange PnL.

## Not done in this module
- Hummingbot MM / CEX arb (needs book/queue/inventory).
- Forced 60s/300s exit overlay (separate experiment).
- Full Freqtrade lookahead-analysis / recursive-analysis CLI (engine is custom).
- User's prior BTC flow / 0.5% chase ledgers (NOT_LOCATED here — not re-run).

# FINAL REPORT — CURSOR_SCALP_CLOSE research execution

**ADOPTED = NO**  
**LIVE_ORDER_ENABLED = NO**  
**PRODUCTION_CHANGE_ALLOWED = NO**

---

## 1. 실제 사용한 데이터

| 항목 | 내용 |
|------|------|
| MASTER 파일 | `CURSOR_SCALP_CLOSE_MASTER_V1.txt` **NOT_LOCATED** (첨부 ZIP/PC worker 없음). 실행은 사용자 메시지 본문 체크리스트 기준. |
| 연결 저장소 | `github.com/patricjane1-byte/-` (웹소설 Streamlit). 시장 RAW/기존 MAIN-H1/HI-KI/KIS **없음·미변경**. |
| BTC | Binance Vision 공개 klines `BTCUSDT` 1m/5m, **180일**, 259,200 / 51,840 bars. `api.binance.com`는 HTTP 451 → Vision 사용. |
| BTC 해시 | 원본 CSV sha256은 `data/btc/DATA_META.json`; 저장은 `.csv.gz`. |
| 전략 원본 | `freqtrade/freqtrade-strategies` berlinguyinca 4파일. 해시: `specs/STRATEGY_SOURCE_HASHES.txt` |
| KR/US 분봉·체결·호가·수급 | **NOT_LOCATED** |

수수료는 **편도 0.0005 ASSUMPTION**(왕복 0.10% 비교용). 실계좌 수수료·다른 거래소 수익으로 주장하지 않음.

---

## 2. 모듈별 실제 계산한 내용

### M7 BTC 공개 전략 — **실행 완료**

엔진: 신호 봉 종가 확정 → 다음 봉 시가 진입, 동시 포지션 1, ROI/손절/매도신호 원형 유지, 동일 봉 ROI+SL 충돌 시 손절 우선(플래그).

| 전략 | TF | 거래수 | 비용후 평균 | 승률 | 최대낙폭(복리경로) | 비고 |
|------|----|--------|-------------|------|-------------------|------|
| BinHV45 | 1m | **0** | — | — | — | 180일 중 1분 종가변화 >1.7% 조건이 1회뿐, 결합조건 0건 → **휴면** |
| ClucMay72018 | 5m | **1** | +0.899% | 100% | 0 | 표본 1건(ROI). 통계 의미 없음 |
| Scalp | 1m | **2855** | **−0.092%** | 10.7% | **−92.9%** | 전원 `exit_signal` 청산, ROI 도달 전 청산 우세 |
| ReinforcedSmoothScalp | 1m | **155** | **−0.017%** | 41.9% | −7.1% | 대부분 exit_signal, ROI 1건. 원형 손절 −10% |

원장: `ledgers/M7_*_trades.csv`  
요약: `reports/M7_BTC_PUBLIC_SUMMARY.json`  
재현: `python3 TRADING_RESEARCH_MASTER_V1/scripts/m7_btc_public_backtest.py`

지표는 pandas 근사(TA-Lib 비트동일 아님). Hummingbot 시장조성은 미실행(호가·대기열·재고 필요).

### M1–M6 — **NOT_TESTED / NOT_LOCATED**

미국 전체 분봉, 프리장, 장초 초단위, 국내 수급·HIGHLOCK·세션 청산에 필요한 원장 부재. 음수 실패와 분리. 상세: `reports/M1_M6_NOT_LOCATED.md`

---

## 3. 미실행 항목과 구체적 이유

| 항목 | 이유 |
|------|------|
| MASTER 원문 해시 대조 | 파일 미도착 |
| M1–M6 전부 | KR/US 원자료 NOT_LOCATED |
| Freqtrade CLI lookahead/recursive | 커스텀 엔진; CLI 미설치 |
| 공통 60초/300초 강제청산 | 명세상 별도 실험 — 원형 재현 우선 |
| Hummingbot MM / cross-exchange | 호가·대기열·양쪽 비용 없음 |
| 기존 BTC 0.5% 추격 등과 중복 비교 | 기존 원장 NOT_LOCATED |
| LIVE / 수집기 / MAIN-H1 변경 | 명시적 금지 |

---

## 4. 기존 기준보다 개선된 점 / 악화된 점

**개선(연구 절차)**
- “공개 수익 공식”이 아니라 **공개 코드 원형 + 해시 + 원장**으로 재현.
- BinHV45/Cluc의 0~1건을 실패로 왜곡하지 않고 **표본·조건 희소성**으로 보고.
- Scalp 주석의 “60병렬” 전제와 BTC 1페어·1포지션 전제를 분리.

**악화/부정 결과 (이 표본·가정 하)**
- Scalp는 비용 후 평균 음수 + 복리경로 낙폭 극심 → **채택 근거 없음**.
- ReinforcedSmoothScalp도 비용 후 소폭 음수.
- Cluc 1건·BinHV 0건으로는 수익 우위 주장 불가.

---

## 5. 추가 검증할 후보와 정확한 명세

1. **PC/ZIP 연결 후** MASTER 원문 해시 확인 → M5 H0/H1(종가+28%/14:30+25%)를 KR 분봉+공식 시가로 복원.  
2. **BinHV45**: 더 긴 기간 또는 알트/변동성 구간에서 closedelta 조건 빈도 재측정(파라미터 변경은 원형과 분리해 RESEARCH_PROXY로 표기).  
3. **Scalp**: ROI-only 청산(원본 주석 권고) vs 활성 exit_signal 을 **별도 원장**으로 비교(규칙을 몰래 바꾸지 말 것).  
4. **Cluc**: 다년 5m 표본으로 n 확대 후에만 평균 해석.  
5. **M1**: 미국 전체 후보 분봉 패널 확보 시에만 TOP20 A/B 모형 시작.

---

## 판정 표 (M8 요약)

| 구분 | 결과 |
|------|------|
| 가격 도달/선정(미국·국내) | NOT_TESTED |
| 거래당 손익 (M7) | Scalp/Reinforced 음수 평균; Cluc n=1; BinHV n=0 |
| 실행모형 손익 | 위와 동일(가정 체결·가정 수수료) |
| 계좌 수익 | Scalp 복리경로 −92.9% (1포지션 연속) — 참고용 |
| OOS | 단일 180일 구간; 별도 홀드아웃 분할 없음 → **미선언 OOS** |

후보가 남아도 **ADOPTED=NO**, **LIVE_ORDER_ENABLED=NO** 유지.

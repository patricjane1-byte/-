# M_US_HIKI_PREMARKET_OPEN_CAPTURE — SPEC

**축 이름:** `US HI-KI PREMARKET → OPEN CAPTURE`  
**Gap-and-Go와 분리:** YES (별도 연구축)  
**ADOPTED:** NO  
**LIVE_ORDER_ENABLED:** NO  
**PRODUCTION_CHANGE_ALLOWED:** NO  

이 모듈은 기존 M1/M2/M3 미장 단타·장중 연구를 **대체하지 않는다**.  
질문 하나:

> HI-KI 사전 후보 안에서, 09:30 이후를 예측하지 않고도  
> 프리마켓 매수 → Opening Cross(또는 OPEN±초) 청산만으로  
> 비용·미체결·실패 종목까지 포함해 순이익이 남는가?

---

## 1. Gap-and-Go와의 구분

| | Classic Gap-and-Go | This axis |
|--|-------------------|-----------|
| 선정 | 프리마켓 강세 | HI-KI 사전 후보 ∩ 프리마켓 실유입 ∩ auction |
| 진입 | 대개 09:30 **이후** continuation | **09:20~09:29** (정규장 전) |
| 청산 | 장중 목표가/시간 | **Opening auction / OPEN+Ns** |
| 핵심 리스크 | 개장 후 되돌림·홀드 | 프리마켓 유동성·스프레드·auction 미체결 |
| 성공 정의 | 개장 후 추가 상승 | **OPEN 직전 edge가 끝나는지** |

논문/관측(overnight vs first-30m reverse / overnight–intraday reversal)은  
“OPEN 이후를 버릴 연구 가치”의 **동기**이지, 프리마켓 매수 수익 증명이 아니다.  
원형에 없는 손절·복리 가정을 몰래 넣지 않는다.

---

## 2. 유니버스

1. **전일 HI-KI 후보 20개** (기존 선정 파이프라인 산출물; 이 모듈에서 재발명하지 않음).  
2. 당일 프리마켓 04:00~09:25 America/New_York 관측.  
3. 실패·보합·하락·미체결 후보도 분모에 포함 (성공주만 남기지 않음).  
4. 잡주 펌핑 단독 순위(프리마켓 상승률 TOP)는 **대조군**이지 본선이 아님.

---

## 3. 선정 특징 (09:20~09:28 ET 스냅샷)

입력은 **그 시각까지 관측 가능**한 값만. 미래 OPEN 가격·장중 고가는 선정에 금지.

| ID | Feature | Notes |
|----|---------|-------|
| F01 | 전일 종가 대비 상승률 | prior official close 분모 명시 |
| F02 | 프리마켓 거래대금 | **거래량으로 치환 금지** (원형 유지) |
| F03 | 프리마켓 체결량 증가 | 구간 정의 기록 (예: 직전 5/15분 vs 새벽) |
| F04 | 최근 5/10/20분 상승 기울기 | ET 기준 완료 분봉만 |
| F05 | 프리마켓 고점 대비 현재 위치 | `px / pm_high` |
| F06 | VWAP 위 유지 | PM VWAP 정의·세션 시작 시각 명시 |
| F07 | 스프레드 | 호가 있으면 quote; 없으면 UNRESOLVED |
| F08 | 뉴스/catalyst | **공개시각 있는 것만**; 없으면 제외 또는 별도 레이블 |
| F09 | 마지막 5분 매수세 | 가능하면 trade aggressor; 대리면 RESEARCH_PROXY |
| F10 | Opening imbalance (09:25+) | Nasdaq NOII / NYSE imbalance — 별도 피드 |
| F11 | Indicative opening price 변화 | NOII/paired 정보 |

선정 출력: 매일 **1~3종목** (감시 예산 고정 비교용으로 TOP1/TOP2/TOP3 모두 기록).

### 순위 계층 (선정 품질)
본선 점수 vs 대조군(순수 PM 상승률)을  
적중·잔여(여기선 “OPEN까지 추가 수익”)로 비교.  
너무 늦게 골라도 OPEN 전 잔여가 없으면 실패로 보고.

---

## 4. 진입 × 청산 그리드 (필수 비교)

모든 칸을 **독립 원장**으로 돌린다. 개장 후를 본 뒤 실패한 것만 시가로 되돌리지 않는다.

### Entry times (ET)
`09:20` | `09:25` | `09:28` | `09:29`

### Exit targets
| Exit ID | Definition | Data need |
|---------|------------|-----------|
| X_AUCTION | Opening Cross / official open print | official open |
| X_OPEN_5s | 09:30:05 | **초 단위** |
| X_OPEN_15s | 09:30:15 | 초 단위 |
| X_OPEN_30s | 09:30:30 | 초 단위 |
| X_OPEN_60s | 09:31:00 | 초 또는 1분 대리 표시 |
| X_OPEN_5m | 09:35 | 1분 허용, 원형과 다름 표기 |

필수 매트릭스 예시(최소):

| Entry | Exits |
|-------|-------|
| 09:20 | X_AUCTION |
| 09:25 | X_AUCTION, X_OPEN_5s, X_OPEN_15s, X_OPEN_30s, X_OPEN_60s, X_OPEN_5m |
| 09:28 | X_AUCTION |
| 09:29 | X_AUCTION |

분봉 대리 청산은 `EXIT_MODEL=MINUTE_PROXY`로 표시하고  
초 단위 `EXIT_MODEL=SECOND` / auction `EXIT_MODEL=OPENING_CROSS`와 섞어 평균내지 않는다.

---

## 5. Opening Auction 실행 메모 (연구 vs 실주문)

연구 단계에서는 **가격 도달·공식 open**으로 PnL을 계산한다.  
실주문은 승인 전까지 금지.

참고(브로커 지원은 UNRESOLVED / 별도 확인):
- Nasdaq Opening Cross @ 09:30 ET; MOO/LOO 경로 존재.
- Nasdaq NOII 대략 09:25–09:30 (indicative price, imbalance).
- NYSE opening imbalance / paired / book-clearing 공개.
- MOO 제출 마감·LOO 마감은 거래소·브로커·KIS 지원 여부가 **별도 검증 항목**  
  → `BROKER_MOO_LOO_SUPPORT = UNRESOLVED` (이 SPEC에서 가정하지 않음).

연구 질문과 운영 질문을 분리:
1. 가격 경로상 edge가 OPEN에서 끝나는가?  
2. 우리 계좌/브로커가 auction 주문을 넣을 수 있는가?

---

## 6. 본선 파이프라인 (고정 순서)

```
전일 HI-KI 20
→ PM 04:00~09:25 관측 패널
→ 09:15 이후 상승 유지 필터 (정의 명시)
→ PM high 근처 유지
→ 09:25+ NOII/imbalance + indicative open (있으면)
→ 09:25~09:29 진입 1~3
→ X_AUCTION / OPEN+Ns 청산 그리드
→ 손실·미체결·부분체결·스프레드 포함 원장
→ 날짜별 계좌 손익·최대낙폭 (평균×일수 복리 금지)
```

대조군:
- C0: HI-KI20 중 PM 상승률 TOP1~3 → 동일 청산 그리드  
- C1: 임의/거래대금만 TOP (HI-KI 무시) — 잡주 펌핑 리스크 측정용

---

## 7. 필수 보고 지표

- 거래당: 평균·중앙·승률·최악·TIME 비율  
- 청산별: OPEN vs +5s/+15s/+30s/+60s/+5m **잔여 edge 곡선**  
- 핵심 가설 검정:  
  `mean(09:25→OPEN) ?> mean(09:25→+30s) ?> mean(09:25→+5m)`  
  (부호·크기·날짜 집중·비용 후)  
- 선정: 적중률이 아니라 **선정 이후 OPEN까지 잔여 수익**  
- 누락: NOII 없는 날 / 호가 없는 날 / auction 미거래 종목  
- OOS: 미리 고정한 후반 기간만; 이미 본 구간을 신규 OOS라 하지 않음

---

## 8. 입력 스키마 (도착 시 바로 돌리기 위함)

최소 파일(가칭):

1. `hiki_prev_day_candidates.csv`  
   `date,symbol,rank,prior_close,...`
2. `us_premarket_1m.csv` or better `us_premarket_1s.csv`  
   `ts_et,symbol,open,high,low,close,volume,dollar_volume,...`
3. `us_official_open.csv`  
   `date,symbol,official_open,open_source`
4. `us_open_seconds.csv` (optional but required for +5s/+15s/+30s)  
   `ts_et,symbol,price,...`
5. `us_noii_or_imbalance.csv` (optional layer)  
   `ts_et,symbol,indicative_price,imbalance_qty,side,...`

없으면: 해당 exit/feature만 `NOT_LOCATED`, 가능한 그리드 칸만 실행.

---

## 9. 현재 VM 상태

| Item | Status |
|------|--------|
| HI-KI 후보 원장 | NOT_LOCATED |
| US premarket bars | NOT_LOCATED |
| Official open / seconds | NOT_LOCATED |
| NOII/imbalance | NOT_LOCATED |
| PC worker | NOT_CONNECTED |

→ 모듈 상태: **SPEC_READY / NOT_TESTED** (음수 실패 아님)

데이터 또는 worker가 붙으면 `scripts/m_us_hiki_premarket_open_eval.py`로 그리드 원장 생성.

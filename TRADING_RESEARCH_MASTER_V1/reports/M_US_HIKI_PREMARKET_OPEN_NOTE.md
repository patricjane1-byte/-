# US HI-KI PREMARKET → OPEN CAPTURE — 연구축 등록

**ADOPTED=NO · LIVE_ORDER_ENABLED=NO**

## 합의된 질문
기존 Gap-and-Go(개장 **후** continuation)와 분리한다.

`전일 HI-KI 20 → 프리마켓 실유입·유지 → (가능하면) 09:25+ auction imbalance → 09:20~09:29 매수 → OPEN / OPEN+Ns 청산`

핵심 가설: **장 시작 전에 edge가 끝나는가?**  
예: 09:25→OPEN +1.2%, →+30s +0.7%, →+5m −0.4% 같은 곡선이면 개장 후 초단타를 풀 필요가 없다.

## 이 VM에서 한 일
1. 별도 SPEC 고정: `specs/M_US_HIKI_PREMARKET_OPEN_CAPTURE_SPEC.md`
2. 평가 스크립트: `scripts/m_us_hiki_premarket_open_eval.py`
3. 실행 결과: 필수 CSV **NOT_LOCATED** → `SPEC_READY_NOT_TESTED`  
   (`reports/M_US_HIKI_PREMARKET_OPEN_STATUS.json`)

## 아직 안 한 일 (데이터 필요)
- HI-KI 후보·프리마켓 분/초·공식 open·NOII 원장 로드
- 특징 점수(1~3종목) 본선 vs PM상승률 대조군
- Opening auction vs +5s/+15s/+30s/+60s/+5m 전 그리드
- 브로커 MOO/LOO 지원 확인 (`UNRESOLVED`, 실주문 금지)

## 데이터 넣는 위치
`TRADING_RESEARCH_MASTER_V1/data/us_hiki_premarket_open/`  
스키마는 SPEC §8. 넣은 뒤:

```bash
python3 TRADING_RESEARCH_MASTER_V1/scripts/m_us_hiki_premarket_open_eval.py
```

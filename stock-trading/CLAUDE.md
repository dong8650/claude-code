# CLAUDE.md — 한국 주식 자동매매 시스템 (stock-trading)

> Claude Code가 이 프로젝트를 다룰 때 참고하는 컨텍스트 파일.
> 작업자: dong8650 (N년차 네트워크 엔지니어, CCIE). 홈랩 운영.

---

## 프로젝트 개요
- 목적: pykrx 기반 한국 주식 일봉 자동매매 시스템. 소액(10만원) 실전 타겟.
- 현재 단계: 모의투자(KIS) 자동매매 봇 서버 배포 + 작동 검증 완료 → 전략 엣지 검증 단계.
- 배포 서버: bastion-dc1 (200.200.200.7), Raspberry Pi aarch64 + Ubuntu 6.8. 경로 /data/claude-code/stock-trading.
- 동거 서비스: 같은 서버에 성운궤도(nebular-orbit) 게임 백엔드 → venv 격리로 충돌 회피.

## 핵심 원칙 (절대 어기지 말 것)
1. 일봉 전략이다. 실시간 매매로 바꾸지 말 것. 신호는 하루 1회만 바뀜. 실시간은 HFT·기관 영역이라 개인 라즈베리파이로 경쟁 불가.
2. 종목당 max_position_pct 10% 상한 — 완화 금지. (과거 삼성 79.5% 몰빵 사고 재발 방지)
3. virtual=True (모의투자) — 검증 전 실전 전환 금지.
4. API 키는 secret_config.py(chmod 600)에만. git·노션에 절대 커밋 금지.
5. v3 ML(XGBoost/LSTM) 보류. 엣지 미확인 상태에서 ML은 과적합으로 가짜 엣지만 키움.

## 파일 구조
- trading_v2_1.py    : 신호/지표/백테스트 (v2 결함 7건 수정판)
- kis_broker.py      : KIS 모의투자 API 연동 (python-kis 2.1.6, 실전+모의 동시 인증)
- notifier.py        : 슬랙 알림 (Incoming Webhook, NEAI 방식)
- live_runner.py     : 메인 실행기 (하루 1회 신호→주문→슬랙→로그)
- secret_config.template.py : 설정 템플릿 (→ secret_config.py로 복사, git 제외)
- setup.sh           : aarch64 환경 자동 구성

## 시스템 구조
- 데이터: pykrx OHLCV 일봉 (백테스트) / KIS chart (라이브)
- 지표: MA(5/20), Z-Score(20), RSI(14), ROC(5)
- 전략: 골든크로스 + Z-Score + RSI/ROC → 가중 결합
- 리스크: 켈리(쿼터, 거래 손익률 기반) / 손절 -2% / 익절 +5% / max_position 10%
- 비용: 슬리피지 0.15% + 수수료 0.015% + 거래세 0.23%
- 실행: 신호는 t일 종가, 체결은 t+1일 시가 (룩어헤드 제거)

## 작업 이력

### 2026-06: v2 → v2.1 결함 수정 (7건)
- [치명1] 룩어헤드: 당일 종가로 당일 체결(현실 불가) → 신호 t일 종가, 체결 t+1 시가
- [치명2] 켈리 무의미: 일간 등락률 → 청산 거래 손익률 기반 재구현
- [치명3] 과적합 무방비 → in-sample/out-of-sample 분리
- [중대4] 손절/익절 종가 판정 → t+1 장중 Low/High 현실화
- [중대5] 전환형+상태형 단순합산 → 가중 결합
- [중대6] Hurst 가격 적용 → 로그수익률 기반
- [중대7] 승률 None → 진입-청산 매칭으로 실제 승률·PF 계산
- 룩어헤드 실측(합성): 제거 시 PF 0.62→0.30, 승률 30%→20%. v2 백테스트가 성적 부풀렸음 입증. 양쪽 다 손실 → 엣지 약함, 실데이터 재확인 필요.

### 2026-06: 모의투자 자동매매 봇
- python-kis 2.1.6 / 하루 1회 / 시장가 체결
- 슬랙 알림: 매수🟢 매도🔵 손절🔴 익절🟣 에러⚠️
- 안전장치: virtual 강제확인 / 하루1회 가드 / max_position 상한 / 에러시 슬랙 즉시 / 전과정 CSV

### 진단: 과거 삼성 79.5% 몰빵 사고
시스템에 max_position 10% 상한이 이미 있었음 → 돌렸으면 몰빵 불가능. 문제는 시스템도 지식도 아니라 알면서 안 쓴 것. 이 시스템 = 규율을 코드로 강제.

### 업계 레퍼런스 결론
- 백테스트 95%가 실전 실패. 무작위 전략도 운으로 Sharpe 2.3 → 노이즈를 알파로 착각.
- 최적 시스템 = 똑똑한 전략이 아니라 가짜 엣지를 빨리 거르는 검증 파이프라인.
- 프레임워크: 리서치=VectorBT/pandas, 실매매=Backtrader, 성과=quantstats.

## 2026-06-15: 서버 배포 완료 + 시스템 작동 검증 ✅

### 배포 환경 (확정)
- 서버: bastion-dc1 (200.200.200.7), aarch64 Ubuntu 6.8
- 경로: /data/claude-code/stock-trading (git clone)
- venv 패키지: numpy pandas scipy statsmodels python-kis typing_extensions
- 배포 방식: PC에서 git push → 서버에서 git pull

### 첫 실행 검증 — 전 파이프라인 정상 작동
- 출력: [KIS] 연결 완료 — 모의투자 | 계좌 50193225-01 / [상태] 신호=+0 | 현재가=322,500 | 보유=0주 | 현금=10,000,000 / [대기] 조건 미충족 / ✅ 오늘 실행 완료
- KIS 모의투자 연결 OK / 시세조회 OK(삼성 322,500) / 잔고조회 OK(모의 1천만)
- 신호계산 OK / 슬랙알림 OK / 하루1회 가드 OK

### 해결한 이슈
1. typing_extensions 누락 → 별도 설치 (python-kis 의존성 누락분). setup.sh에 추가 필요.
2. "auth에는 실전도메인 인증 정보를 입력해야 합니다" → python-kis는 모의투자라도 실전 앱키 필수(시세용). kis_broker.py를 실전+모의 동시 인증(virtual_appkey) 구조로 수정. secret_config는 실전4+모의2 키로 분리.
3. 계좌번호 형식 50193225-01 (뒤 -01 필수).

### 알려진 경고 (무시 가능)
- "API 호출 횟수를 초과하였습니다" — 모의계좌 호출 제한이 빡빡해 일봉 차트 조회 시 발생. python-kis가 자동 대기·재시도로 복구하므로 작동엔 지장 없음. 개선하려면 차트 조회 캐싱/호출 절감.

## 다음 단계 (갱신)
1. [완료] 모의투자 시스템 작동 검증
2. 평일 장중 수동 실행 며칠 관찰 → 이상 없으면 systemd timer 등록 (평일 16시)
3. ★ v2.1 실데이터(pykrx) 백테스트 → IS/OOS 엣지 판정 (제일 중요, 미실행)
4. 엣지 있으면 소액 실전 / 없으면 VectorBT walk-forward 재검증
5. v3 ML 보류

## 실행 방법
- python trading_v2_1.py            # 실데이터 IS/OOS
- python trading_v2_1.py --compare  # 룩어헤드 전/후 비교
- python trading_v2_1.py --synth    # 합성데이터(네트워크 불필요)
- python live_runner.py             # 모의투자 봇 (하루 1회)

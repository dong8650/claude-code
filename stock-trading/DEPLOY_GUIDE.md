# 🚀 bastion-dc1 (200.200.200.7) 모의투자 자동매매 배포 가이드

## 0. 사전 확인 (서버에서 먼저 실행)
```bash
uname -m          # 아키텍처 (aarch64=RPi64, armv7l=RPi32, x86_64=일반)
python3 --version # 3.11+ 권장 (python-kis가 3.11 기준)
cat /etc/os-release | head -2
```
→ 이 결과를 알려주면 환경에 맞게 스크립트 조정 가능

---

## 1. 환경 구성
```bash
# setup.sh 를 서버에 올린 뒤
chmod +x setup.sh
./setup.sh
```

## 2. 코드 배치
```bash
cd ~/trading-bot
source venv/bin/activate
# trading_v2_1.py, kis_broker.py, live_runner.py 복사
# secret_config.template.py → secret_config.py 로 복사 후 모의투자 키 입력
cp secret_config.template.py secret_config.py
nano secret_config.py    # 키 4개 입력 (app_key, app_secret, hts_id, account)
chmod 600 secret_config.py   # 키 파일 권한 잠금 (본인만 읽기)
```

## 3. 첫 실행 (반드시 수동)
```bash
cd ~/trading-bot && source venv/bin/activate
python live_runner.py
```
→ 연결 성공 / 신호 출력 / 주문(또는 대기) 정상인지 눈으로 확인.
→ 에러 나면 메시지 그대로 기록 (python-kis 버전별 메서드명 차이 가능)

---

## 4-A. systemd 자동 실행 (권장 — 로그·재시작 관리 우수)

### `/etc/systemd/system/trading-bot.service`
```ini
[Unit]
Description=Mock Trading Bot (daily signal check)
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
User=YOUR_USER
WorkingDirectory=/home/YOUR_USER/trading-bot
ExecStart=/home/YOUR_USER/trading-bot/venv/bin/python live_runner.py
StandardOutput=append:/home/YOUR_USER/trading-bot/run.log
StandardError=append:/home/YOUR_USER/trading-bot/run.log
```

### `/etc/systemd/system/trading-bot.timer`
```ini
[Unit]
Description=Run trading bot at 16:00 on weekdays

[Timer]
# 평일 16:00 (장 마감 후). 한국 시간 기준 — 서버 TZ 확인 필수
OnCalendar=Mon..Fri 16:00
Persistent=true

[Install]
WantedBy=timers.target
```

### 등록
```bash
# 서버 타임존이 KST 인지 먼저 확인
timedatectl    # Time zone 이 Asia/Seoul 이어야 함. 아니면:
sudo timedatectl set-timezone Asia/Seoul

sudo systemctl daemon-reload
sudo systemctl enable --now trading-bot.timer
systemctl list-timers trading-bot.timer   # 다음 실행 시각 확인
```

### 로그 확인
```bash
tail -f ~/trading-bot/run.log              # 실행 로그
journalctl -u trading-bot.service -n 50    # systemd 로그
cat ~/trading-bot/trade_log_live.csv       # 거래 기록
```

---

## 4-B. crontab (간단하게 가려면)
```bash
crontab -e
# 아래 한 줄 추가 (평일 16:00, KST)
0 16 * * 1-5 cd ~/trading-bot && ./venv/bin/python live_runner.py >> run.log 2>&1
```

---

## 5. 운영 체크리스트
- [ ] 서버 타임존 = Asia/Seoul (`timedatectl`)
- [ ] secret_config.py 권한 600 (본인만)
- [ ] virtual=True 확인 (모의투자!)
- [ ] 첫 주는 매일 run.log·trade_log_live.csv 눈으로 확인
- [ ] FortiGate 방화벽: 200.200.200.7 → 한투 API 도메인(openapi.koreainvestment.com) 아웃바운드 443 허용 확인
- [ ] 모의계좌 잔고가 의도대로 움직이는지 (10만원 세팅)

## 6. 중단 방법
```bash
sudo systemctl stop trading-bot.timer     # 타이머 중지
sudo systemctl disable trading-bot.timer  # 자동시작 해제
# 또는 crontab -e 에서 해당 줄 삭제
```

---

## ⚠️ 주의 (네트워크/보안 — bastion 호스트 특성상)
- bastion-dc1 은 외부 접점 서버다. 자동매매 봇을 여기 두면 한투 API 아웃바운드가 열려야 한다.
  보안상 신경 쓰이면 별도 내부 호스트(예: zbx-proxy-dc1)에 두는 것도 고려.
- API 키는 secret_config.py 에만. run.log·csv 에 키가 안 찍히는지 첫 실행 후 grep 확인:
  `grep -i "appkey\|secret" run.log`  (아무것도 안 나와야 정상)
- 호출 제한(2026.03~ 초당 제한) — 하루 1회 일봉 전략이라 무관하지만, 디버깅 중 반복 실행 주의.

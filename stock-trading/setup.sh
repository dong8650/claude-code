#!/usr/bin/env bash
# ════════════════════════════════════════════════════════════
# setup.sh — 모의투자 자동매매 환경 (bastion-dc1 / 200.200.200.7)
# 대상: Raspberry Pi aarch64 + Ubuntu (커널 6.8 확인됨)
# 사용: chmod +x setup.sh && ./setup.sh
# ════════════════════════════════════════════════════════════
set -e

PROJECT_DIR="$HOME/trading-bot"

echo "════════════════════════════════════════"
echo " 모의투자 자동매매 환경 구성 (aarch64/RPi)"
echo " 위치: $PROJECT_DIR"
echo " 아키텍처: $(uname -m)"
echo " 파이썬: $(python3 --version 2>&1)"
echo "════════════════════════════════════════"

# 1. 시스템 패키지 (aarch64는 numpy/pandas/scipy 휠 있어 컴파일 불필요)
echo "[1/5] 시스템 패키지..."
apt-get update -qq
apt-get install -y python3-venv python3-pip python3-dev \
                   libxml2-dev libxslt1-dev tzdata 2>/dev/null || echo "  (일부 스킵)"

# 2. 타임존 KST 강제 (16시 트리거 정확성)
echo "[2/5] 타임존 확인..."
CUR_TZ=$(cat /etc/timezone 2>/dev/null || echo "unknown")
if [ "$CUR_TZ" != "Asia/Seoul" ]; then
    echo "  현재 TZ=$CUR_TZ -> Asia/Seoul 로 변경"
    timedatectl set-timezone Asia/Seoul || ln -sf /usr/share/zoneinfo/Asia/Seoul /etc/localtime
else
    echo "  [OK] 이미 Asia/Seoul"
fi

# 3. 프로젝트 폴더 + venv
echo "[3/5] 프로젝트 폴더 & 가상환경..."
mkdir -p "$PROJECT_DIR"
cd "$PROJECT_DIR"
python3 -m venv venv
source venv/bin/activate

# 4. 파이썬 패키지 (aarch64 휠)
echo "[4/5] 파이썬 패키지 설치..."
pip install --upgrade pip wheel
pip install numpy pandas
pip install scipy statsmodels
pip install python-kis
echo "  설치된 핵심 패키지:"
pip list 2>/dev/null | grep -iE "numpy|pandas|scipy|statsmodels|python-kis"

# 5. .gitignore
echo "[5/5] .gitignore..."
cat > "$PROJECT_DIR/.gitignore" <<'EOF'
secret_config.py
.last_run_date
*.csv
*.log
venv/
__pycache__/
EOF

echo ""
echo "[완료] aarch64 환경 구성 완료!"
echo "────────────────────────────────────────"
echo "다음 단계:"
echo "  1. 코드 4개 파일을 $PROJECT_DIR 에 복사"
echo "  2. cp secret_config.template.py secret_config.py && chmod 600 secret_config.py"
echo "  3. nano secret_config.py  (모의투자 키 4개 입력)"
echo "  4. source venv/bin/activate && python live_runner.py  (첫 실행 수동)"
echo "  5. 정상이면 DEPLOY_GUIDE.md 의 systemd timer 등록"
echo "────────────────────────────────────────"

# 성운궤도 (Nebular Orbit) — Claude 컨텍스트

> 이 파일을 읽으면 이전 대화 없이도 즉시 프로젝트 작업 가능.
> 업데이트 후 반드시 git push.

---

## 프로젝트 개요

| 항목 | 내용 |
|------|------|
| 게임명 | 성운궤도 (Nebular Orbit) |
| 내부 코드명 | STARWEAVE |
| 패키지 | com.kdclab.starweave |
| 개발자 | 김동천 · KDC Lab |
| 플랫폼 | Android TWA + 웹 (kdclab.kr) |
| 장르 | 수학 별 연결 퍼즐 |
| GitHub | github.com/dong8650/kdc-games |

---

## 경로 구조

```
로컬 (맥북)
~/ai-works/apps/code/dev/          ← 웹 소스 루트 (git repo)
  games/starweave/Starweave.html   ← 메인 게임 파일 (~14,000줄)
  index.html                       ← 게임존 랜딩 페이지
  privacy.html / terms.html        ← 법적 문서
  ads.txt                          ← AdSense 인증 (서버에만 존재, git 미포함)
  deploy.sh                        ← 이중 배포 스크립트

~/starweave-apk/                   ← TWA Android 빌드 디렉토리
  twa-manifest.json
  android.keystore                 ← 서명 키 (alias: starweave)
  app-release-bundle.aab           ← 빌드 결과물

~/Downloads/Starweave.html         ← deploy.sh가 이 파일을 먼저 복사함
                                      → 게임 수정 시 이 파일을 수정하거나
                                         deploy 후 직접 반영할 것
```

---

## 서버 정보

| 역할 | IP | 접속 | 웹루트 |
|------|-----|------|--------|
| Active | 200.200.200.7 | ssh root@200.200.200.7 | /data/app/ |
| Standby | 7.7.7.7 | ssh root@7.7.7.7 | /data/app/ |

- 도메인: kdclab.kr (HTTPS)
- 두 서버 모두 /data/app에서 git pull로 동기화

---

## 배포 워크플로우

```bash
# 표준 배포 (웹 파일 변경 시)
cd ~/ai-works/apps/code/dev
./deploy.sh "커밋 메시지"
```

**deploy.sh 동작 순서:**
1. ~/Downloads/Starweave.html 존재 시 games/starweave/에 복사
2. git add . && git commit && git push
3. Active 서버 SSH → git pull
4. Standby 서버 SSH → git pull
5. MD5 해시 동기화 검증
6. 헬스체크 + 외부 접속 테스트

**주의:** deploy.sh가 ~/Downloads/Starweave.html을 먼저 덮어씀.
게임 파일 수정 시 Downloads 파일도 같이 수정하거나, 배포 후 적용할 것.

---

## TWA 빌드 프로세스

```bash
cd ~/starweave-apk

# 1. manifest 변경사항 프로젝트에 반영 (버전명 입력 필요 - 터미널에서 직접 실행)
bubblewrap update

# 2. update 후 반드시 수동으로 아래 두 파일 변경사항 재적용
#    (bubblewrap update가 파일을 재생성하므로 덮어씌워짐)

# 3. AAB 빌드 (키스토어 비밀번호 입력 필요 - 터미널에서 직접 실행)
bubblewrap build
# → app-release-bundle.aab 생성
```

### bubblewrap이 재생성해도 유지해야 할 수동 변경사항

**LauncherActivity.java** (`app/src/main/java/com/kdclab/starweave/`):
```java
import android.content.Intent;  // 추가

// onNewIntent 메서드 추가 (getLaunchingUrl 위에)
@Override
protected void onNewIntent(Intent intent) {
    super.onNewIntent(intent);
    Uri data = intent.getData();
    if (data != null && "starweave".equals(data.getScheme()) && "close".equals(data.getHost())) {
        finishAndRemoveTask();
    }
}
```

**AndroidManifest.xml** (`app/src/main/`):
```xml
<!-- LauncherActivity 태그에 추가 -->
android:launchMode="singleTop"

<!-- intent-filter 추가 (MAIN launcher 위에) -->
<intent-filter>
    <action android:name="android.intent.action.VIEW" />
    <category android:name="android.intent.category.DEFAULT" />
    <category android:name="android.intent.category.BROWSABLE" />
    <data android:scheme="starweave" android:host="close" />
</intent-filter>
```

### Play Console 업로드
1. play.google.com/console → 성운궤도
2. 테스트 및 출시 → 비공개 테스트 → 새 버전 만들기
3. app-release-bundle.aab 업로드

---

## 버전 현황

| 구분 | 버전 | 비고 |
|------|------|------|
| 웹 (kdclab.kr) | 최신 배포 상태 | deploy.sh로 관리 (이동 횟수 버전 배포됨) |
| Android APK | 1.0.31 (versionCode 34) | 2026-05-04 빌드 — **단, 이 빌드는 타이머 기준** |
| Play Store 프로덕션 | **출시 완료** | 직접 링크 접속 가능, 검색 색인 반영 중 |

---

## Play Store 프로덕션 현황

- ✅ **2026-05-04 프로덕션 출시 완료** (100% 롤아웃)
- ✅ 직접 링크 접속 확인: play.google.com/store/apps/details?id=com.kdclab.starweave
- ✅ IARC Live Rating Notice 수신 (자동 알림, 별도 조치 불필요)
- 검색 노출: 색인 반영까지 수일 소요 예상

### 이전 신청 리젝 사유 (참고)
1. 테스터가 실제로 참여하지 않음
2. 피드백을 반영한 업데이트가 없음

---

## IAP 상품 (Google Play Console)

| 상품명 | 제품 ID | 가격 |
|--------|---------|------|
| VIP 패스 | vip_pass | — |
| 광고 제거 | no_ads | — |
| 힌트팩 50개 (17% 할인) | hints_50 | ₩3,900 |
| 힌트팩 10개 | hints_10 | ₩990 |
| 이동팩 15회 | moves_15 | ₩1,200 ✅ 등록 완료 (2026-05-17) |

- 별힌트 3개 → 이동 +5회 교환 겸용 (이동 횟수 전환 후 적용)

---

## 수익 모델 및 수수료 구조

### 플랫폼별 수수료

| 플랫폼 | 수수료 | 예시 (₩9,900 VIP) |
|--------|--------|-------------------|
| Google Play IAP | 구글 15% | 개발자 ₩8,415 (85%) |
| 앱인토스 IAP | 구글/애플 15% + 토스 5% = **20%** | 개발자 ₩7,920 (80%) |
| Web PG (카드결제) | PG사 2~3% | 개발자 ₩9,600~9,700 (97~98%) |
| AdSense / Toss Ads | 플랫폼별 상이 | — |

> 구글/애플이 앱인토스에 기여가 없음에도 15% 수수료를 가져가는 구조 (불가피, 스토어 수수료 정책).  
> Web PG가 수수료 가장 낮지만 접근성이 낮아 현실적으로 IAP가 주력.

### 수익 목표
- **성운궤도 월 목표**: 200~300만원
- **전략**: 앱인토스 심사 통과 후 유입 확인 → 난이도 조정 → 결제 전환율 측정
- 현재 구글 플레이 결제 0건 → 난이도가 너무 쉬워 결제 필요성이 없는 수준으로 판단

### 수익 채널
1. **AdSense** (웹 광고) — AdSense 승인 대기 중
2. **Google Play IAP** — 앱 설치 유저
3. **앱인토스 IAP** — 토스 앱 유저 (심사 통과 후)
4. **Toss Ads (보상형)** — 광고 시청 보상

---

## 게임 고도화 핵심 방향

> 상세: `context/game_direction.md`

### ✅ 타이머 → 이동 횟수 제한 전환 (웹 완료, APK 미반영)
- **이유**: 타이머는 스트레스, 이동 횟수는 "아깝다" 감정 → IAP 전환율 높음
- **동작**: 성공 연결(합=타겟)만 횟수 차감, 실패는 무료
- **웹 배포**: 2026-05-04 commit 9f2efc6 배포 완료
- **APK**: 아직 미반영 — 다음 빌드 시 포함 필요
- **신규 IAP**: moves_15 (₩1,200) 등록 필요

#### 이동 횟수 전환 주요 변경 내용
| 항목 | 변경 전 | 변경 후 |
|------|---------|---------|
| DESTINATIONS 필드 | `timeLimit:90` | `moveLimit:20` (행성별 차등) |
| G 상태 | `timeLeft`, `timeExtendUsed` | `movesLeft`, `movesExtendUsed` |
| UI 라벨 | `TIME` | `MOVE` |
| `setInterval` 타이머 | 있음 | 완전 제거 |
| `_onTimerEnd` | 시간 종료 처리 | `_onMovesEnd` alias |
| 광고 보상 | `timeLeft += 30` | `movesLeft += 3` |
| 이동팩 아이템 | `timeLeft += 15` | `movesLeft += 2` |

#### 행성별 moveLimit
지구/달:20 → 수성/금성/화성:18 → 목성/토성:16 → 천왕성/해왕성:15 → 은하계:14 → 우주:13

### 남은 작업
- **와일드카드 타이머 제거**: 와일드카드 UI에 남아있는 시간 표시 제거 필요
- **APK 빌드**: 이동 횟수 전환 + 와일드카드 타이머 제거 후 bubblewrap build → Play Console 업로드

### 상점 2컬럼 레이아웃
- 왼쪽: 이동 횟수 (이동+5회, 이동팩15회)
- 오른쪽: 별힌트 (10개, 50개)
- 하단: 광고 무료충전 → VIP 패스 (풀와이드) → 게임오버 광고 제거
- 시안: `/Users/mins/Downloads/shop_mockup.html`

### 게임오버 팝업 3선택지
1. 별힌트×3 → +5회
2. ₩1,200 IAP → +15회
3. 광고 시청 → +3회 무료

---

## AdSense 현황

| 항목 | 내용 |
|------|------|
| Publisher ID | pub-9880579204573301 |
| ads.txt | /data/app/ads.txt (서버에만 존재) |
| 상태 | 재검토 요청 완료 (2026-05-10) |
| 거절 사유 | 가치가 별로 없는 콘텐츠 |
| 조치 | sitemap.xml·robots.txt 추가, 가이드 3편 신규 작성, 게임 랜딩 페이지(2000+자) 생성, 아동 타겟 표현 제거, 게임명 성운궤도 통일 |
| 예상 결과 | 1~4주 내 dong8650@gmail.com 통보 |

---

## 앱인토스 현황

| 항목 | 내용 |
|------|------|
| 플랫폼 | 토스 앱 내 WebView 미니앱 (APK 스토어 아님) |
| 콘솔 | apps-in-toss.toss.im |
| 앱 이름 | 성운궤도 |
| appName | nebular-orbit (변경 불가) |
| 앱 유형 | 게임 |
| 상태 | **게임 심사 중** (2~4주 소요, 2026-05-23 검토 요청 완료) |
| 광고 | Toss Ads 연동 완료 (현재 테스트 ID 사용, 실제 adGroupId 교체 필요) |
| 인앱결제 | 앱인토스 IAP SDK 연동 완료 (정산 검토 완료 후 상품 등록 필요) |
| 일회성 제품 | 앱인토스 콘솔에 vip_pass, no_ads, hints_50, hints_10 별도 등록 필요 |
| 검수 기간 | 게임 2~4주 |
| 번들 버전 | 20260522-1 (SDK 2.6.0) |
| 프로젝트 경로 | ~/ai-works/apps/code/dev/nebular-orbit/ |

### 앱인토스 프로젝트 구조

```
~/ai-works/apps/code/dev/nebular-orbit/
  index.html          ← Starweave.html 복사본 (게임 메인)
  Starweave.html      ← 원본 참조용
  granite.config.ts   ← appName: nebular-orbit, brand 설정
  src/toss-bridge.ts  ← Toss SDK를 window.__tossSDK__로 노출
  nebular-orbit.ait   ← 빌드 결과물 (콘솔에 업로드)
```

### 앱인토스 빌드/배포 워크플로우

```bash
cd ~/ai-works/apps/code/dev/nebular-orbit

# 게임 파일 업데이트 (원본 변경 시)
cp ../games/starweave/Starweave.html ./index.html
# → index.html에 수동으로 두 가지 재적용:
#   1. <script type="module" src="/src/toss-bridge.ts"></script> (head에 추가)
#   2. _detectPlatform()에 toss_miniapp 분기 (첫 줄에 추가)

# 빌드
npm run build
# → nebular-orbit.ait 생성

# 콘솔 업로드
npx ait deploy  # 또는 콘솔에서 수동 업로드
```

### _detectPlatform() toss_miniapp 분기

```javascript
function _detectPlatform() {
  if (window.__tossSDK__) return 'toss_miniapp';  // ← 추가된 부분
  if (_isTWA()) return 'android_app';
  // ...
}
```

---

## 게임 아키텍처

### 플랫폼 감지 (_detectPlatform)
```
android_app  → TWA/Play Billing (document.referrer 또는 getDigitalGoodsService)
ios          → 결제 모달 표시
android_web  → Play Store 리다이렉트
desktop      → QR 코드 표시
toss_miniapp → (추가 예정) 앱인토스 IAP SDK + Toss Ads
```

### localStorage 키
| 키 | 용도 |
|----|------|
| sw_vip | VIP 상태 |
| sw_no_ads | 광고 제거 여부 |
| slv4_cleared | 4레벨 클리어 |
| sw_planet1_cleared | 첫 행성 클리어 |
| sw_planets_cleared_count | 클리어한 행성 수 |
| sw_ad_clear_count | 광고 시청 횟수 |

### 행성 순서 (11단계)
지구 → 달 → 수성 → 금성 → 화성 → 목성 → 토성 → 천왕성 → 해왕성 → 은하계 → 우주

### 게임 모드
- **우주탐험**: 메인 퍼즐 (별 드래그 연결, 목표값 달성)
- **크로스매스**: 보조 모드 (첫 행성 클리어 후 해금)

---

## 인프라 / 도메인

- kdclab.kr → Active 서버 (200.200.200.7)
- Google Search Console: 소유권 확인 완료 (2026-05-01)
- Search Console 인증 파일: googlec5dc85ee5de230fa.html

### 네트워크 구조

```
인터넷 사용자
      │ HTTPS (443)
      ├─────────────────────────────────────────┐
      ▼                                         ▼
[DC1 Fortigate tl-fw-dc1 — 218.38.161.182]   [DC2 Fortigate tl-fw-dc2 — 175.119.14.194]
 SSL Offloading: Client <-> FortiGate (Full)   SSL Offloading: Client <-> FortiGate (Full)
 인증서: kdclab-cert (만료 2026-06-29)          인증서: kdclab-cert (동일)
 Load Balancing: First Alive                   Load Balancing: First Alive
 Health Check: hc_kdclab_http                  Health Check: hc_kdclab_http (src-ip 172.26.20.77)
      │                                              │ VPN 터널 (tl_fw_m_vpn)
      │ HTTP (80)                                    │ DC2 내부 IP: 172.26.20.77
      ├──────────────┐                               │ DC1 VPN 측 첫 홉: 192.168.0.77
      ▼              ▼                          ┌────┴──────────────────┐
[200.200.200.7:80] [7.7.7.7:80]               ▼                       ▼
 Active (nginx)    Standby (nginx)       [200.200.200.7:80]       [7.7.7.7:80]
 certbot 자동갱신   certbot 없음           Active (Primary)         Standby (Backup)
                                          status=UP ✅              status=DOWN (비활성)
```

**DC2 Virtual Server (`vs_kdclab_https`):**
- VIP: `175.119.14.194:443` → 백엔드: `200.200.200.7:80` (Primary) / `7.7.7.7:80` (Backup)
- 헬스체크: `hc_kdclab_http` — HTTP GET /health, src-ip 172.26.20.77 필수 (VPN Phase2 selector 조건)
- 방화벽 정책 #29: srcintf=any → dstintf=tl_fw_m_vpn, dst=200.200.200.0/24, nat=enable

**⚠️ 미해결 이슈: DC2 VIP → DC1 백엔드 실제 트래픽 포워딩 불가**
- 헬스체크는 정상 (src-ip 172.26.20.77 강제) → `200.200.200.7 status=UP` ✅
- 실제 클라이언트 트래픽 포워딩은 미동작 — policy #29 hit count=0
- **추정 원인**: VIP 백엔드 연결의 source IP가 172.26.20.0/24 밖 → VPN Phase2 selector 불일치 → 터널 진입 불가
- **진단**: `nc -zv 175.119.14.194 443` 은 SSL 핸드셰이크를 안 하므로 백엔드 연결 생성 안 됨 → `curl -k https://175.119.14.194/` 로 테스트해야 함
- **Fix 방안**: policy #29에 IP Pool(172.26.20.77 SNAT) 추가 또는 VIP 백엔드 src-ip 강제 설정

> SSL 종료는 Fortigate에서 처리. 서버의 certbot 갱신 후 **Fortigate 인증서를 수동 교체**해야 함.

### SSL 인증서 관리

| 항목 | 내용 |
|------|------|
| Fortigate 인증서명 | `kdclab-cert` (현재), 이후 `kdclab-cert_YYYYMMDD` 날짜 명명 방식 사용 |
| 현재 만료일 | **2026-06-29** |
| 발급 기관 | Let's Encrypt (E7) |
| 서버 certbot 갱신 시점 | 만료 30일 전 → 약 **5월 30일 전후** 자동 갱신 |
| Fortigate 교체 시점 | certbot 갱신 후 → **6월 초** 수동 교체 필요 |

### Fortigate 인증서 교체 절차 (날짜 이름 방식)

```bash
# Step 1 — 맥북에서 서버 인증서 다운로드
scp root@200.200.200.7:/etc/letsencrypt/live/kdclab.kr/fullchain.pem ~/Downloads/kdclab_fullchain.pem
scp root@200.200.200.7:/etc/letsencrypt/live/kdclab.kr/privkey.pem ~/Downloads/kdclab_privkey.pem
```

```
# Step 2 — Fortigate 업로드
System → Certificates → Create/Import → Certificate
  Type: Certificate (PKCS#12 아님)
  Certificate file: kdclab_fullchain.pem
  Key file: kdclab_privkey.pem
  Password: 비워둠
  이름: kdclab-cert_20260930 (실제 만료일로)

# Step 3 — Virtual Server 교체 (무중단)
Policy & Objects → Virtual Servers → vs_kdclab_https → Edit
  SSL Offloading → Certificate → kdclab-cert_20260930

# Step 4 — 교체 확인
echo | openssl s_client -connect kdclab.kr:443 2>/dev/null | openssl x509 -noout -enddate

# Step 5 — 기존 인증서 삭제
System → Certificates → kdclab-cert_20260629 → Delete
```

> ⚠️ PFX 방식은 과거 실패 경험 있음. 반드시 **Certificate 타입(PEM 분리)** 으로 올릴 것.

---

## 작업 규칙

1. **게임 파일 수정 시** ~/Downloads/Starweave.html 수정 → deploy.sh 실행
2. **네이티브 변경 시** bubblewrap update → 수동 변경 재적용 → bubblewrap build → Play Console 업로드
3. **서버 pull 충돌 시** `git checkout -- 파일명` 후 다시 pull
4. **versionCode**는 항상 이전보다 높게 (현재 32)

---

## 컨텍스트 문서

| 파일 | 내용 |
|------|------|
| `context/tester_feedback.md` | 테스터 피드백 6건 + 우선순위 |
| `context/game_direction.md` | 타이머→이동 횟수 전환 설계, IAP, 상점, 성운 유니버스 로드맵 |

---

## 로드맵

### 성운궤도 Phase별 계획
- **Phase 1 (현재)**: 프로덕션 승인 대기
- **Phase 2 (승인 직후)**: 타이머→이동 횟수 전환, 상점 UI 개선, moves_15 IAP 등록
- **Phase 3 (v1.1)**: 테스터 피드백 반영 (크로스매스 기호, 행성 이동 힌트, 팝업 개선)

### 성운 유니버스 확장 순서
```
빠른 승리: 성운 커넥션 (5일) — 데일리 퍼즐, 바이럴 공유
메인 승부: 성운 수이카 (2주) — 물리 드롭&합성, 바이럴 최강
장기 투자: 성운 서바이버 (4주) — 리텐션 최강
```

---

## 현재 진행 상황

### 2026-05-01 완료 작업

| 작업 | 결과 |
|------|------|
| AdSense "가치 없는 콘텐츠" 원인 분석 | JS 렌더링만 → HTML 크롤 불가 → index.html 실제 HTML 콘텐츠 추가 |
| index.html 개선 | 게임 5개 article 추가, 성운궤도 브랜드 통일, 메타태그, footer (privacy/terms 링크) |
| Google Search Console 등록 | kdclab.kr URL 접두어 방식, 소유권 확인 완료, 색인 생성 요청 완료 |
| AdSense 재검토 신청 | 검토 요청 완료 (결과: 1~4주 내 dong8650@gmail.com) |
| 뒤로가기 종료 버그 수정 | doExit() → intent:// URI 브릿지로 네이티브 종료 |
| TWA native 수정 | LauncherActivity.java onNewIntent 추가, AndroidManifest.xml singleTop + intent-filter 추가 |
| v1.0.30 빌드 및 업로드 | bubblewrap build → app-release-bundle.aab → Play Console 비공개 테스트 업로드 |
| claude-code 레포 구성 | github.com/dong8650/claude-code 생성, 프로젝트별 CLAUDE.md 작성 |

### 2026-05-03 완료 작업

| 작업 | 결과 |
|------|------|
| 프로덕션 신청 | Play Console 신청 완료 |
| 테스터 피드백 #6 수집 | 게임 중 팝업 흐름 방해 → tester_feedback.md 반영 |
| IAP 4종 확인 | vip_pass, no_ads, hints_50, hints_10 Google Play 등록 확인 |
| 타이머 → 이동 횟수 전환 설계 | 분석 완료 |
| 상점 2컬럼 레이아웃 시안 | shop_mockup.html 제작 완료 |
| 게임오버 팝업 3선택지 설계 | 힌트/IAP/광고 3중 수익 구조 확정 |
| context 문서 작성 | tester_feedback.md, game_direction.md 생성 및 git push |
| 성운 유니버스 로드맵 확정 | 5개 게임 라인업 + 신규 게임 TOP5 분석 |

### 2026-05-04 완료 작업

| 작업 | 결과 |
|------|------|
| Play Store 프로덕션 출시 | v1.0.31 (versionCode 34), 100% 롤아웃 완료 |
| versionCode 충돌 해결 | 32 이미 사용됨 → 33으로 수정, bubblewrap이 34로 자동 증가 |
| IARC 등급 알림 수신 | 자동 알림, 별도 조치 불필요 |
| 타이머 → 이동 횟수 전환 코드 작업 | Starweave.html 전면 수정 완료 |
| 웹 배포 | deploy.sh "feat: 타이머 → 이동 횟수 제한 전환 (v1.0.31)" — commit 9f2efc6 |

### 2026-05-05 완료 작업

| 작업 | 결과 |
|------|------|
| 피드백 #5 — 크로스매스 연산자 가시성 | `.cm-op` 폰트 130%→140%, 배경+테두리+글로우 추가 |
| 피드백 #6 — Plan B 이벤트 큐 결과화면 통합 | 인터미션에 `#interEventSection` 추가, `_renderPendingEvents()` 구현 |
| 피드백 #6 — 연속출석/미션 달성 팝업 제거 | `showStreakPopup()`, 미션 달성 → `_pendingGameEvents` 큐로 변경 |
| 우주인 캐릭터 제거 | `#charWrap` `display:none` |
| 와일드카드 3초 타이머 제거 | `_startWildLink()` 카운트다운 완전 제거 |
| 상점 2컬럼 레이아웃 완료 | 이동횟수/별힌트 2컬럼, 광고충전, VIP카드 |
| 게임 중 팝업 전면 제거 1차 | bonusPop, boostPop, showComboPop, showResultPop, wildcardToast 제거 |
| 게임 중 팝업 전면 제거 2차 | itemToast(applyItem), scoreBonusBanner, conquestBanner, dualBonusToast 제거 |
| 게임 중 팝업 전면 제거 3차 | 힌트없음/결과, 로켓/블랙홀/미니폭발, 와일드관련, 미션진행 toast 11종 제거 |
| Standby 서버 IP 변경 | 7.7.7.253 → 7.7.7.7, deploy.sh 반영 완료 |
| Play Store ko-KR 주소 노출 제거 | 개인 주소 포함 구버전 한국어 설명 → 새 내용으로 교체 제출 완료 |

### 2026-05-17 완료 작업

| 작업 | 결과 |
|------|------|
| 보상형 광고 우회 버그 수정 | `_openRewardedAdModal()` 공통 함수 추가 — adsbygoogle 슬롯 재생성, 15초 카운트다운 후 버튼 활성화, skipRewardedAd() 타이머 정리. 힌트충전/이어하기/별힌트 3곳 적용. commit b7beef1 |
| 게임 랜딩 페이지 오류 수정 | /games/starweave/index.html — 존재하지 않는 EASY/HARD 모드 제거, 실제 존재하는 우주탐험/크로스매스 모드로 교체. commit a4f4d54 |
| 앱인토스 앱 생성 | 앱 이름: 성운궤도, appName: nebular-orbit, 유형: 게임. 생성 완료. |
| 앱인토스 구조 파악 | APK 스토어 아님. WebView 미니앱. 광고/IAP 별도 SDK. HTML 1개로 플랫폼 분기 관리 가능. |
| 앱인토스 기본 정보 입력 | 부제: 별 연결로 우주를 정복하라, 카테고리: 게임>퍼즐, 키워드 7개, 로고/썸네일 업로드, 고객문의: dong8650@gmail.com |
| 앱인토스 게임 등급분류 입력 | GRAC 자체등급분류 방식. 등급분류번호: GOOG-SG-260504-0447, 날짜: 2026-05-04. 게임 주요화면 4장 PNG 업로드 완료. |
| 앱인토스 검토 요청 완료 | 모든 항목 입력 후 검토 요청 제출. 영업일 기준 2일 내 dong8650@gmail.com으로 결과 통보 예정. |
| SSL 인증서 구조 파악 | Fortigate(tl-fw-dc1)에서 SSL 종료. kdclab-cert(만료 2026-06-29) 사용 중. 서버 certbot 자동갱신 정상, Fortigate는 수동 교체 필요. |
| Fortigate 인증서 교체 절차 정립 | PEM 분리 방식(Certificate 타입), 날짜 이름 방식(kdclab-cert_YYYYMMDD)으로 무중단 교체. PFX 방식은 과거 실패 경험으로 사용 금지. CLAUDE.md에 절차 문서화. |
| DR 서버 인증서 자동 동기화 구축 | Active→DR SSH 키 인증 설정. `/etc/letsencrypt/renewal-hooks/deploy/sync-to-dr.sh` 설치. certbot 갱신 후 rsync로 7.7.7.7에 자동 동기화. 로그: `/var/log/certbot-sync-dr.log` |
| Fortigate HTTP 80 포트 오픈 | certbot HTTP-01 챌린지용. vs_kdclab_http 추가 (218.38.161.182:80 → 200.200.200.7:80, 7.7.7.7:80). certbot dry-run 성공 확인. |
| moves_15 IAP 추가 | Play Console 일회성 제품 등록 (moves_15, ₩1,200, 대한민국, 활성). 게임 코드 PLAY_SKU_MAP + PURCHASE_ITEMS 추가 (commit 857990b). 양쪽 서버 배포 완료. AAB 재빌드 불필요 (웹 코드만 변경). |

### 2026-05-23 완료 작업

| 작업 | 결과 |
|------|------|
| 앱인토스 승인 확인 | 2026-05-17 제출 → 승인 완료 |
| Granite 프로젝트 생성 | npx create-ait-app nebular-orbit (SDK 2.6.0) |
| 게임 통합 | Starweave.html → index.html, toss-bridge.ts 생성, _detectPlatform() toss_miniapp 분기 추가 |
| v0.1.0 빌드/업로드 | nebular-orbit.ait → 콘솔 업로드 → QR 테스트 성공 |
| 게임 심사 요청 | 검토 요청 완료, 영업일 7일 내 결과 통보 |
| Toss IAP 연동 | _purchaseViaToss() 추가, purchaseItem()에 toss_miniapp 분기 |
| Toss Ads 연동 | _showTossRewardedAd() 추가, _openRewardedAdModal()에 toss_miniapp 분기 |
| v0.2.0 빌드/업로드 | IAP/광고 연동 버전 콘솔 업로드 완료 |
| 정산 정보 등록 | 매일의 설계, 김동천, 토스뱅크 → 검토 요청 완료 (약 1일 소요) |

### 다음 할 일

#### 🔴 앱인토스 (정산 승인 대기 — 화요일 이후)
- **정산 검토 완료 후 IAP 상품 5개 등록** (콘솔 → 인앱 결제 → 상품 등록):
  - `hints_10` (₩990, 소모품), `hints_50` (₩3,900, 소모품), `moves_15` (₩1,200, 소모품)
  - `no_ads` (₩2,900, 비소모품), `vip_pass` (₩9,900, 비소모품)
- **광고 그룹 등록**: 콘솔 → 인앱 광고 → 리워드/전면/배너 그룹 생성
  - 실제 adGroupId 발급 후 게임 코드 `_TOSS_REWARDED_AD_ID` 변수 교체 → 재빌드 → 콘솔 업로드
  - 현재 테스트 ID: `ait-ad-test-rewarded-id` (index.html 내 변수)
- **게임 심사 결과 대기**: 영업일 7일, dong8650@gmail.com 통보 (2026-05-23 제출)

#### 🟡 게임 난이도 및 수익화 전략
- **유저 유입 모니터링**: 앱인토스 심사 통과 후 DAU/리텐션 확인
- **난이도 조정**: 현재 구글 플레이 결제 0건 → 너무 쉬운 난이도 → 행성별 moveLimit 조정 검토
  - 목표: 결제 전환율 확보 (VIP ₩9,900 기준 월 200~300건 = 월 200~300만원)
- **APK 재빌드**: bubblewrap build → v1.0.32 (versionCode 35) — 이동 횟수 전환 + 팝업 제거 반영

#### 🟠 인프라 (언제든 가능)
- **DC2 VIP → DC1 백엔드 포워딩 Fix**:
  1. `curl -k https://175.119.14.194/` 로 실제 HTTPS 테스트 (nc 아님)
  2. DC2 Fortigate debug flow 동시 확인 (source IP 확인)
  3. policy #29에 IP Pool SNAT 추가:
     ```
     config firewall ippool → edit "snat-dc2-internal" → startip/endip 172.26.20.77
     config firewall policy → edit 29 → set ippool enable → set poolname "snat-dc2-internal"
     ```
- **nginx 443 제거**: Active 서버(200.200.200.7) nginx 443 블록 제거 + certbot webroot 방식 전환 (`authenticator=webroot, installer=None, webroot=/var/www/html`)

#### ⚪ 대기
- **AdSense**: 재검토 결과 대기 (1~4주, dong8650@gmail.com, 2026-05-10 신청)

---

## 게임 중 팝업 정책

**모든 게임 중 팝업은 완전 제거됨.** 아래만 유지:
- 진동, 파티클, 화면흔들림 (시각/촉각 피드백)
- `showScorePop` (셀 위치에 점수 표시, 0.9초)
- 와일드카드 선택 팝업 (`#wildcardChoicePopup`) — 탭 시 선택지 제공 (필수 인터랙션)
- 이동 횟수 소진 시 팝업 (`_onMovesEnd`) — 필수 게임오버 흐름
- 상점/힌트 버튼 오류는 무음 처리

---

## 마지막 업데이트

2026-05-23 — 앱인토스 승인 완료 → Granite 프로젝트(nebular-orbit) 생성 → 게임 통합(Starweave.html → index.html, toss-bridge.ts) → v0.1.0 빌드/업로드/QR 테스트 → 게임 심사 요청 → IAP/광고 연동(v0.2.0) → 정산 정보 등록(매일의 설계/김동천/토스뱅크, 검토 중). 수익 구조 분석: 앱인토스 IAP는 구글/애플 15% + 토스 5% = 20% 수수료. 월 200~300만원 목표로 유입 확인 후 난이도 조정 예정.

2026-05-17 (3차) — moves_15 IAP 추가 완료. Play Console 등록 + 게임 코드(PLAY_SKU_MAP, PURCHASE_ITEMS) 수정 + 양쪽 서버 배포. 이동 추가 +5회는 별힌트×3 소모 교환 방식(IAP 아님) 확인.

2026-05-17 (2차) — DC2 Fortigate (tl-fw-dc2, 175.119.14.194) Virtual Server 이중화 구성 작업. 헬스체크 src-ip 172.26.20.77 설정으로 DC1 백엔드 정상 확인(status=UP). VIP 실제 트래픽 포워딩은 source IP ↔ VPN Phase2 selector 불일치 문제로 미완. Fix: policy #29에 SNAT(172.26.20.77) 추가 예정. 핵심 패턴: DC2에서 DC1으로 가는 모든 트래픽(로컬 originating)은 반드시 src-ip 172.26.20.77 사용해야 VPN 터널 진입 가능.

2026-05-17 (1차) — 보상형 광고 우회 버그 수정, 랜딩 페이지 모드 오류 수정, 앱인토스 검토 요청 완료, Fortigate SSL 구조 파악·인증서 교체 절차 정립, DR 인증서 자동 동기화 구축, Fortigate 80포트 오픈 (certbot dry-run 정상). nginx 443 제거는 다음 작업으로.

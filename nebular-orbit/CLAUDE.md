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
| Standby | 7.7.7.253 | ssh root@7.7.7.253 | /data/app/ |

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
| 웹 (kdclab.kr) | 최신 배포 상태 | deploy.sh로 관리 |
| Android APK | 1.0.30 (versionCode 32) | 2026-05-01 빌드 |
| Play Store 알파 | 비공개 테스트 완료 | 테스터 12명, 피드백 6건 수집 |
| Play Store 프로덕션 | **신청 완료 (2026-05-03)** | 결과 대기 중, 약 7일 이내 |

---

## Play Store 프로덕션 신청 현황

- ✅ 비공개 테스트 버전 게시
- ✅ 12명 이상 테스터 참여
- ✅ 검토일(4/19)부터 14일 테스트 완료
- ✅ **2026-05-03 프로덕션 신청 완료**
- 결과 수신: dong8650@gmail.com (약 7일 이내)
- **주의: 승인 전까지 게임 코드 수정 금지**

### 이전 신청 리젝 사유 (참고)
1. 테스터가 실제로 참여하지 않음
2. 피드백을 반영한 업데이트가 없음

### 이번 신청 대응 방향
- 테스터 6명 피드백 수집 → tester_feedback.md에 기록
- 피드백 반영 업데이트 계획 수립 → game_direction.md에 기록

---

## IAP 상품 (Google Play Console)

| 상품명 | 제품 ID | 가격 |
|--------|---------|------|
| VIP 패스 | vip_pass | — |
| 광고 제거 | no_ads | — |
| 힌트팩 50개 (17% 할인) | hints_50 | ₩3,900 |
| 힌트팩 10개 | hints_10 | ₩990 |
| 이동팩 15회 | moves_15 | ₩1,200 (프로덕션 승인 후 등록 예정) |

- 별힌트 3개 → 이동 +5회 교환 겸용 (이동 횟수 전환 후 적용)

---

## 수익 모델 (이중 구조)
1. **AdSense** (웹 광고)
2. **Google Play IAP** (위 4종 상품)

---

## 게임 고도화 핵심 방향 (프로덕션 승인 후)

> 상세: `context/game_direction.md`

### 타이머 → 이동 횟수 제한 전환
- **이유**: 타이머는 스트레스, 이동 횟수는 "아깝다" 감정 → IAP 전환율 높음
- **동작**: 성공 연결(합=타겟)만 횟수 차감, 실패는 무료
- **구현**: ~100~150줄 변경, 반나절~하루 예상
- **신규 IAP**: moves_15 (₩1,200) 등록 필요

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
| 상태 | 재검토 요청 완료 (2026-05-01) |
| 거절 사유 | 가치가 별로 없는 콘텐츠 |
| 조치 | index.html 콘텐츠 보강, 메타태그, privacy/terms 링크 추가 |
| 예상 결과 | 1~4주 내 dong8650@gmail.com 통보 |

---

## 게임 아키텍처

### 플랫폼 감지 (_detectPlatform)
```
android_app  → TWA/Play Billing (document.referrer 또는 getDigitalGoodsService)
ios          → 결제 모달 표시
android_web  → Play Store 리다이렉트
desktop      → QR 코드 표시
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
| 프로덕션 신청 | Play Console 신청 완료, 결과 대기 중 |
| 테스터 피드백 #6 수집 | 게임 중 팝업 흐름 방해 → tester_feedback.md 반영 |
| IAP 4종 확인 | vip_pass, no_ads, hints_50, hints_10 Google Play 등록 확인 |
| 타이머 → 이동 횟수 전환 설계 | 분석 완료, 구현은 프로덕션 승인 후 |
| 상점 2컬럼 레이아웃 시안 | shop_mockup.html 제작 완료 |
| 게임오버 팝업 3선택지 설계 | 힌트/IAP/광고 3중 수익 구조 확정 |
| context 문서 작성 | tester_feedback.md, game_direction.md 생성 및 git push |
| 성운 유니버스 로드맵 확정 | 5개 게임 라인업 + 신규 게임 TOP5 분석 |

### 다음 할 일

- **프로덕션 승인 대기**: 약 7일 이내 dong8650@gmail.com 수신
- **승인 후 즉시**: 타이머 → 이동 횟수 전환 코드 작업 (반나절~하루)
- **승인 후 즉시**: moves_15 IAP 상품 Google Play Console 등록
- **AdSense**: 재검토 결과 대기 (1~4주)

---

## 마지막 업데이트

2026-05-03 — 프로덕션 신청 완료, 타이머→이동 횟수 전환 설계, IAP 구조 확인, 상점 시안, 성운 유니버스 로드맵 확정

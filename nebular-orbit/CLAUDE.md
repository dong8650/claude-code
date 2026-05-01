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
| Play Store 알파 | 비공개 테스트 중 | 테스터 12명 |
| Play Store 프로덕션 | 미승인 | 5/3 이후 재신청 예정 |

---

## Play Store 프로덕션 신청 조건

- ✅ 비공개 테스트 버전 게시
- ✅ 12명 이상 테스터 참여
- ○ 검토일(4/19)부터 14일 테스트 → **5/3 조건 충족**
- 5/3 이후 Play Console → 프로덕션 신청 버튼 활성화

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

## 로드맵 (v40)

`~/Downloads/STARWEAVE_v40_Roadmap.md` 참조.

- Phase 1 (현재): 프로덕션 승인 집중
- Phase 2 (v31~35): 행성 4개 추가, 우주정거장 시스템
- Phase 3 (v40): 심우주 확장
- Phase 4 (v50): 엔딩 시네마틱, 글로벌 랭킹

---

## 현재 진행 상황

### 2026-05-01 완료 작업

| 작업 | 결과 |
|------|------|
| AdSense "가치 없는 콘텐츠" 원인 분석 | JS 렌더링만 → HTML 크롤 불가 → index.html 실제 HTML 콘텐츠 추가 |
| index.html 개선 | 게임 5개 article 추가, 성운궤도 브랜드 통일, 메타태그, footer (privacy/terms 링크) |
| Google Search Console 등록 | kdclab.kr URL 접두어 방식, 소유권 확인 완료, 색인 생성 요청 완료 |
| AdSense 재검토 신청 | 체크박스 선택 → 검토 요청 버튼 클릭 완료 (결과: 1~4주 내 dong8650@gmail.com) |
| 뒤로가기 종료 버그 수정 | doExit() → intent:// URI 브릿지로 네이티브 종료 |
| TWA native 수정 | LauncherActivity.java onNewIntent 추가, AndroidManifest.xml singleTop + intent-filter 추가 |
| v1.0.30 빌드 및 업로드 | bubblewrap build → app-release-bundle.aab → Play Console 비공개 테스트 업로드 |
| 종료 버그 수정 확인 | "뒤로가기 → 종료 버튼 → 게임종료" 정상 동작 확인 |
| claude-code 레포 구성 | github.com/dong8650/claude-code 생성, 프로젝트별 CLAUDE.md 작성 |

### 다음 할 일

- **5/3 (2026-05-03)**: Play Console → 비공개 테스트 12명 14일 충족 → 프로덕션 신청 버튼 클릭
- **AdSense**: 재검토 결과 대기 (1~4주, dong8650@gmail.com)
- **content-pipeline/CLAUDE.md**: claude.ai 웹 채팅 내용 정리 필요

---

## 마지막 업데이트

2026-05-01 — 뒤로가기 종료 버그 수정, AdSense 재검토 신청, Search Console 등록, TWA intent 브릿지 추가 (v1.0.30)

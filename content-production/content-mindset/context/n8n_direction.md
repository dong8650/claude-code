# 컨텐츠 자동화 파이프라인 — n8n 활용 방향성

> 현재 파이프라인(Python 서버 스크립트)을 n8n으로 어디까지 자동화할 수 있는지 정리.
> 마지막 업데이트: 2026-05-03

---

## 현재 파이프라인 구조 (n8n 도입 전)

```
[수동 트리거]
    ↓
ai_orchestrator.py (서버에서 직접 실행)
    ↓
대본 생성 → 이미지/스톡클립 → TTS → 영상 합성
    ↓
output_final.mp4 (서버에 저장)
    ↓
[수동] scp 다운로드 → 유튜브 수동 업로드
```

**병목 지점**: 영상 생성 이후 업로드·공유·분석이 전부 수동

---

## n8n 도입으로 해결할 문제

| 현재 문제 | n8n 해결 방향 |
|-----------|--------------|
| 영상 생성 후 수동 업로드 | 자동 YouTube 업로드 |
| 업로드 완료 여부 수동 확인 | Slack 알림 |
| 대본 품질 확인 불편 | 노션 자동 기록 + 검토 플로우 |
| 조회수 성과 파악 안 됨 | 주간 성과 리포트 자동화 |
| 에피소드 생성 수동 실행 | 스케줄 자동 실행 |
| 유튜브만 업로드 | 멀티플랫폼 동시 배포 |

---

## 워크플로우 1 — YouTube 자동 업로드 ✅ (구현 완료)

> 파일: `n8n_workflow_youtube_upload.json`

### 흐름
```
서버 auto_upload.py POST
    ↓
Webhook 수신 (n8n)
    ↓
Code 노드 — 유튜브 설명란 자동 생성
(BGM 크레딧, 태그, 채널 슬로건 포함)
    ↓
Read Binary File — 서버 로컬 mp4 읽기
    ↓
YouTube Upload — 제목/설명/태그/공개범위 설정
    ↓
YouTube Comment — 고정 댓글 자동 등록
    ↓
Slack Notify — 업로드 완료 알림
    ↓
Respond to Webhook — 서버에 결과 반환
```

### 서버 실행 명령어
```bash
python3 /root/auto_pipeline/auto_upload.py \
  --ep episodes/20260503_001 \
  --style docsul \
  --privacy private
```

### 설정 필요 항목
- `REPLACE_WITH_YOUR_YOUTUBE_CREDENTIAL_ID`
- `REPLACE_WITH_YOUR_SLACK_CREDENTIAL_ID`
- `REPLACE_WITH_YOUR_SLACK_CHANNEL_ID`
- `config.py`의 `N8N_WEBHOOK_URL = "http://localhost:5678/webhook/youtube-upload"`

---

## 워크플로우 2 — 에피소드 생성 스케줄러

> 매일 정해진 시간에 서버에서 ai_orchestrator.py 자동 실행

### 흐름
```
Cron Trigger (매일 오전 2시)
    ↓
SSH 노드 — 서버 접속
    ↓
Command 실행:
cd /root/auto_pipeline &&
nohup python3 -u ai_orchestrator.py
  --batch --count 3 --auto > batch.log 2>&1
    ↓
Wait 노드 — 60분 대기 (영상 생성 완료 예상)
    ↓
SSH — batch.log 마지막 10줄 확인
    ↓
Slack Notify — 완료/실패 결과 알림
```

### 포인트
- `--count 3` → 하루 3편씩 자동 생성
- 성공한 에피소드만 워크플로우 1(업로드)로 자동 연결 가능
- 실패 시 Slack으로 에러 로그 전달

---

## 워크플로우 3 — 대본 검토 플로우 (노션 연동)

> 생성된 대본을 노션에 자동 기록 → 승인 후 영상 제작 진행

### 흐름
```
Webhook 수신 (script.json 완성 시 서버가 POST)
    ↓
Notion — 대본 검토 DB에 새 페이지 추가
  - 제목: hook 텍스트
  - 내용: hook / script_ko / closing_ko
  - 상태: "검토 대기"
  - Quality Gate 점수
    ↓
Slack Notify — "새 대본 검토 요청" + 노션 링크
    ↓
[대기] 노션에서 상태를 "승인"으로 변경
    ↓
Notion Trigger (상태 변경 감지)
    ↓
SSH — 해당 ep 디렉토리에 영상 제작 명령 실행
```

### 노션 DB 필드 구조
| 필드 | 타입 | 내용 |
|------|------|------|
| 제목 | Title | hook 텍스트 |
| 스타일 | Select | docsul / janas / list / seulki |
| 상태 | Select | 검토 대기 / 승인 / 반려 |
| 점수 | Number | Quality Gate view_score |
| 영상 타입 | Select | 내레이션형 / 다큐형 / 인포그래픽형 |
| 에피소드 ID | Text | YYYYMMDD_NNN |
| 생성일 | Date | 자동 |

---

## 워크플로우 4 — 주간 성과 리포트

> 매주 월요일 오전에 지난 7일 성과를 자동 집계 → Slack + 노션 기록

### 흐름
```
Cron Trigger (매주 월요일 오전 9시)
    ↓
YouTube Data API — 최근 7일 업로드 영상 목록 조회
    ↓
각 영상별: 조회수 / 좋아요 / 댓글 / 시청 지속시간 수집
    ↓
Code 노드 — 성과 집계 및 순위 계산
  - 스타일별 평균 조회수 (docsul vs janas vs list)
  - 주제 유형별 성과 (emotion vs ranking vs money vs quote)
  - 최고 성과 영상 TOP3
    ↓
Notion — 주간 리포트 페이지 자동 생성
    ↓
Slack Notify — 리포트 요약 + 노션 링크
```

### 분석 항목
- **스타일별 성과**: 어떤 보이스 스타일이 잘 되나
- **주제 유형별 성과**: emotion / ranking / money / quote 중 어디서 터지나
- **영상 타입별 성과**: 내레이션형 vs 다큐형 vs 인포그래픽형
- **업로드 시간대 분석**: 어느 시간에 올린 영상이 잘 되나

---

## 워크플로우 5 — 멀티플랫폼 배포

> YouTube 업로드 완료 후 TikTok / Instagram Reels 자동 업로드

### 흐름
```
워크플로우 1 완료 이벤트
    ↓
[분기 1] TikTok Upload API
  - 제목: hook 텍스트 (21자 이내)
  - 해시태그 자동 추가 (#직장인 #30대 등)
    ↓
[분기 2] Instagram Graph API (Reels)
  - caption: hook + closing + 해시태그
  - cover_image: 영상 첫 프레임 자동 추출
    ↓
Slack Notify — 3개 플랫폼 업로드 완료 링크
```

### 주의사항
- TikTok: Content Posting API 승인 필요
- Instagram: Meta Business 계정 + 페이지 연결 필요
- 영상 길이 제한: TikTok 60초, Instagram Reels 90초 (현재 18~25초라 문제없음)

---

## 워크플로우 6 — 에러 모니터링

> 파이프라인 실패 시 즉시 알림

### 흐름
```
Cron Trigger (매 30분)
    ↓
SSH — batch.log에서 "ERROR" / "FAIL" / "Traceback" 검색
    ↓
에러 감지 시:
Slack Notify — 에러 내용 + 로그 마지막 20줄
    ↓
정상 시: 무시 (노이즈 방지)
```

### 감지 대상 에러
- `generate_script.py` API 타임아웃
- `generate_image.py` DALL-E quota 초과
- `generate_tts.py` ElevenLabs 크레딧 소진
- `make_video.py` FFmpeg 실패
- 디스크 용량 부족 (`df -h` 체크)

---

## 전체 자동화 아키텍처 (목표)

```
[매일 오전 2시 — Cron]
    ↓
워크플로우 2: 에피소드 3편 자동 생성
    ↓
워크플로우 3: 노션에 대본 등록 + Slack 검토 요청
    ↓
[검토 승인 — 노션]
    ↓
워크플로우 2 후속: 영상 제작 명령 실행
    ↓
워크플로우 1: YouTube 업로드 (private → 확인 후 public)
    ↓
워크플로우 5: TikTok / Instagram 자동 업로드
    ↓
[매주 월요일 — Cron]
    ↓
워크플로우 4: 주간 성과 리포트
```

---

## 구현 우선순위

| 순위 | 워크플로우 | 난이도 | 임팩트 | 상태 |
|------|-----------|--------|--------|------|
| 1 | YouTube 자동 업로드 | ⭐ | 높음 | ✅ 완료 |
| 2 | 에피소드 생성 스케줄러 | ⭐⭐ | 높음 | ⏳ 미구현 |
| 3 | 에러 모니터링 | ⭐ | 중간 | ⏳ 미구현 |
| 4 | 대본 검토 플로우 | ⭐⭐⭐ | 중간 | ⏳ 미구현 |
| 5 | 주간 성과 리포트 | ⭐⭐⭐ | 높음 | ⏳ 미구현 |
| 6 | 멀티플랫폼 배포 | ⭐⭐⭐⭐ | 매우 높음 | ⏳ 미구현 |

---

## n8n 설치 정보

- **설치 위치**: 로컬 맥북 (서버가 아닌 클라이언트)
- **접속**: `http://localhost:5678`
- **서버 연결**: SSH 노드로 192.168.0.21 접속
- **워크플로우 파일**: `n8n_workflow_youtube_upload.json` (import 가능)

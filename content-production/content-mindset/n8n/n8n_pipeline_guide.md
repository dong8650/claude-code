# n8n 자동화 파이프라인 가이드

> 매일의 설계 채널 — 매일 00:00 인포그래픽 + 내레이션/다큐 영상 자동 생성 및 YouTube 업로드

---

## 워크플로우 파일

| 파일 | 용도 |
|------|------|
| `n8n_workflow_daily_auto.json` | **메인** — 매일 00:00 자동 실행 |
| `n8n_workflow_youtube_upload.json` | 수동 one-off 업로드용 (webhook) |

---

## 일일 업로드 스케줄

| 요일 | 인포그래픽 | 에피소드 |
|------|-----------|---------|
| 월·수·금·일 | ✅ | 내레이션형 (DALL-E 이미지) |
| 화·목·토 | ✅ | 다큐형 (Pexels 스톡) |

→ **매일 2편** 자동 업로드

---

## 파이프라인 흐름

```
00:00 Cron
  │
  ├─ [1] Daily Plan (Code)
  │       요일 → videoType 결정 (narration / docu)
  │
  ├─ [2] Git Sync (SSH)
  │       git pull origin main
  │       cp *.py → /root/auto_pipeline/
  │       cp infographic_topic_pool.json → /root/auto_pipeline/
  │
  ├─ [3] Generate Infographic Data (SSH)
  │       python3 generate_infographic_data.py
  │       Claude API로 오늘의 주제 데이터 생성 → data_YYYYMMDD.json
  │
  ├─ [4] Parse Infographic Topic (Code)
  │       stdout JSON 파싱 → data_file 경로 추출
  │
  ├─ [5] Infographic Generate (SSH)
  │       python3 generate_infographic.py --data data_YYYYMMDD.json
  │       --video --duration 7  (~5분)
  │
  ├─ [6] Infographic Read Data (SSH)
  │       cat data_YYYYMMDD.json  (title/tags 읽기)
  │
  ├─ [7] Infographic Metadata (Code)
  │       YouTube 제목 / 설명 / 태그 생성
  │
  ├─ [8] Read Infographic Video (Read File)
  │       mp4 바이너리 읽기
  │
  ├─ [9] YouTube Infographic (YouTube Upload)
  │       비공개 업로드
  │
  ├─ [10] Episode Generate (SSH)
  │        setsid python3 ai_orchestrator.py
  │        --batch --count 1 --auto --video-type narration|docu
  │        백그라운드 실행 후 즉시 반환 (PID=$!)
  │
  ├─ [11] Wait 1h
  │        영상 생성 완료 대기 (내레이션 ~45분, 다큐 ~30분)
  │
  ├─ [12] Get Episode Info (SSH)
  │        python3 get_episode_info.py
  │        오늘 날짜 episodes/ 디렉토리 탐색 → 메타데이터 JSON 출력
  │
  ├─ [13] Episode Metadata (Code)
  │        YouTube 제목 / 설명 / 태그 생성
  │
  ├─ [14] Episode OK? (IF)
  │        error 필드 없으면 성공 분기
  │
  ├─ [성공] Read Episode Video → YouTube Episode → Slack ✅
  └─ [실패] Slack ❌
```

---

## 노드별 상세

### [2] Git Sync
```bash
cd /root/claude-code && git pull origin main \
&& cp /root/claude-code/content-pipeline/*.py /root/auto_pipeline/ \
&& cp /root/claude-code/content-pipeline/infographic_data/infographic_topic_pool.json /root/auto_pipeline/
```
- `topics.json` / `infographic_used.json` 은 서버 고유 — **복사하지 않음**

### [3] Generate Infographic Data
- `infographic_topic_pool.json` (50개 주제) 에서 미사용 주제 선택
- Claude API (`claude-sonnet-4-6`) 로 랭킹/표 데이터 생성
- `infographic_used.json` 에 사용 기록 → 중복 방지
- 50개 소진 시 자동 리셋 후 재순환 (매번 새 데이터 생성)

### [10] Episode Generate
```bash
setsid python3 -u ai_orchestrator.py \
  --batch --count 1 --auto --video-type narration \
  > /root/auto_pipeline/daily_gen.log 2>&1 </dev/null &
echo "PID=$!"
```
- `setsid` + `</dev/null` : SSH 세션 즉시 반환 (없으면 SSH가 프로세스 종료까지 대기)

---

## 서버 구성

| 서버 | 도메인 | n8n 포트 | 역할 |
|------|--------|---------|------|
| zbx-proxy-dc1 (192.168.0.21) | kdclab.kr | 8084 | 메인 (Active) |
| arkime-dc2 (7.7.7.254) | tossdata.fortiddns.com | 8084 | 백업 (메인 장애 시 Active ON) |

---

## 서버 최초 세팅

```bash
# 1. git 클론
git clone https://github.com/dong8650/claude-code.git /root/claude-code

# 2. 최신 파일 복사 (최초 1회)
cp /root/claude-code/content-pipeline/*.py /root/auto_pipeline/
cp /root/claude-code/content-pipeline/infographic_data/infographic_topic_pool.json /root/auto_pipeline/
cp /root/claude-code/content-pipeline/topics.json /root/auto_pipeline/
```

### n8n Docker 배포

```bash
# zbx-proxy-dc1 (kdclab.kr)
docker run -d --name n8n --privileged --user root \
  -p 8080:8080 -e N8N_PORT=8080 -e N8N_SECURE_COOKIE=false \
  -e N8N_HOST=kdclab.kr -e N8N_PROTOCOL=http \
  -e WEBHOOK_URL=http://kdclab.kr:8084/ \
  -e GENERIC_TIMEZONE=Asia/Seoul -e TZ=Asia/Seoul \
  -e N8N_RESTRICT_FILE_ACCESS_TO=/root \
  -v /root/.n8n:/root/.n8n \
  -v /root/auto_pipeline:/root/auto_pipeline \
  --restart always n8nio/n8n

# arkime-dc2 (tossdata.fortiddns.com) — DDNS 외부 8084 → 내부 8080
docker run -d --name n8n --privileged --user root \
  -p 8080:8080 -e N8N_PORT=8080 -e N8N_SECURE_COOKIE=false \
  -e N8N_HOST=tossdata.fortiddns.com -e N8N_PROTOCOL=http \
  -e WEBHOOK_URL=http://tossdata.fortiddns.com:8084/ \
  -e GENERIC_TIMEZONE=Asia/Seoul -e TZ=Asia/Seoul \
  -e N8N_RESTRICT_FILE_ACCESS_TO=/root \
  -v /root/.n8n:/root/.n8n \
  -v /root/auto_pipeline:/root/auto_pipeline \
  --restart always n8nio/n8n
```

---

## n8n Import 후 설정

1. **SSH 노드 6곳** Credential 지정
   - `Git Sync` / `Generate Infographic Data` / `Infographic Generate`
   - `Infographic Read Data` / `Episode Generate` / `Get Episode Info`
2. **YouTube OAuth2** — Google Console 승인된 리디렉션 URI 확인
   - kdclab.kr: `http://kdclab.kr:8084/rest/oauth2-credential/callback`
   - tossdata: `http://tossdata.fortiddns.com:8084/rest/oauth2-credential/callback`
3. **Active 토글** — 양쪽 서버 동시 ON 금지 (하루 4편 생성됨)

---

## 주의사항

- **Wait 노드**: 60분 (내레이션 ~45분 + 여유 15분). 테스트 시 1분으로 줄인 경우 운영 전 **60분** 으로 복원
- **YouTube 업로드**: 기본 `private` — YouTube Studio에서 수동 공개 전환
- **인포그래픽 BGM 없음**: BGM 필요 시 `--bgm bgm/bgm_dark_cinematic.mp3` 수동 추가
- **에피소드 생성 로그**: `tail -f /root/auto_pipeline/daily_gen.log`

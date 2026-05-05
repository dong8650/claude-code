# 컨텐츠 자동화 파이프라인 — Claude 컨텍스트

> 이 파일을 읽으면 이전 대화 없이도 즉시 프로젝트 작업 가능.
> 업데이트 후 반드시 git push.

---

## 프로젝트 개요

| 항목 | 내용 |
|------|------|
| 채널명 | 매일의 설계 (@life-architecture) |
| 콘셉트 | 30~40대 대상 감정·철학·현실·돈·인간관계 쇼츠 — 대신 말해주고 관점을 바꿔주는 채널 |
| 목표 | 조회수 1만 이상 / 완전 자동화 완성 시스템 |
| 플랫폼 | 유튜브 쇼츠 / 틱톡 / 인스타릴스 |
| 개발자 | 김동천 · KDC Lab |

---

## 서버 정보

| 서버 | IP | 역할 | OS |
|------|-----|------|-----|
| zbx-proxy-dc1 | 192.168.0.21 | 메인 | Ubuntu 24.04 aarch64 |
| arkime-dc2 | 7.7.7.254 | 백업 | Ubuntu 22.04 aarch64 |

- **작업 디렉토리**: `/root/auto_pipeline/`
- **에피소드 디렉토리**: `/root/auto_pipeline/episodes/YYYYMMDD_NNN/`
- **rsync 자동 동기화**: 매일 새벽 3시 (sync_to_backup.sh)

---

## 영상 스타일 3종

### 1. 내레이션형
- DALL-E 3 이미지 8장 + TTS 음성 + ASS 자막 + BGM + Ken Burns
- hook → script_ko → closing_ko 구조
- **어울리는 주제**: 감정·철학·인간관계·돈·현실·사회 전반

### 2. 인포그래픽형
- 데이터 카드 정적 이미지(1080×1920) → 7초 MP4
- 음성 없음, 텍스트만, 다크 오렌지 스타일 (채널 색상 통일)
- **어울리는 주제**: 통계·데이터·순위 TOP8~10

### 3. 다큐형
- Pexels 실사 스톡 영상(bg*.mp4) + TTS 음성 + ASS 자막 + BGM
- Ken Burns 없음 — 실사 영상 그대로 사용
- **어울리는 주제**: 감정·철학·인간관계·돈·현실·사회 전반

---

## 영상 주문 프롬프트

### 내레이션형
```
내레이션형으로 만들어줘
주제: [주제]
스타일: docsul / janas / list / seulki 중 하나 (없으면 자동 선택)
```

### 다큐형
```
다큐형으로 만들어줘
주제: [주제]
```

### 인포그래픽형
```
인포그래픽형으로 만들어줘
주제: [주제]
타입: 랭킹 / 표 중 하나
```

### 스타일 옵션

| 스타일 | 분위기 | 어울리는 주제 |
|--------|--------|--------------|
| `docsul` | 낮고 묵직한 남성 | 철학, 현실, 경고성 |
| `janas` | 차분한 여성 | 감성, 인간관계, 위로 |
| `list` | 밝은 여성 | 순위, 정보, 팁 |
| `seulki` | ElevenLabs 고품질 | 프리미엄 영상 |

---

## 파일 구조

```
/root/auto_pipeline/
├── config.py                    # API Key, 경로 설정
├── topics.json                  # Seed Topic Pool — 검증된 주제 30개
├── generate_script.py           # GPT-4o 각색 → Claude 검수/교정 → Quality Gate
├── quality_gate.py              # Hard Gate + Drop + Soft Gate (Claude 의미 판단)
├── ai_orchestrator.py           # 오케스트레이터 — 배치/단일 CLI
├── generate_image.py            # [내레이션형] DALL-E 3 이미지 생성
├── generate_stock_clips.py      # [다큐형] Pexels 스톡 영상 다운로드 → bg*.mp4
├── generate_tts.py              # TTS + ASS 자막 생성 (내레이션형·다큐형 공통)
├── make_video.py                # [내레이션형] Ken Burns + 자막 영상 합성
├── make_video_stock.py          # [다큐형] 실사 클립 + 자막 영상 합성
├── generate_infographic.py      # [인포그래픽형] PIL 이미지 + FFmpeg 영상 생성
├── get_episode_info.py          # n8n SSH 노드 전용 — 오늘 에피소드 메타데이터 JSON 출력
├── analyze_youtube.py           # YouTube Analytics 분석 — 완시율·좋아요율·Claude 패턴 분석
├── auto_upload.py               # 수동 업로드용 (n8n webhook 경유, 자동화에는 불필요)
├── infographic_upload.py        # 수동 업로드용 (n8n webhook 경유, 자동화에는 불필요)
├── sync_to_backup.sh            # 백업 서버 동기화
├── bgm/
│   ├── bgm_philosophy.mp3
│   ├── bgm_dark_cinematic.mp3
│   ├── bgm_dramatic_ambient.mp3
│   └── ranking_candidates/      # 랭킹용 BGM 후보 (Kevin MacLeod CC BY 3.0)
│       ├── killers.mp3
│       ├── rocket_power.mp3
│       ├── volatile_reaction.mp3
│       └── hyperfun.mp3
├── data_*.json                  # 인포그래픽 데이터 파일 (git에서 infographic_data/에서 복사)
└── episodes/
    └── YYYYMMDD_NNN/
        ├── script.json          # 최종 대본
        ├── bg1~bg8.jpg          # [내레이션형] DALL-E 이미지
        ├── bg1~bg8.mp4          # [다큐형] Pexels 스톡 클립
        ├── voice_ko.mp3
        ├── subtitles_tts.ass
        └── output_final.mp4
```

---

## 내레이션형 / 다큐형 파이프라인

```
[내레이션형]
topics.json → generate_script.py → generate_image.py → generate_tts.py → make_video.py

[다큐형]
topics.json → generate_script.py → generate_stock_clips.py → generate_tts.py → make_video_stock.py
```

### 다큐형 명령어
```bash
cd /root/auto_pipeline

# 1. 대본 생성 (기존과 동일)
python3 ai_orchestrator.py --ep YYYYMMDD_NNN --topic-id [id] --script-only

# 2. Pexels 스톡 클립 다운로드 (bg*.jpg 대신 bg*.mp4)
python3 generate_stock_clips.py --ep episodes/YYYYMMDD_NNN --duration 5

# 3. TTS 생성
cd episodes/YYYYMMDD_NNN && python3 /root/auto_pipeline/generate_tts.py

# 4. 영상 합성
cd /root/auto_pipeline && python3 make_video_stock.py --ep episodes/YYYYMMDD_NNN --style docsul
```

---

## 인포그래픽형 파이프라인

```
data_*.json → generate_infographic.py → JPG + MP4 (7초, BGM 선택)
```

### 인포그래픽 명령어
```bash
cd /root/auto_pipeline

# 이미지만
python3 generate_infographic.py --data data_burnout.json

# 영상 (BGM 없음)
python3 generate_infographic.py --data data_burnout.json --video --duration 7

# 영상 (BGM 포함)
python3 generate_infographic.py --data data_burnout.json --video --duration 7 --bgm bgm/bgm_philosophy.mp3

# 로컬 다운로드
scp root@192.168.0.21:/root/auto_pipeline/data_burnout.mp4 ./
```

### 인포그래픽 데이터 자동 생성 (v3.8~)

- `generate_infographic_data.py` — Claude API로 매일 새 주제 데이터 생성
- `infographic_data/infographic_topic_pool.json` — 50개 주제 풀 (랭킹 40개 + 표 10개)
- `infographic_used.json` — 서버 고유, git 미포함 (사용된 topic_id 추적)
- 50개 소진 시 자동 리셋 후 재순환 (Claude가 매번 새 데이터 생성)

### 인포그래픽 기존 데이터 파일 현황 (수동 테스트용)

| 파일 | 제목 | 타입 |
|------|------|------|
| data_burnout.json | 직장인 10명 중 7명이 번아웃인 이유 TOP10 | 랭킹 |
| data_resign.json | 직장인이 퇴사하는 진짜 이유 TOP10 | 랭킹 |
| data_debt.json | 연령대별 평균 빚 | 표 |
| data_money_lifespan.json | 3억/6억 유통기한 | 표 |
| data_regret_20s.json | 40대가 20대로 돌아간다면 반드시 할 것 TOP8 | 랭킹 |
| data_quit_moment.json | 직장인이 이직을 결심하는 순간 TOP8 | 랭킹 |
| data_rich_fail.json | 월급쟁이가 절대 부자 못 되는 이유 TOP8 | 랭킹 |
| data_40s_fear.json | 40대 직장인이 새벽에 잠 못 자는 이유 TOP8 | 랭킹 |
| data_survive_10y.json | 직장에서 10년 살아남는 사람들의 비밀 TOP8 | 랭킹 |
| data_after_work.json | 한국 직장인 퇴근 후 실제 모습 TOP8 | 랭킹 |

### 인포그래픽 디자인
- **배경**: `#111111` 다크
- **강조색**: `#FF8C00` 오렌지 (채널 썸네일 톤 통일)
- **TOP1~3**: 오렌지 → 중간 오렌지 → 어두운 오렌지
- **헤더 구조**: 상단 30% (576px) 전체를 타이틀 전용 구역으로 고정
  - 제목 폰트 76px, 헤더 안에 세로 가운데 정렬
  - 오렌지 구분선(3px)으로 헤더 ↔ 아이템 분리
  - 아이템은 헤더 아래부터 나머지 70% 사용
- **워터마크**: `© 2026 매일의 설계` — channel_branding.py에서 임포트 (전 채널 공통)
- **BGM**: HitsLab — Pixabay 무료 (상업·수익화 채널 모두 허용, 크레딧 불필요)
  - 파일: `/root/content/runtime/mindset/bgm/bgm_infographic.mp3`

---

## 콘텐츠 방향

- **채널 미션**: 대신 말해주고, 관점을 바꿔주는 채널
- **closing 원칙**: 최대 20자. 좋아요·저장·공유 유발 — 아래 4패턴 중 1개 적용
  - ① 공감형  — "나만 이랬던 거 아니었어" 형태 (공감 폭발 → 좋아요)
  - ② 저장형  — "이거 저장 안 하면 또 당한다" 형태 (손실 공포 → 저장)
  - ③ 승리감형 — "이 영상 본 사람만 안다" 형태 (소수 선택감 → 공유)
  - ④ 공유형  — "지금 주변에 퍼뜨려야 함" 형태 (긴박감 → 공유)
  - FAIL: 단어 반전(역설) 금지. "표현이 너를 살린다" / "침묵이 답이었다" (hook 단어 뒤집기)
- **주제 다양성**: 직장 얘기 30~40%, 나머지는 인간관계·나이·돈·사회·자기인식·건강으로 분산

---

## 유튜브 쇼츠 알고리즘 구조

### 단계별 확산 구조

| 단계 | 조회수 | 핵심 지표 | 통과 조건 |
|------|--------|---------|---------|
| 1단계 초기 테스트 | 0 ~ 1,000 | 시청 유지율 / 스킵률 / 좋아요 | 끝까지 보게 만든다 |
| 2단계 확산 테스트 | 1,000 ~ 10,000 | **완시율 80%+** / 반복 재생 / 좋아요율 5~10% | 다시 보게 만든다 |
| 3단계 폭발 구간 | 10,000 ~ 100,000 | 완시율 90%+ / 반복 시청 / 댓글 발생 | 추천 알고리즘 확장 |
| 4단계 바이럴 | 100,000 ~ 1,000,000 | 저장 / 공유 / 멈춤+다시봄 | 공유하고 싶게 만든다 |

### 2~3천에서 멈추는 이유

> "끝까지는 보는데, 다시 보진 않는다"

- 초반 후킹 성공 → 시청 유지 → 반복 재생·감정 충격 부족 → 정체

### 영상 등급 기준

| 등급 | 조회수 | 상태 |
|------|--------|------|
| C급 | ~1,000 | 초반 후킹 실패 |
| B급 | 2,000~3,000 | 후킹 성공, 반복 재생 부족 |
| A급 | 1만+ | 반복 재생 발생 |
| S급 | 10만+ | 공유·저장 발생 |

### 핵심 개선 포인트

1. **Hook 공격적으로** — "당신은 이미 이용당했다" 수준 (통과형 아닌 멈추게 하는 수준)
2. **영상 길이 단축** — 28~36초 → 18~25초 (완시율 상승)
3. **마지막 문장** — "이거 저장 안 하면 또 당한다" / "지금 안 바꾸면 5년 뒤 똑같다" (반복 시청 유도)
4. **인포그래픽 속도** — 항목당 0.5~0.7초로 빠르게 (다시 봐야지 유발)

### 수치 목표

| 지표 | 목표 |
|------|------|
| 완시율 | 85% 이상 |
| 좋아요율 | 5% 이상 |
| 반복 시청 | 발생 |
| 영상 길이 | 20초 내외 |

---

## 대본 생성 파이프라인 구조 (v3.1 — Seed Topic Pool)

```
topics.json (검증된 주제 풀)
    ↓ topic_seed 선택 (CONTENT_RATIO 비율)
GPT-4o  — 각색 (발명 X, 각색만)
    ↓ hook / script_ko / closing_ko
Claude  — 검수/교정 (R1~R10 규칙)
    ↓
Quality Gate v3 — Hard(수치) → Drop(클리셰) → Soft(Claude 의미)
    ↓ PASS만
generate_image or generate_stock_clips → generate_tts → make_video or make_video_stock
```

### Claude 검수 항목 (R1~R10)
- `R1` hook 공백 제외 12자 이내
- `R2` script_ko 4~5문장, 총 60~120자, 문장별 18자 이하
- `R3` closing_ko 20자 이내 — **4패턴 보호** (공감형/저장형/승리감형/공유형, 단어 반전 교정 금지)
- `R4` 설명형 문장 → 직격형 교정
- `R5` 금지어·비속어·법적 위험
- `R6` scenes 8개 보장
- `R7` 클리셰 감지
- `R8` ranking/money 추상 표현 → 수치 교정
- `R9` 내면 직격 표현 보강
- `R10` ranking 타입 수치 기반 항목 보장

### Quality Gate v3 기준
| 기준 | 임계값 |
|------|--------|
| hook 길이 | ≤12자 |
| script 길이 | ≤120자 |
| 문장 수 | ≤5개 |
| closing 길이 | ≤20자 |
| scroll_stop_power | ≥7 |
| emotional_attack | ≥7 |
| repeat_value | ≥6 |
| view_score (Soft) | ≥7 |

---

## Seed Topic Pool (topics.json)

| content_type | 수량 | 예시 |
|---|---|---|
| emotion | 9 | 참을수록 망가지는 이유, 착한 사람이 손해 보는 구조 |
| ranking | 9 | 40대 되면 후회하는 30대 결정 TOP3 |
| money | 6 | 월급 300만원의 진짜 수명, 3억이면 몇 년 버티냐 |
| quote | 6 | 노력하면 더 망하는 사람, 착하게 살아서 잘 됐냐 |

**CONTENT_RATIO**: emotion 30% / ranking 30% / money 20% / quote 20%

---

## 기술 스택

| 항목 | 기술 |
|------|------|
| 대본 생성 | GPT-4o (각색) + Claude Sonnet (검수/교정) |
| 품질 게이트 | Quality Gate v3 (Hard + Drop + Soft) |
| 이미지 생성 | DALL-E 3 HD (8장, 9:16) — 내레이션형 |
| 스톡 영상 | Pexels API (무료, 상업 사용 가능) — 다큐형 |
| 인포그래픽 | PIL (Python) — 인포그래픽형 |
| 음성 합성 | Edge TTS (HyunsuNeural/SunHiNeural) + ElevenLabs API |
| 자막 | ASS 블러박스 자막 (단어별 \kf, 흰색→브론즈) |
| 영상 합성 | FFmpeg |
| 서버 | Ubuntu 24.04 aarch64 (ARM) |
| 언어 | Python 3.10 |
| 폰트 | NotoSansCJK-Bold.ttc |

---

## 에피소드당 비용 (실측)

| 스타일 | 비용 |
|--------|------|
| 내레이션형 | ~$0.775/편 (DALL-E 8장 $0.64 포함) |
| 다큐형 | ~$0.135/편 (Pexels 무료, TTS+API만) |
| 인포그래픽형 | ~$0/편 (API 미사용) |

---

## 인프라 문서

> n8n Docker 설치/설정, 서버 환경, API Keys 등 공통 인프라 문서:
> `content-pipeline-core/infra/n8n_requirements.md` — 서버 환경 + Docker 명령어 (공통)
> `n8n/n8n_pipeline_guide.md` — mindset n8n 워크플로우 흐름 상세 (이 채널 전용)

---

## n8n 자동화 워크플로우

### 워크플로우 파일 목록

| 파일 | 용도 | 상태 |
|------|------|------|
| `n8n/n8n_workflow_daily_auto.json` | **메인** — 매일 00:00 자동 생성+업로드 (단일 통합) | ✅ 완료 |
| `n8n/n8n_workflow_youtube_upload.json` | 수동 one-off 업로드용 (webhook 방식) | ✅ 완료 |

### 일일 자동화 스케줄

| 요일 | 내레이션형 | 다큐형 | 인포그래픽형 |
|------|-----------|-------|------------|
| 월·수·금·일 | ✅ | — | ✅ (매일) |
| 화·목·토 | — | ✅ | ✅ (매일) |

→ 하루 2편 자동 업로드. 인포그래픽은 Claude API가 매일 새 주제 생성 (50개 풀 순환).

### 일일 자동화 실행 흐름 (n8n_workflow_daily_auto.json)
```
00:00 Cron
    ↓ Code — 요일 판단 (videoType: narration/docu)
    ↓ SSH — git pull + cp *.py + infographic_topic_pool.json (Git Sync)
    ↓ SSH — generate_infographic_data.py (Claude API로 오늘 주제 데이터 생성)
    ↓ Code — data_file 경로 파싱 (Parse Infographic Topic)
    ↓ SSH — generate_infographic.py --video --duration 7 (BGM 없음, ~5분)
    ↓ SSH — cat data_YYYYMMDD.json (메타데이터 읽기)
    ↓ Code — 인포그래픽 YouTube 설명/태그 생성
    ↓ Read File — 인포그래픽 mp4 직접 읽기
    ↓ YouTube Upload — 인포그래픽 업로드
    ↓ SSH — setsid ai_orchestrator.py --video-type narration|docu (백그라운드)
    ↓ Wait 2시간 30분
    ↓ SSH — get_episode_info.py (에피소드 메타데이터 JSON)
    ↓ Code — 에피소드 YouTube 설명/태그 생성
    ↓ IF — 에피소드 생성 성공?
        ↓ 성공: Read File → YouTube Upload → Slack ✅
        ↓ 실패: Slack ❌
```

### 서버 최초 1회 세팅

```bash
# 1. git 클론
git clone https://github.com/dong8650/claude-code.git /root/claude-code

# 2. 런타임 디렉토리 생성
mkdir -p /root/content/runtime/mindset/{episodes,bgm}

# 3. 서버 고유 파일 배치
# config.py, topics.json → /root/content/runtime/mindset/
# bgm/*.mp3 → /root/content/runtime/mindset/bgm/

# 이후 n8n이 매일 git pull 만 실행 (cp 불필요)
# 코드는 /root/claude-code/content-production/content-mindset/ 에서 직접 실행
```

### n8n Docker 배포

```bash
# zbx-proxy-dc1 (192.168.0.21) — kdclab.kr
docker run -d --name n8n --privileged --user root \
  -p 8080:8080 -e N8N_PORT=8080 -e N8N_SECURE_COOKIE=false \
  -e N8N_HOST=kdclab.kr -e N8N_PROTOCOL=http \
  -e WEBHOOK_URL=http://kdclab.kr:8084/ \
  -e GENERIC_TIMEZONE=Asia/Seoul -e TZ=Asia/Seoul \
  -e N8N_RESTRICT_FILE_ACCESS_TO=/root \
  -v /root/.n8n:/root/.n8n -v /root/auto_pipeline:/root/auto_pipeline \
  --restart always n8nio/n8n

# arkime-dc2 (7.7.7.254) — tossdata.fortiddns.com (DDNS 외부 8084 → 내부 8080)
docker run -d --name n8n --privileged --user root \
  -p 8080:8080 -e N8N_PORT=8080 -e N8N_SECURE_COOKIE=false \
  -e N8N_HOST=tossdata.fortiddns.com -e N8N_PROTOCOL=http \
  -e WEBHOOK_URL=http://tossdata.fortiddns.com:8084/ \
  -e GENERIC_TIMEZONE=Asia/Seoul -e TZ=Asia/Seoul \
  -e N8N_RESTRICT_FILE_ACCESS_TO=/root \
  -v /root/.n8n:/root/.n8n -v /root/auto_pipeline:/root/auto_pipeline \
  --restart always n8nio/n8n
```

### Git Sync 아키텍처
- **코드 관리**: `/root/claude-code/` (git repo) — n8n이 매일 00:00에 `git pull`
- **실행 디렉토리**: `/root/claude-code/content-production/content-mindset/` — git repo에서 직접 실행 (cp 불필요)
- **런타임 데이터**: `/root/content/runtime/mindset/` — config.py, topics.json, infographic_used.json, episodes/, bgm/
- **서버 이중화**: 192.168.0.21 (메인 Active) / 7.7.7.254 (백업 — 메인 장애 시 Active ON)

### n8n import 후 설정 필요 항목
- SSH 노드 6곳: `REPLACE_WITH_SSH_CREDENTIAL_ID` → 해당 서버 SSH Credential 지정
- YouTube/Slack Credential ID는 각 서버에서 새로 등록 (OAuth 재인증 필요)

### n8n 주의사항
- YouTube Upload 노드: `description`, `privacyStatus`, `tags`는 반드시 `options` 하위
- YouTube Comment 노드 없음 — n8n 2.x 전 버전 미지원. YouTube Studio에서 수동 고정 댓글 필요
- n8n Docker: `--privileged` 필수 (DHI 보안 모델이 seccomp + AppArmor 동시 적용)

---

## 주요 명령어

```bash
MINDSET=/root/claude-code/content-production/content-mindset
RUNTIME=/root/content/runtime/mindset

# ── 내레이션형 배치 (대본만) ──────────────────────────────
cd $MINDSET
python3 ai_orchestrator.py --batch --count 10 --script-only

# ── 내레이션형 전체 파이프라인 ───────────────────────────
nohup python3 -u ai_orchestrator.py --batch --count 10 --auto > $RUNTIME/batch.log 2>&1 &

# ── 다큐형 배치 생성 ────────────────────────────────────
nohup python3 -u ai_orchestrator.py --batch --count 1 --auto --video-type docu > $RUNTIME/batch.log 2>&1 &

# ── 인포그래픽형 (랭킹/표) ───────────────────────────────
python3 generate_infographic.py --data $RUNTIME/data_burnout.json --video --duration 7

# ── 영상 로컬 다운로드 ───────────────────────────────────
scp root@192.168.0.21:$RUNTIME/episodes/YYYYMMDD_NNN/output_final.mp4 ./

# ── 배치 로그 확인 ───────────────────────────────────────
tail -f $RUNTIME/batch.log
```

---

## 작업 규칙

1. **배치 실행 시** `--start-seq`로 기존 ep 디렉토리 충돌 확인
2. **FAIL 대본** 절대 영상 단계 진행 금지 (Quality Gate가 차단)
3. **topics.json 수정 시** use_count/last_used 보존
4. **인포그래픽 연도 표기 금지** — subtitle에 "20XX 설문" 문구 넣지 않음
5. **Pexels 저작권**: 상업 사용 무료, 크레딧 불필요
6. **Kevin MacLeod BGM**: CC BY 3.0 — 유튜브 설명란에 크레딧 필수
7. **백업 동기화** 작업 후 sync_to_backup.sh 실행 확인
8. **ai_orchestrator.py `--ep`**: `YYYYMMDD_NNN` (episodes/ 없이) / **auto_upload.py `--ep`**: `episodes/YYYYMMDD_NNN` (접두사 포함) — 혼용 주의
9. **`--video-type`**: 배치/단일 모두 지원. `narration`(기본, DALL-E) | `docu`(Pexels 스톡)

---

## YouTube Analytics 분석

```bash
MINDSET=/root/claude-code/content-production/content-mindset

# 분석 실행 (첫 실행: OAuth 인증 필요)
cd $MINDSET && python3 analyze_youtube.py

# 저장된 결과만 재출력 (API 호출 없음)
cd $MINDSET && python3 analyze_youtube.py --report

# 기간 지정 (기본 90일)
cd $MINDSET && python3 analyze_youtube.py --days 30
```

### 첫 실행 OAuth 인증 절차
1. `python3 analyze_youtube.py` 실행
2. 출력된 URL을 브라우저에서 열기 (YouTube 채널 계정으로 로그인)
3. 인증 코드 복사 → 터미널에 붙여넣기
4. `youtube_analytics_token.json` 자동 저장 — 이후 자동 갱신

### 서버 사전 준비
```bash
# 패키지 설치
pip install google-api-python-client google-auth-oauthlib

# client_secret 업로드 (로컬에서)
scp ~/Downloads/youtube_client_secret.json root@192.168.0.21:/root/content/runtime/mindset/
```

### 출력 지표
| 지표 | 설명 |
|------|------|
| 완시율 (averageViewPercentage) | 핵심 — 85%+ 목표 |
| 평균 시청 시간 | 초단위 |
| 좋아요율 | 5%+ 목표 |
| 구독자 전환율 | 영상별 구독 유입 |
| 트래픽 소스 | Shorts피드/검색/구독 분류 |

> API 미제공: 반복재생 수, 저장 수, 초단위 시청 유지율 곡선 (YouTube Studio에서만 확인)

### 실측 채널 현황 (2026-05-05 기준)
- 채널 평균 완시율: **49.1%** (목표 85% 대비 -35.9%p)
- 완시율 100%+ 영상 4개 (반복재생 발생 확인)
  - 번아웃 TOP10: 180% / 영어 영상: 121% / 완벽주의자: 108% / 혼자인 게: 106%
- 좋아요율 최대 0.2% → **고정댓글 달기로 즉시 개선 필요**

---

## 노션 페이지

- 개발일지: https://www.notion.so/340cdf28986281359e2ceb38293db4fa
- 대본 검토: https://www.notion.so/340cdf28986281b39c4dc97e3a9c6819
- 백업 서버: https://www.notion.so/340cdf28986281a697b2e786261409a6

---

## 마지막 업데이트

2026-05-05 — v4.2 좋아요 설계 전략 적용
- make_video.py, make_video_stock.py: CTA 오버레이 추가 — 마지막 1.2초 "공감됐으면 좋아요  저장해두세요" (`#FFD700`, 36px, drawtext `enable='between(t,{cta_start},{N_main})'`)
- generate_script.py: Closing 4패턴 강제 (공감형/저장형/승리감형/공유형), 최대 15자→20자
  - R3 검수: "관점 전환 보호" → "4패턴 보호 (공감형/저장형/승리감형/공유형)"
  - Quality Gate: closing 길이 ≤15자 → ≤20자
  - repeat_value 채점: 관점전환 중심 → 행동유발(좋아요·저장·공유) 중심

2026-05-05 — v4.1 YouTube Analytics + 인포그래픽 개선 + 채널 공통 브랜딩
- analyze_youtube.py 신규: YouTube Analytics API OAuth 인증 + 완시율 랭킹 + Claude S급 전략 분석
- generate_infographic.py: 상단 30% 타이틀 전용 구역 고정 (피드 썸네일 가시성 개선)
  - 헤더 576px 고정, 제목 76px 세로 가운데 정렬, 오렌지 구분선
- channel_branding.py (pipeline-core): WATERMARK/CHANNEL_NAME/CHANNEL_HANDLE 단일 출처
  - generate_infographic.py, content-health/make_video_v2.py 모두 임포트
- 채널 실측: 평균 완시율 49.1%, 반복재생 영상 4개 확인

2026-05-05 — v4.0 런타임 경로 분리 + 코드 git 직접 실행 구조 완성
- auto_pipeline/ 의존성 완전 제거 — 코드를 /root/claude-code/content-production/content-mindset/ 에서 직접 실행
- 런타임 데이터: /root/content/runtime/mindset/ (config.py, topics.json, infographic_used.json, episodes/, bgm/)
- 전체 Python 파일 sys.path에 /root/content/runtime/mindset 추가 (config import 경로 수정)
- n8n Git Sync: cp 제거, git pull 단일 명령으로 단순화
- n8n_workflow_daily_auto.json: 모든 SSH 노드 경로 업데이트, infographic data_file full path 처리
- n8n Docker 볼륨: /root/auto_pipeline 제거, /root/content + /root/claude-code 추가
- infra 문서 content-pipeline-core/infra/ 로 이동 (n8n_requirements.md, n8n_pipeline_guide.md)
- 서버 config.py BGM 경로 수정: /root/auto_pipeline/bgm/ → /root/content/runtime/mindset/bgm/

2026-05-04 — v3.9 자동화 첫 실행 성공 + 이중화 서버 세팅 완료.
- 192.168.0.21 n8n 자동화 첫 실행 성공: 인포그래픽 + 에피소드 2편 YouTube 업로드
- 인포그래픽 BGM 제거 (--bgm 옵션 및 설명란 크레딧 삭제)
- 인포그래픽 주제 풀 중복 4개 교체 (기존 data_*.json 콘텐츠와 겹치는 항목)
- 7.7.7.254 (arkime-dc2) n8n Docker 설치 완료: tossdata.fortiddns.com:8084
- arkime-dc2 Credentials 등록 완료 (SSH/YouTube/Slack)
- arkime-dc2 인포그래픽 자동화 성공 확인, 에피소드 내일 재테스트 예정
- Episode Generate SSH 노드: setsid + </dev/null 적용 확인 (PID 즉시 반환)

2026-05-03 — v3.8 인포그래픽 AI 생성 로직 완성.
- generate_infographic_data.py 신규: Claude API로 매일 새 주제 데이터 생성
- infographic_topic_pool.json 신규: 50개 주제 풀 (랭킹 40개 + 표 10개)
- infographic_used.json 서버 고유 (git 미포함) — 중복 방지
- n8n 워크플로우: Git Sync → Generate Infographic Data → Parse Infographic Topic → 기존 흐름
- Episode Generate: setsid + </dev/null 적용 (SSH 즉시 반환 버그 수정)

2026-05-03 — v3.7 JSON 파일 구조 정리.
- n8n/ 폴더: n8n 워크플로우 JSON 2개
- infographic_data/ 폴더: data_*.json 10개
- samples/ 폴더: sample_*.json 2개
- Git Sync 명령어: infographic_data/data_*.json 경로로 수정

2026-05-03 — v3.6 Git Sync 아키텍처 완성.
- n8n_workflow_daily_auto.json: Git Sync 노드 추가 (매일 git pull → cp *.py data_*.json)
- 코드 관리=git, 서버=기술스택만 실행하는 구조로 완성
- 서버 이중화 지원: 192.168.0.21 / 7.7.7.254 동일 git 클론, SSH Credential만 교체
- topics.json은 서버 고유 보존 (use_count/last_used 이력)

2026-05-03 — v3.5 n8n 단일 통합 워크플로우 완성.
- n8n_workflow_daily_auto.json: 서버→n8n 콜백 루프 제거, 단일 직선 파이프라인
- get_episode_info.py 신규: n8n SSH 노드에서 에피소드 메타데이터 JSON 출력
- n8n에서 직접 Read File → YouTube Upload (webhook 방식 불필요)
- 구조: Cron→인포그래픽생성/업로드→에피소드생성(nohup)→Wait→에피소드업로드→Slack

2026-05-03 — v3.4 일일 자동화 파이프라인 완성.
- n8n_workflow_daily_auto.json 신규: 매일 00:00 인포그래픽+내레이션/다큐 자동 생성+업로드
- ai_orchestrator.py에 --video-type narration|docu 플래그 추가
- infographic_upload.py 신규: data_*.json 기반 인포그래픽 YouTube 업로드
- n8n YouTube Upload Code 노드: video_path override + 인포그래픽 description 분기 지원
- 일일 스케줄: 월/수/금/일=내레이션형, 화/목/토=다큐형, 매일=인포그래픽형

2026-05-03 — v3.3 n8n YouTube 자동 업로드 완성.
- n8n 워크플로우 1번(YouTube 자동 업로드) 실전 검증 완료
- auto_upload.py → n8n webhook → YouTube Upload → Slack 알림 파이프라인 동작
- Docker n8n: `--privileged` 필수 이유 확인 및 requirements.md 문서화
- YouTube Upload 노드 파라미터 구조 확정 (options 하위 배치)
- YouTube Comment 노드 제거 (n8n 2.x 전 버전 미지원)
- 첫 자동 업로드 성공: 20260503_money004 "10년 모아도 집 못 사는 현실" (비공개)

2026-05-02 — v3.2 3가지 영상 스타일 완성.
- 내레이션형: 기존 DALL-E 파이프라인 유지, 관점 전환 방향 강화
- 인포그래픽형: generate_infographic.py 다크오렌지 스타일, 데이터 JSON 10종
- 다큐형: generate_stock_clips.py (Pexels) + make_video_stock.py 신규
- 채널 방향: 직장 편중 → 감정·인간관계·돈·사회 전반으로 확장

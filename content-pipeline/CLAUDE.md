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
├── data_*.json                  # 인포그래픽 데이터 파일
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

### 인포그래픽 데이터 파일 현황

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
- **BGM 저작권**: Kevin MacLeod CC BY 3.0 — 설명란에 크레딧 필요
  - `Music: "[곡명]" by Kevin MacLeod (incompetech.com) Licensed under CC BY 3.0`

---

## 콘텐츠 방향

- **채널 미션**: 대신 말해주고, 관점을 바꿔주는 채널
- **closing 원칙**: 단어 반전(역설) 금지. 진짜 관점 전환 한 문장
  - PASS: "말할 때 비로소 산다" / "먼저 빼야 모인다" / "착함보다 경계가 먼저다"
  - FAIL: "표현이 너를 살린다" / "침묵이 답이었다" (hook 단어 뒤집기)
- **주제 다양성**: 직장 얘기 30~40%, 나머지는 인간관계·나이·돈·사회·자기인식으로 분산

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
- `R3` closing_ko 15자 이내 — **관점 전환 보호** (단어 반전 교정 금지)
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
| closing 길이 | ≤15자 |
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

## 주요 명령어

```bash
# ── 내레이션형 배치 (대본만) ──────────────────────────────
cd /root/auto_pipeline
python3 ai_orchestrator.py --batch --count 10 --script-only

# ── 내레이션형 전체 파이프라인 ───────────────────────────
nohup python3 -u ai_orchestrator.py --batch --count 10 --auto > batch.log 2>&1 &

# ── 다큐형 단일 영상 (ep 디렉토리 직접 지정) ─────────────
python3 generate_stock_clips.py --ep episodes/YYYYMMDD_NNN --duration 5
cd episodes/YYYYMMDD_NNN && python3 /root/auto_pipeline/generate_tts.py
cd /root/auto_pipeline && python3 make_video_stock.py --ep episodes/YYYYMMDD_NNN --style docsul

# ── 인포그래픽형 (랭킹/표) ───────────────────────────────
python3 generate_infographic.py --data data_burnout.json --video --duration 7

# ── 영상 로컬 다운로드 ───────────────────────────────────
scp root@192.168.0.21:/root/auto_pipeline/episodes/YYYYMMDD_NNN/output_final.mp4 ./
scp root@192.168.0.21:/root/auto_pipeline/data_burnout.mp4 ./

# ── 배치 로그 확인 ───────────────────────────────────────
tail -f /root/auto_pipeline/batch.log

# ── 백업 동기화 ──────────────────────────────────────────
/root/auto_pipeline/sync_to_backup.sh
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

---

## 노션 페이지

- 개발일지: https://www.notion.so/340cdf28986281359e2ceb38293db4fa
- 대본 검토: https://www.notion.so/340cdf28986281b39c4dc97e3a9c6819
- 백업 서버: https://www.notion.so/340cdf28986281a697b2e786261409a6

---

## 마지막 업데이트

2026-05-02 — v3.2 3가지 영상 스타일 완성.
- 내레이션형: 기존 DALL-E 파이프라인 유지, 관점 전환 방향 강화
- 인포그래픽형: generate_infographic.py 다크오렌지 스타일, 데이터 JSON 10종
- 다큐형: generate_stock_clips.py (Pexels) + make_video_stock.py 신규
- 채널 방향: 직장 편중 → 감정·인간관계·돈·사회 전반으로 확장

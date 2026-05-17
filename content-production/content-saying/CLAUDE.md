# content-saying — 매일의 설계 명언편

> 니체·쇼펜하우어 공개 도메인 명언 × Ken Burns × Edge TTS
> 이미지: fal.ai Flux.1 Dev — Dark Academia 스타일 가중치 (cinematic/woodcut/ink 53%)
> 대본: 원문(독일어)에서 직접 AI 재창작 — 출판사 번역본 미사용 (저작권 독립)

---

## 채널 정체성

| 항목 | 내용 |
|------|------|
| 채널명 | 매일의 설계 |
| 콘셉트 | 철학자의 말, 오늘 하루에 대입 — Dark Academia |
| 대상 | 30~40대 — 지치고 회의적인 직장인 |
| 길이 | 22~30초 목표 |
| 이미지 | fal.ai Flux.1 Dev ($0.025/장 × 3 = $0.075/편) |
| TTS | Edge TTS ko-KR-HyunsuNeural (무료) |
| 대본 | Claude Haiku — 원문 재창작 (~$0.001/편) |
| 여운 | Claude Sonnet — echo 생성 (~$0.001/편) |

---

## 영상 구조 (3 클립)

```
clip1  인트로   (~3s)   "니체가 말했다"           — zoom-in
clip2  명언     (~18s)  quote_ko 낭독 (-15% 속도) — zoom-out
clip3  여운     (~5s)   echo_ko 한마디             — zoom-in
```

### 레이아웃 (mindset 동일)

| 요소 | 값 |
|------|-----|
| 상단 바 | 22% (422px) — 철학자명(흰색 64px) + 책 이름(오렌지 76px) |
| 하단 바 | 22% (422px) — WATERMARK + SLOGAN |
| 타이틀 y1 | H × 9% = 173px (철학자명) |
| 타이틀 y2 | y1 + 90px = 263px (책 이름) |
| 자막 MarginV | bot_bar_h + 40 = 462px |
| 자막 폰트 | Intro 56px / Quote 64px / Echo 58px |

### 자막 스타일

| 스타일 | 색상 | 효과 |
|--------|------|------|
| Intro | 크림 `&H00C8E6F5` | 단순 표시 |
| Quote | **카라오케** 노란→흰 | 단어별 `\kf` 좌→우 채우기 |
| Echo | 오렌지 `&H00008CFF` | 단순 표시 |

- BGM: `bgm_dark_cinematic.mp3` volume 0.10, 끝 2초 페이드아웃

---

## 파일 구조

```
content-saying/
├── CLAUDE.md
├── topics_saying.json          # 명언 풀 45개 (니체 23 + 쇼펜하우어 22)
├── config_template.py          # 서버 config.py 템플릿
├── generate_script.py          # 명언 선택 + AI 재창작 + echo 생성
├── generate_image.py           # fal.ai Flux — Dark Academia 스타일 가중치
├── generate_tts.py             # Edge TTS 3분할 (intro/quote/echo)
├── make_video.py               # Ken Burns + 카라오케 자막 + BGM 합성
└── ai_orchestrator.py          # 파이프라인 CLI
```

---

## 대본 생성 방식

### 저작권 정책

- 원문(독일어)은 공개 도메인
- 기존 한국어 출판 번역본은 저작권 있음 → **절대 미사용**
- 매 에피소드마다 Claude Haiku가 원문에서 직접 재창작

### Dark Academia 재창작 스타일 (`_MAIN_PROMPT`)

- 웅장하고 선언적인 문장
- 직접적·능동형·2인칭("당신은") 선호
- 번역체·수동형 금지
- 40자 이내, 영상 자막으로 충격이 있을 것

### Echo 바이럴 3패턴 (`_ECHO_PROMPT`)

| 패턴 | 예시 |
|------|------|
| 공격형 (반박 불가) | "편안함이 당신을 죽이고 있다" |
| 공감형 (나 얘기다) | "혼자가 편한 게 잘못이 아니다" |
| 질문형 (불편한 거울) | "당신은 지금 생각하고 있나" |

---

## 이미지 생성 방식

### Dark Academia 스타일 가중치

| 스타일 | Weight | 비율 |
|--------|--------|------|
| 다크 시네마틱 | 3 | 18% |
| 렘브란트 유화 | 2 | 12% |
| **독일 표현주의 목판화** | **3** | **18%** |
| 다크 애니메이션 배경 | 1 | 6% |
| **잉크 일러스트** | **3** | **18%** |
| 실루엣 인물 | 2 | 12% |
| 3D 추상 렌더 | 1 | 6% |
| 수채화 일러스트 | 2 | 12% |

Dark Academia 3종(cinematic + woodcut + ink) 합산 **53%**

---

## 주제 풀 (topics_saying.json)

| 철학자 | 편수 | 비고 |
|--------|------|------|
| 니체 | 23개 (001~023) | 즐거운 학문, 차라투스트라, 선악의 저편 등 |
| 쇼펜하우어 | 22개 (001~022) | 의지와 표상, 소품과 부록 등 |
| **합계** | **45개** | |

### 추가 예정 철학자

| 철학자 | 비고 |
|--------|------|
| 마르쿠스 아우렐리우스 | 《명상록》— 감성 높음, 스토아 |
| 알베르 카뮈 | 실존주의, 공유율 높음 |
| 칸트 | 딱딱한 문장 → echo로 풀어야 함 |

---

## 서버 최초 세팅

```bash
# 1. 런타임 디렉토리 생성
mkdir -p /root/content/runtime/saying/episodes

# 2. config.py 배치 (config_template.py 참고)
vi /root/content/runtime/saying/config.py
# → CLAUDE_API_KEY, FAL_API_KEY, BGM_PATH, FONT_PATH 입력

# 3. topics_saying.json 복사
cp /root/claude-code/content-production/content-saying/topics_saying.json \
   /root/content/runtime/saying/

# 4. 패키지 설치
pip3 install fal-client anthropic edge-tts requests
```

---

## 실행 명령어

```bash
SAYING=/root/claude-code/content-production/content-saying
RUNTIME=/root/content/runtime/saying

# 랜덤 철학자 1편
cd $SAYING && python3 ai_orchestrator.py --batch --count 1 --auto

# 니체만
cd $SAYING && python3 ai_orchestrator.py --batch --count 1 --auto --philosopher 니체

# 쇼펜하우어만
cd $SAYING && python3 ai_orchestrator.py --batch --count 1 --auto --philosopher 쇼펜하우어

# 백그라운드 실행
cd $SAYING && setsid python3 -u ai_orchestrator.py --batch --count 1 --auto \
  > $RUNTIME/daily_gen.log 2>&1 </dev/null &

# 로그 확인
tail -f $RUNTIME/daily_gen.log

# 영상 다운로드
scp root@192.168.0.21:$RUNTIME/episodes/YYYYMMDD_NNN/output_final.mp4 ~/Downloads/
```

---

## 에피소드당 비용

| 항목 | 비용 |
|------|------|
| 이미지 (fal.ai Flux.1 Dev × 3장) | ~$0.075 |
| TTS (Edge TTS) | $0 |
| 대본 재창작 (Claude Haiku) | ~$0.001 |
| echo 생성 (Claude Sonnet) | ~$0.001 |
| **총합** | **~$0.077/편** |

---

## 관련 파일

| 경로 | 설명 |
|------|------|
| `content-pipeline-core/` | Ken Burns / BGM 믹싱 / channel_branding 공통 모듈 |
| `content-org/` | 신규 채널 생성용 클론 템플릿 (이 파이프라인이 기반) |
| `content-production-codex.MD` | 채널 전략 기준 문서 (Codex) |

---

## 마지막 업데이트

2026-05-18 — v1.3 Dark Academia 강화

- `topics_saying.json`: 45개 (니체 5편 추가 — 도전/변화/인식, 쇼펜하우어 2편 추가 — 선택/자존감)
- `generate_script.py`: `_MAIN_PROMPT` Dark Academia 재창작 스타일 지침 (선언적/능동형/2인칭)
- `generate_script.py`: `_ECHO_PROMPT` 바이럴 3패턴 추가 (공격형/공감형/질문형)
- `generate_image.py`: `_STYLE_WEIGHTS` 추가 — cinematic/woodcut/ink 가중치 3, 합산 53%
- `generate_image.py`: `_THEME_VISUAL` 신규 5종 추가 (도전/변화/인식/선택/자존감)
- `content-org/` 신규: 이 파이프라인 기반 채널 클론 템플릿

2026-05-18 — v1.2 mindset 레이아웃 동기화

- `make_video.py`: `TOP_BAR_RATIO = 0.22`, `BOT_BAR_RATIO = 0.22`
- `make_video.py`: 타이틀 y1 = H×9%, y2 = +90px, fs1 = 64px, fs2 = 76px
- `make_video.py`: 자막 폰트 56/64/58px, `MarginV = bot_bar_h+40 = 462px`
- `make_video.py`: Quote 카라오케 (`&H0000FFFF` 노란, `_kf_line()` 단어별 채우기)

2026-05-18 — v1.1 8 features + fal.ai Flux 이미지

- fal.ai Flux.1 Dev: 에피소드별 철학자 분위기 3장, 8가지 스타일 랜덤
- pipeline-core 공통 모듈: `make_ken_burns_clip` (portrait_safe) / `concat_clips` / `assemble_video`
- `generate_script.py`: Claude Haiku로 원문 직접 AI 재창작 (저작권 독립)
- BGM 페이드아웃, TTS skip 로직, 이모지 제거

2026-05-18 — v1.0 초기 파이프라인 구축

- `topics_saying.json`: 니체 20개 + 쇼펜하우어 20개
- Ken Burns 3클립 구조, Edge TTS (무료), Claude API echo 생성

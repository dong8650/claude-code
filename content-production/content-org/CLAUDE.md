# content-org — 영상 채널 표준 템플릿

> 새 콘텐츠 채널을 만들 때 이 폴더를 기반으로 클론한다.
> content-saying 구조 기반 — Ken Burns + Edge TTS + fal.ai Flux + 카라오케 자막
> Codex 기준 적용 — 공격형 CTA 없음, 편집자 개입 흔적, 현실 설계형 톤

---

## 클론 절차

```bash
# 1. 폴더 복사
cp -r content-org content-xxx

# 2. 아래 체크리스트 항목 교체

# 3. 서버 배포
git add content-xxx && git commit -m "feat(content-xxx): 채널 초기화"
git push
ssh root@SERVER "cd /root/claude-code && git pull"

# 4. 서버 런타임 세팅 (아래 참조)

# 5. 테스트 에피소드 생성
python3 ai_orchestrator.py --batch --count 1 --auto
```

---

## 교체 체크리스트

### 코드 내 교체 항목

| 파일 | 상수/변수 | 설명 |
|------|-----------|------|
| `ai_orchestrator.py` | `CHANNEL_ID` | 채널 식별자 (예: `saying`, `history`) |
| `make_video.py` | `SLOGAN` | 채널 하단 슬로건 |
| `make_video.py` | `CHANNEL_ID` | 런타임 경로용 |
| `generate_script.py` | `CHANNEL_ID` | 런타임 경로용 |
| `generate_script.py` | `INTRO_PATTERNS` | 도입부 나레이션 패턴 목록 |
| `generate_script.py` | `_MAIN_PROMPT` | 대본 생성 Claude 프롬프트 |
| `generate_script.py` | `_ECHO_PROMPT` | 여운 생성 Claude 프롬프트 |
| `generate_image.py` | `CHANNEL_ID` | 런타임 경로용 |
| `generate_image.py` | `_SUBJECT_ATMOS` | 주제별 이미지 분위기 |
| `generate_tts.py` | `CHANNEL_ID` | 런타임 경로용 |
| `topics_template.json` | 전체 내용 | 실제 주제 풀로 교체 |

### config_template.py → config.py 배치

```
/root/content/runtime/{채널명}/config.py
```

`CHANNEL_ID`, `RUNTIME_DIR`, `EPISODES_DIR`, `API_KEYS` 수정 필수.

---

## 서버 런타임 세팅

```bash
CHANNEL=xxx  # 채널명

# 1. 런타임 디렉토리
mkdir -p /root/content/runtime/$CHANNEL/episodes

# 2. config.py 배치
cp /root/claude-code/content-production/content-$CHANNEL/config_template.py \
   /root/content/runtime/$CHANNEL/config.py
vi /root/content/runtime/$CHANNEL/config.py  # API keys 입력

# 3. topics JSON 배치
cp /root/claude-code/content-production/content-$CHANNEL/topics_template.json \
   /root/content/runtime/$CHANNEL/topics_$CHANNEL.json
# → 실제 주제 내용 채우기

# 4. 패키지 설치
pip3 install fal-client anthropic edge-tts requests
```

---

## 실행 명령어

```bash
CHANNEL=/root/claude-code/content-production/content-xxx

# 1편 생성
python3 $CHANNEL/ai_orchestrator.py --batch --count 1 --auto

# 특정 주제 분류로 생성
python3 $CHANNEL/ai_orchestrator.py --batch --count 1 --auto --subject 주제명

# 백그라운드
setsid python3 -u $CHANNEL/ai_orchestrator.py --batch --count 1 --auto \
  > /root/content/runtime/xxx/daily_gen.log 2>&1 </dev/null &

# 로그 확인
tail -f /root/content/runtime/xxx/daily_gen.log

# 영상 다운로드
scp root@192.168.0.21:/root/content/runtime/xxx/episodes/YYYYMMDD_NNN/output_final.mp4 ~/Downloads/
```

---

## 파일 구조

```
content-org/
├── CLAUDE.md               ← 이 파일
├── config_template.py      ← 서버 config.py 템플릿
├── topics_template.json    ← 주제 풀 구조 템플릿
├── generate_script.py      ← 대본 생성 (Claude API)
├── generate_image.py       ← 이미지 생성 (fal.ai Flux)
├── generate_tts.py         ← TTS 생성 (Edge TTS)
├── make_video.py           ← 영상 합성 (FFmpeg)
└── ai_orchestrator.py      ← 파이프라인 실행
```

---

## 영상 구조 (3클립 기본)

```
clip1  도입부    (~3s)   intro_ko        — zoom-in
clip2  핵심 내용 (~18s)  main_ko (-15%)  — zoom-out (느리게)
clip3  여운      (~5s)   echo_ko         — zoom-in, 어두운 오버레이
```

- 상단 바 22%: subject(흰색 64px) + subtitle(오렌지 76px)
- 하단 바 22%: WATERMARK + SLOGAN
- 자막: intro(크림) / main(카라오케 노란→흰) / echo(오렌지)
- BGM: volume 0.10, 끝 2초 페이드아웃

---

## 에피소드당 예상 비용

| 항목 | 비용 |
|------|------|
| 이미지 (fal.ai Flux × 3) | ~$0.075 |
| TTS (Edge TTS) | $0 |
| 대본 (Claude Haiku) | ~$0.001 |
| **합계** | **~$0.076/편** |

---

## 채널 확장 목록

| 채널 | 상태 | 주제 |
|------|------|------|
| content-saying | ✅ 운영 중 | 니체·쇼펜하우어 명언 |
| content-history | 계획 | 역사 인물 명언/결정적 장면 |
| content-stoic | 계획 | 마르쿠스 아우렐리우스·세네카 |

---

## Codex 핵심 원칙 (채널 공통)

> 공격형 CTA 없음 — 설계 원칙으로 끝낼 것
> 정체성 모욕 없음 — 구조 문제로 설명할 것
> AI 산출물 위에 편집자 판단 흔적을 남길 것
> 자동 생성 → 비공개 업로드 → 사람이 최종 공개 승인

---

## 마지막 업데이트

2026-05-18 — content-org v1.0 초기화
- content-saying 기반 표준 템플릿 생성
- Dark Academia 이미지 가중치 시스템 포함
- 카라오케 자막 (bot_bar_h+40 MarginV) 포함
- Codex 기준 적용 (CTA 제거, 편집자 개입 설계)

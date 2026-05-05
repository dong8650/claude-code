# content-health — 매일의 설계 건강편

> content-mindset(감정·철학·인간관계)과 독립 운영. Claude API 전용 (OpenAI = DALL-E만 사용).

---

## 채널 정체성

| 항목 | 내용 |
|------|------|
| 채널명 | 매일의 설계 |
| 워터마크 | © 2026 매일의 설계 |
| 슬로건 | 매일 하나씩, 건강 상식을 쌓자 |
| 콘텐츠 | 잘못된 건강 상식 뒤집기 — 반복재생·저장 폭발 |
| 길이 | 22~26초 (TTS 실제 길이 기준, 고정 아님) |
| 이미지 | DALL-E 3 귀여운 장기/캐릭터 스타일 (실제 사람 금지) |

---

## S급 포맷 (7장면, TTS 실제 길이 기준 — 22~26초 최적)

```
scene1  🔥 Hook       — Hook 3대 공식 중 1개 (정체성공격/전문가반전/잘못된상식직격)
scene2  ✅ 과학설명1  — 핵심 메커니즘 + 수치 (→ 기호 활용)
scene3  ✅ 과학설명2  — 추가 효과 + 이모지 + 수치
scene4  ⚠️ 잘못된상식 — 반전 포인트 "근데 대부분은..."
scene5  😱 감정충격   — "매일 이렇게 했던 당신..." 짧고 강하게
scene6  💾 저장유도   — 구체적 행동 촉구 + 💾
scene7  👀 루프트리거 — Hook 복선 구체적 언급 (추상적 "복선 있음" 금지)
```

**영상 길이 자동 결정**: TTS 실제 발화 시간 = 클립 길이 = 자막 타이밍 (고정 없음)

---

## 파일 구조

```
content-health/
├── CLAUDE.md
├── topics_health.json          # 건강 주제 풀 30개
├── health_used.json            # 서버 고유 — git 미포함
├── generate_script_v2.py       # Claude API → S급 대본 JSON (Quality Gate 포함)
├── generate_image_v2.py        # DALL-E 3 → 귀여운 장기 캐릭터 이미지 (9:16)
├── make_video_v2.py            # FFmpeg → S급 영상 (TTS 실제 길이 기준, 장면별 속도)
├── ai_orchestrator_v2.py       # CLI 오케스트레이터 (자동화용)
├── run_custom_v2.py            # 사전 정의 스크립트 즉시 실행
├── get_episode_info_v2.py      # n8n SSH 노드용
├── analyze_competitor.py       # 경쟁 채널 분석 (yt-dlp + Claude, 주 1회 권장)

competitor_insights.json       # 서버 고유 — git 미포함 (analyze_competitor.py 생성)

episodes_v2/                   # 서버 고유 — git 미포함
└── YYYYMMDD_NNN/
    ├── script_v2.json
    ├── bg1~bg7.jpg
    ├── tts_scene*.mp3          # 장면별 TTS
    ├── voice_ko.mp3            # concat TTS
    ├── subtitles_v2.ass
    └── output_final.mp4
```

---

## 영상 효과 (v1 이식)

| 효과 | v1 | v2 |
|------|----|----|
| Ken Burns | zoompan 짝수=줌인/홀수=줌아웃 | ✅ 동일 |
| 상단 검은 바 | 22% + 채널명 | ✅ 20% + "건강 상식 연구소" |
| 하단 검은 바 | 22% + 워터마크 | ✅ 18% + @health.lab.kr |
| 자막 스타일 | ASS Karaoke (노래방 효과) | ✅ ASS 장면별 (Hook=오렌지, Main=흰색, Save=노랑, Loop=시안) |
| BGM 믹싱 | voice 1.0 + bgm 0.18 | ✅ 동일 |
| TTS | 3분할 (hook/body/closing) | ✅ 장면별 실제 TTS 길이 기준 + 장면별 속도 차별화 |
| 자막 싱크 | TTS 예상 길이 기준 | ✅ 실제 클립 길이(ffprobe) 기준 — 프레임 정렬 오차 제거 |
| 이미지 방향 | 가로 이미지 오류 가능 | ✅ force_original_aspect_ratio=increase → crop 1080x1920 강제 |
| 해상도 | 1080×1920 25fps | ✅ 동일 |
| CRF | 18 | ✅ 동일 |

---

## 실행 명령어

```bash
HEALTH=/root/claude-code/content-production/content-health
RUNTIME=/root/content/runtime/health

# 경쟁 채널 분석 (주 1회 권장 — 처음 실행 시 또는 매주 월요일)
cd $HEALTH && python3 analyze_competitor.py

# 분석 결과만 출력 (재실행 없이)
cd $HEALTH && python3 analyze_competitor.py --report

# 자동 (주제 풀에서 순서대로)
cd $HEALTH && python3 ai_orchestrator_v2.py --batch --count 1 --auto

# 특정 주제 지정
cd $HEALTH && python3 ai_orchestrator_v2.py --topic morning_water

# 사전 정의 스크립트 즉시 실행
cd $HEALTH && python3 run_custom_v2.py

# 백그라운드 (n8n용)
cd $HEALTH && setsid python3 -u ai_orchestrator_v2.py --batch --count 1 --auto \
  > $RUNTIME/daily_gen_v2.log 2>&1 </dev/null &
echo "PID=$!"

# 로그 확인
tail -f $RUNTIME/daily_gen_v2.log

# 영상 다운로드
scp root@192.168.0.21:$RUNTIME/episodes/YYYYMMDD_NNN/output_final.mp4 ~/Downloads/
```

---

## 서버 최초 세팅

```bash
# 1. git 클론
git clone https://github.com/dong8650/claude-code.git /root/claude-code

# 2. 런타임 디렉토리 생성
mkdir -p /root/content/runtime/health/{episodes,bgm}

# 3. 서버 고유 파일 배치
# config.py → /root/content/runtime/health/
# bgm/*.mp3 → /root/content/runtime/health/bgm/
```

---

## Git Sync (n8n 자동화용)

```bash
cd /root/claude-code && git pull origin main
```
- cp 불필요 — 코드는 git repo에서 직접 실행

---

## 알고리즘 2차 테스트 돌파 전략

> 현재 채널 상태: 1차 통과(~2.5k) → **2차 실패** → 3차 미도달

| 단계 | 조회수 | 알고리즘이 보는 것 | 통과 조건 | 현재 |
|------|--------|-----------------|---------|------|
| 1차 | ~500 | 클릭율, 초반 3초 이탈 | 끝까지 보게 만든다 | ✅ 통과 |
| 2차 | ~2.5k | **완시율 85%+, 반복재생, 저장율** | 다시 보게 만든다 | ❌ 실패 |
| 3차 | ~10k | 공유, 댓글, 외부 유입 | 공유하고 싶게 만든다 | 미도달 |

**2차 실패 원인 (코드 수준 진단)**:
1. Hook이 "정보 전달형" → Identity Attack 없음 → **v2.5에서 Hook 3대 공식으로 수정** ✅
2. Quality Gate 없어 저품질 대본 그대로 통과 → **v2.5에서 Quality Gate 추가** ✅
3. 루프트리거 추상적 ("복선 있음") → 반복재생 유발 안 됨 → **v2.5에서 구체적 복선 강제** ✅
4. 첫 프레임 최적화 미구현 → 피드 썸네일 효과 없음 → **미구현**
5. YouTube Analytics 피드백 루프 없음 → **미구현**

---

## 알고리즘 수치 목표

| 지표 | 목표 | 적용 방법 |
|------|------|---------|
| 완시율 | 85%+ | 22~26초 + 2초마다 새 정보 (Hook 강도가 핵심) |
| 좋아요율 | 5%+ | 공감 자막 "매일 이렇게 했던 당신" |
| 반복시청 | 발생 | 루프트리거 — Hook 복선 구체적 언급 강제 |
| 저장 | 발생 | 저장유도 씬 + 구체적 행동 촉구 |
| 공유 | 발생 | 잘못된 상식 반전 + 감정충격 |

---

## n8n 자동화 워크플로우

### 워크플로우 파일 목록

| 파일 | 용도 | 상태 |
|------|------|------|
| `n8n/n8n_workflow_health_daily.json` | 매일 01:00 자동 생성+업로드 | ✅ 완료 |

### 일일 자동화 실행 흐름

```
01:00 Cron (매일)
    ↓ SSH — git pull (Git Sync)
    ↓ SSH — 경쟁 분석 (월요일만): analyze_competitor.py → competitor_insights.json
    ↓ SSH — setsid ai_orchestrator_v2.py --batch --count 1 --auto (백그라운드)
    ↓ Wait 30분
    ↓ SSH — get_episode_info_v2.py (에피소드 메타데이터 JSON)
    ↓ Code — YouTube 설명/태그 파싱
    ↓ IF — 에피소드 생성 성공?
        ↓ 성공: Read File → YouTube Upload → Slack ✅
        ↓ 실패: Slack ❌
```

### n8n import 후 설정 필요 항목
- SSH 노드 3곳: `REPLACE_WITH_SSH_CREDENTIAL_ID` → 해당 서버 SSH Credential 지정
- YouTube 노드: `REPLACE_WITH_YOUTUBE_CREDENTIAL_ID` → YouTube OAuth2 Credential 지정
- Slack Credential ID는 각 서버에서 등록

---

## 서버 패키지

```bash
# 기본 (초기 세팅 시)
pip install anthropic openai requests pillow edge-tts elevenlabs
apt install ffmpeg

# 알고리즘 최적화 추가 패키지 (v2.6~)
pip install yt-dlp google-api-python-client google-auth-oauthlib numpy moviepy
```

| 패키지 | 용도 | 구현 상태 |
|--------|------|---------|
| `yt-dlp` | 경쟁 채널 쇼츠 Hook 패턴 분석 | ✅ analyze_competitor.py |
| `google-api-python-client` | YouTube Analytics API (완시율·반복재생 측정) | ⏳ 미구현 |
| `google-auth-oauthlib` | YouTube Analytics OAuth 인증 | ⏳ 미구현 |
| `numpy` | 오디오 파형 분석 (BGM 볼륨 자동 최적화) | ⏳ 미구현 |
| `moviepy` | 빠른 컷 편집 (장면 전환 효과) | ⏳ 미구현 |

---

## 미구현 예정 기능

| 기능 | 우선순위 | 설명 |
|------|---------|------|
| YouTube Analytics 연동 | ⭐⭐⭐ | 실제 완시율·반복재생 수 읽어서 어떤 Hook이 효과적인지 피드백 루프 |
| 첫 프레임 최적화 | ⭐⭐ | 가장 충격적인 장면을 첫 0.3초에 배치 (피드 썸네일 효과) |
| BGM 볼륨 자동 최적화 | ⭐ | numpy로 오디오 파형 분석 → Hook 장면 BGM 강조 |

---

## 주의사항

- DALL-E image_prompt: 실제 사람 얼굴 금지 (cute cartoon 스타일만)
- `health_used.json` — 서버 고유, git push 금지
- BGM: `/root/content/runtime/health/bgm/bgm_dramatic_ambient.mp3`
- config.py: `/root/content/runtime/health/config.py`

---

## Quality Gate 기준 (v2.5~)

| 지표 | 최소 기준 | 미달 시 |
|------|---------|--------|
| scroll_stop_power | 7+ | Hook 재작성 (최대 2회 재시도) |
| emotional_attack | 7+ | 감정충격 장면 재작성 |
| loop_value | 6+ | 루프트리거 재작성 (복선 구체화) |

**Hook 3대 공식** (반드시 1개 적용):
1. 정체성 공격형 — "매일 {행동}했던 당신, 사실 {충격 사실}"
2. 전문가 반전형 — "의사들이 절대 말 안 해주는 {주제} 진실"
3. 잘못된상식 직격형 — "{대중 상식}, 사실 반대임"

**TTS 장면별 속도** (알고리즘 완시율 최적화):
| 장면 | 속도 | 이유 |
|------|------|------|
| Hook | -5% | 느리고 강하게, 멈추게 |
| 과학설명1 | +8% | 빠르게, 정보 압축감 |
| 과학설명2 | +5% | 약간 빠르게 |
| 잘못된상식 | +0% | 보통, 공감 유발 |
| 감정충격 | -8% | 매우 느리게, 여운 |
| 저장유도 | +5% | 약간 빠르게 |
| 루프트리거 | +12% | 매우 빠르게, 긴박감 |

---

## 마지막 업데이트

2026-05-05 — v2.7 싱크 완전 수정 + 세로형 강제
- make_video_v2.py: make_ken_burns_clip() → bool 반환 → float(실제 클립 길이) 반환으로 변경
- make_video_v2.py: actual_clip_durations 수집 (ffprobe 측정) → build_ass()에 적용
  - 기존: TTS 파일 길이 기준 자막 타이밍 → 프레임 정렬 오차 누적 (씬7개 기준 ~0.1초 오차)
  - 수정: 실제 클립 길이 기준 자막 타이밍 → 영상=자막 완전 동기화
- make_video_v2.py: 최종 출력에 -shortest 추가 (음성/영상 미세 차이 트림)
- make_video_v2.py: Ken Burns 전처리 세로형 강제
  - scale=1080:1920:force_original_aspect_ratio=increase → crop=1080:1920
  - DALL-E 가로/정사각형 이미지도 portrait로 변환 후 Ken Burns 적용
- analyze_competitor.py: MIN_VIEWS 필터 제거 (yt-dlp 검색 결과 view_count=0 문제 해결)
  - 74개 영상 전체 제목 패턴 분석 가능

2026-05-05 — v2.6 경쟁 채널 분석 연동
- analyze_competitor.py 신규: yt-dlp로 건강 쇼츠 상위 영상 수집 → Claude Hook 패턴 분류
- competitor_insights.json 생성 (RUNTIME_DIR, git 미포함)
- generate_script_v2.py: 인사이트 자동 로드 → 대본 생성 프롬프트에 주입
  - 최강 Hook 타입, 고성과 제목 예시, 핵심 문구가 Claude 대본에 반영됨
- 서버 필수 패키지: yt-dlp, google-api-python-client, google-auth-oauthlib, numpy, moviepy

2026-05-05 — v2.5 알고리즘 최적화 (2.5k 천장 돌파 목표)
- generate_script_v2.py: Hook 3대 공식 강제, Quality Gate (scroll_stop≥7, emotional≥7, loop≥6)
- Quality Gate 미달 시 최대 2회 자동 재시도 (Hook 재작성 피드백 포함)
- 25초 고정 완전 해제 — TTS 실제 길이 기준 (22~26초 최적)
- 루프트리거: "처음부터 보면 복선 있음" 금지 → Hook 복선 구체적 언급 강제
- make_video_v2.py: 장면별 TTS 속도 차별화 (Hook -5%, 감정충격 -8%, 루프 +12%)
- make_video_v2.py: 영상 길이 경고 (<18초 또는 >30초)

2026-05-05 — v2.4 TTS 싱크 완전 수정 + n8n 워크플로우 추가
- make_video_v2.py 전면 재작성: scene["duration"] 고정값 폐기 → 실제 TTS 파일 길이 기준
  - generate_scene_tts() → (voice_file, actual_durations) 반환 (패딩/트림 없음)
  - build_ass() durations 파라미터 추가 (실제 TTS 길이 기반 자막 타이밍)
  - Ken Burns 클립 길이도 actual_durations 사용 → 자막·음성·영상 완전 동기화
- n8n/n8n_workflow_health_daily.json 신규: 매일 01:00 자동 생성+업로드
  - Cron(01:00) → Git Sync → Episode Generate(백그라운드) → Wait 30분 → Get Episode Info → YouTube → Slack

2026-05-05 — v2.3 런타임 경로 분리 + 영상 품질 수정
- auto_pipeline_v2/ 의존성 완전 제거 — 코드를 /root/claude-code/content-production/content-health/ 에서 직접 실행
- 런타임 데이터: /root/content/runtime/health/ (config.py, health_used.json, episodes/, bgm/)
- generate_image_v2.py, generate_script_v2.py sys.path 수정 (config import 경로)
- make_video_v2.py FONT_PATH 수정: truetype → opentype (한글 제목/워터마크 □□□ 깨짐 수정)
- TTS 나레이션 길이 scene duration에 맞게 단축 (TTS/자막 싱크 불일치 수정)
- run_custom_v2.py: sys.path /root/auto_pipeline 참조 제거

2026-05-05 — v2.2 코드 관리=git, 서버=기술스택만 실행하는 구조로 완성
- 채널 브랜딩: 워터마크 "© 2026 매일의 설계" (v1 동일), CHANNEL_NAME "매일의 설계"
- topics_drama.json 제거, 드라마 관련 코드 전면 건강 상식으로 전환
- generate_image_v2.py: generate_health_image() kawaii 건강 일러스트 스타일
- get_episode_info_v2.py: drama 필드 → title, 건강 상식 연구소 채널 메타데이터
- run_custom_v2.py: 달리기 뇌변화 6씬 → S급 7씬 (잘못된상식 반전 씬 추가), 25초 고정

2026-05-04 — v2.1 건강 상식 연구소 채널 전환 완료
- 드라마 콘텐츠 제거 → 건강 상식 단일 채널
- topics_health.json: 30개 주제 (잘못된 상식 반전 포맷)
- make_video_v2.py: v1 영상 효과 완전 이식
  - Ken Burns zoompan (짝수=줌인, 홀수=줌아웃)
  - 상하 검은 바 + 채널 브랜딩
  - 장면별 TTS + duration 패딩 (장면별 싱크)
  - BGM 믹싱 voice 1.0 + bgm 0.18
  - ASS 자막 (Hook=오렌지, Main=흰색, Save=노랑, Loop=시안)
- generate_script_v2.py: 건강상식 단일 타입, 25초 고정 구조
- run_custom_v2.py: "달리기 후 뇌 변화" 즉시 실행 스크립트

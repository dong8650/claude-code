# content-health — 매일의 설계 건강편

> content-mindset(감정·철학·인간관계)과 독립 운영. 대본: Claude API. 숏폼 이미지: fal.ai Flux.1 Dev. 롱폼 이미지: Pexels 무료.

---

## 채널 정체성

| 항목 | 내용 |
|------|------|
| 채널명 | 매일의 설계 (`channel_branding.CHANNEL_NAME`) |
| 워터마크 | © 2026 매일의 설계 (`channel_branding.WATERMARK`) |
| 슬로건 | 매일 하나씩, 건강 상식을 쌓자 (health 전용, 로컬 상수) |
| 콘텐츠 | 잘못된 건강 상식 뒤집기 — 반복재생·저장 폭발 |
| 길이 | **35~50초 목표** (30초 미만 정보량 부족 경고, 55초 초과 완시율 경고) |
| 숏폼 이미지 | **fal.ai Flux.1 Dev** ($0.025/장, 7장 월 $5) — photo/digital/object 3종 스타일 |
| 롱폼 이미지 | Pexels 무료 API (pexels_query 키워드 검색) |

---

## S급 포맷 (7장면, TTS 실제 길이 기준 — 35~50초 목표)

```
scene1  🔥 Hook       (~5초, 25자)  — Hook 3대 공식 중 1개 (정체성공격/전문가반전/잘못된상식직격)
scene2  ✅ 과학설명1  (~8초, 40자)  — 핵심 메커니즘 + 수치 (→ 기호 활용)
scene3  ✅ 과학설명2  (~8초, 40자)  — 추가 효과 + 이모지 + 수치
scene4  ⚠️ 잘못된상식 (~8초, 40자) — 반전 포인트 "근데 대부분은..."
scene5  😱 감정충격   (~5초, 25자)  — "매일 이렇게 했던 당신..." 짧고 강하게
scene6  💾👍 저장유도  (~4초, 20자)  — 좋아요+저장 동시 촉구
scene7  👀 루프트리거 (~3초, 15자)  — Hook 복선 구체적 언급 (추상적 "복선 있음" 금지)
```

**narration 규칙**: 전체 165자 이내 (5자/초 기준). caption 핵심 1~2문장만.
**영상 길이 자동 결정**: TTS 실제 발화 시간 = 클립 길이 = 자막 타이밍 (고정 없음)

---

## 파일 구조

```
content-health/
├── CLAUDE.md
├── topics_health.json          # 건강 주제 풀 30개
├── health_used.json            # 서버 고유 — git 미포함
├── generate_script_v2.py       # Claude API → S급 대본 JSON (Quality Gate 포함)
├── generate_image_v2.py        # 숏폼 이미지 — fal.ai Flux.1 Dev ($0.025/장), photo/digital/object 3종 (9:16)
├── generate_image_longform.py  # 롱폼 이미지 — Pexels 무료 API (pexels_query 키워드 검색)
├── make_video_v2.py            # FFmpeg → S급 영상 (TTS 실제 길이 기준, 장면별 속도)
├── ai_orchestrator_v2.py       # CLI 오케스트레이터 (자동화용)
├── run_custom_v2.py            # 사전 정의 스크립트 즉시 실행
├── get_episode_info_v2.py      # n8n SSH 노드용
├── analyze_competitor.py       # 경쟁 채널 분석 (yt-dlp + Claude, 주 1회 권장)
├── test_run_realistic.py       # [테스트] 실사 DALL-E 이미지 스타일 (192.168.0.21에서 실행)
├── test_run_stock.py           # [테스트] Pexels 실사 영상 스타일 (7.7.7.254에서 실행)

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
| 상단 검은 바 | 22% + 채널명 | ✅ 20% + hook 텍스트 2줄 (흰색 56px / 오렌지 68px) |
| 하단 검은 바 | 22% + 워터마크 | ✅ 18% + `WATERMARK`(© 2026 매일의 설계) + `SLOGAN`(매일 하나씩, 건강 상식을 쌓자) |
| 자막 스타일 | ASS Karaoke (노래방 효과) | ✅ ASS 장면별 (Hook=오렌지, Main=흰색, Save=노랑, Loop=시안) |
| BGM 믹싱 | voice 1.0 + bgm 0.18 | ✅ 동일 |
| CTA 오버레이 | — | ✅ 마지막 1.2초 "공감됐으면 좋아요  저장해두세요" (`#FFD700`, 36px, borderw=2) |
| TTS | 3분할 (hook/body/closing) | ✅ 장면별 실제 TTS 길이 기준 + 장면별 속도 차별화 |
| 자막 싱크 | TTS 예상 길이 기준 | ✅ 실제 클립 길이(ffprobe) 기준 — 프레임 정렬 오차 제거 |
| 이미지 방향 | 가로 이미지 오류 가능 | ✅ force_original_aspect_ratio=increase → crop 강제 (portrait/landscape 모두 지원) |
| 해상도 (숏폼) | 1080×1920 25fps | ✅ 동일 |
| 해상도 (롱폼) | — | ✅ 1920×1080 25fps (landscape=True) |
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

# 숏폼만 자동 (기본값)
cd $HEALTH && python3 ai_orchestrator_v2.py --batch --count 1 --auto

# 롱폼만 (16:9 가로)
cd $HEALTH && python3 ai_orchestrator_v2.py --batch --count 1 --auto --mode long

# 롱폼 + 숏폼 순차 생성
cd $HEALTH && python3 ai_orchestrator_v2.py --batch --count 1 --auto --mode both

# 특정 주제 지정
cd $HEALTH && python3 ai_orchestrator_v2.py --topic morning_water

# 사전 정의 스크립트 즉시 실행
cd $HEALTH && python3 run_custom_v2.py

# 백그라운드 (n8n용)
cd $HEALTH && setsid python3 -u ai_orchestrator_v2.py --batch --count 1 --auto --mode both \
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
| 완시율 | 85%+ | ~~22~26초~~ → 18~30초 유효, 22~26초 최적 + 2초마다 새 정보 (Hook 강도가 핵심) |
| 좋아요율 | 5%+ | 공감 자막 "매일 이렇게 했던 당신" |
| 반복시청 | 발생 | 루프트리거 — Hook 복선 구체적 언급 강제 |
| 저장 | 발생 | 저장유도 씬 + 구체적 행동 촉구 |
| 공유 | 발생 | 잘못된 상식 반전 + 감정충격 |

---

## n8n 자동화 워크플로우

### 워크플로우 파일 목록

| 파일 | 용도 | 상태 |
|------|------|------|
| `n8n/n8n_workflow_health_daily.json` | 매일 02:00 자동 생성+업로드 | ✅ 완료 |

### 일일 자동화 실행 흐름

```
02:00 Cron (매일)
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
| `google-api-python-client` | YouTube Analytics API (완시율·반복재생 측정) | ✅ content-mindset/analyze_youtube.py (채널 공통 사용) |
| `google-auth-oauthlib` | YouTube Analytics OAuth 인증 | ✅ 동일 |
| `numpy` | 오디오 파형 분석 (BGM 볼륨 자동 최적화) | ⏳ 미구현 |
| `moviepy` | 빠른 컷 편집 (장면 전환 효과) | ⏳ 미구현 |

---

## 숏폼 이미지 생성 옵션 비교

| AI | 가격/장 | 7장 월비용 | 품질 | 비고 |
|----|---------|----------|------|------|
| DALL-E 3 | $0.080 | $17 | ★★★★★ | 이전 사용, fal.ai 전환으로 제거 |
| **Flux.1 Dev** | **$0.025** | **$5** | ★★★★★ | **현재 사용** (fal.ai) |
| Flux.1 Schnell | $0.003 | $0.6 | ★★★★ | fal.ai — 채널 궤도 후 전환 테스트 예정 |
| Stable Diffusion (자체) | 전기세만 | ~$0 | ★★★ | GPU 서버 필요, 운영 부담 |

> **현재 전략**: Flux.1 Dev 유지 (품질 우선, 알고리즘 2차 통과 목표). 채널 성과 안정화 후 Schnell 전환 비교 테스트.

---

## YouTube 업로드 메타데이터 작성 가이드

### 제목 패턴
```
[Hook 표현] | [구체적 궁금증 또는 충격 사실]
```
- 숏폼: `단거 먹으면 힘난다? 틀렸습니다 | 30분 후 더 피곤한 진짜 이유`
- 롱폼: `코로 숨쉬기 vs 입으로 숨쉬기 | 자는 동안 입 벌리는 사람, 몸에 무슨 일이 벌어지는지 알아?`

### 설명란 구조
```
[현상 1~2줄 — 공감 유발]

⚡ 핵심 메커니즘 (수치 포함, → 기호 활용)
⚠️ 잘못된 상식 결과
✅ 오늘 바로 실천법

📌 저장 유도 문구

#태그1 #태그2 ... #건강상식연구소
```

### 고정 댓글 구조
```
💡 영상 핵심 요약

[현상] 생기는 일
→ 수치/메커니즘

[올바른 습관]으로 달라지는 것
→ 수치/효과

🔧 오늘 바로 실천 (번호 목록)

[참여 유도 질문 — 댓글율 UP]
💾 저장 유도 문구
```

> **규칙**: 수치 1개 이상 필수 (신뢰도), 마지막에 저장 유도, 롱폼은 참여 유도 질문 추가
> **금지**: 설명란에 `<` `>` 꺾쇄괄호 사용 금지 — YouTube가 허용하지 않음. 비교 표현은 `A가 B보다` 형식으로 대체.

---

## 미구현 예정 기능

| 기능 | 우선순위 | 설명 |
|------|---------|------|
| YouTube Analytics 연동 | ⭐⭐⭐ | 실제 완시율·반복재생 수 읽어서 어떤 Hook이 효과적인지 피드백 루프 |
| 첫 프레임 최적화 | ⭐⭐ | 가장 충격적인 장면을 첫 0.3초에 배치 (피드 썸네일 효과) |
| BGM 볼륨 자동 최적화 | ⭐ | numpy로 오디오 파형 분석 → Hook 장면 BGM 강조 |

---

## 주의사항

- DALL-E image_prompt: 실사/시네마틱 스타일. 사람은 뒷모습·실루엣·부분(손발)만 허용. 얼굴 금지.
- ~~감정충격(scene5)·잘못된상식(scene4) 씬: 오브젝트 기반 프롬프트 필수~~ → 감정충격(scene5)만 object 고정 필수. scene4(잘못된상식)는 AI 자율 선택.
- content_policy_violation 발생 시 safe_fallback 자동 전환 (generate_image_v2.py 내장)
- `health_used.json` — 서버 고유, git push 금지
- BGM: `/root/content/runtime/health/bgm/bgm_dramatic_ambient.mp3`
- config.py: `/root/content/runtime/health/config.py`

---

## image_style 3종 시스템 (v3.0~)

씬마다 `image_style` 필드로 DALL-E 생성 방식을 결정. **씬 위치가 아닌 씬 내용 기준**으로 AI가 자율 선택.

| 스타일 | 선택 기준 | 적용 예시 |
|--------|---------|---------|
| `photo` | 현실에서 찍을 수 있는 장면 (운동, 생활, 행동) | 달리는 사람 뒷모습, 커피 마시는 장면 |
| `digital` | 눈에 안 보이는 내부 메커니즘 (뇌·세포·신호·장기) | 도파민 신경망, 목 디스크 구조 압박 |
| `object` | 사람 없이 사물로 상황 암시 | 닫힌 짐가방, 바닥의 운동화 |

**고정 규칙**:
- `scene5 감정충격` — `object` 고정 필수 (부정적 감정 씬 → content_policy_violation 차단)
- `scene7 루프트리거` — scene1 Hook과 **동일한 image_style** 강제 (시각적 루프 연결)
- 나머지 씬 — Claude가 씬 내용 보고 자율 판단

**suffix 방식** (`generate_image_v2.py`):
```python
_SUFFIX = {
    "photo":   "cinematic sports photography, photorealistic, golden hour, from behind or silhouette...",
    "digital": "cinematic sci-fi digital art, glowing neon particles, dark background, 3D render...",
    "object":  "cinematic still life photography, dramatic spotlight, dark moody, NO people...",
}
```

---

## Quality Gate 기준 (v2.5~)

| 지표 | 최소 기준 | 미달 시 |
|------|---------|--------|
| scroll_stop_power | 7+ | Hook 재작성 (최대 2회 재시도) |
| emotional_attack | 7+ | 감정충격 장면 재작성 |
| loop_value | 6+ | 루프트리거 재작성 (복선 구체화) |

**Hook 3대 공식 + 엄격 순환 (v3.4~)**:
- 순환 주기: `myth_direct → identity_attack → expert_reversal → myth_direct → ...`
- 타입은 Python `get_next_hook_type()`이 강제 결정 (Claude에게 선택 위임 안 함)
- 표현은 타입별 11개 후보 중 Python `random.choice()`로 매회 랜덤 선택
- 선택된 `{expression_template}`을 프롬프트에 주입 → Claude는 placeholder만 채움

| 타입 | 예시 표현 (총 11개 중 랜덤) |
|------|--------------------------|
| myth_direct | "{상식}, 틀렸습니다" / "평생 믿었던 {상식}, 오늘 뒤집힙니다" / ... |
| identity_attack | "매일 {행동}했던 당신, 사실 {충격 사실}" / "당신의 {행동}, 몸이 비명 지르고 있어" / ... |
| expert_reversal | "의사들이 절대 말 안 해주는 {주제} 진실" / "최신 연구가 뒤집은 {주제} 상식" / ... |

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

2026-05-06 — v3.4 Hook 3타입 엄격 순환 + 표현 11종 random.choice()
- HOOK_TYPE_CYCLE: myth_direct → identity_attack → expert_reversal (3편 주기 강제 순환)
- HOOK_VARIANTS: 타입별 11개 표현 후보, Python random.choice()로 매회 선택
- generate_script_v2.py: get_next_hook_type() + get_hook_expression() 추가
- 프롬프트에 forced_hook_type + expression_template 주입 → Claude는 placeholder만 채움
- 기존 avoid_hook_type 방식(권고) → 강제 지정 방식으로 교체

2026-05-06 — v3.3 롱폼 16:9 가로 영상 + --mode long 추가
- 롱폼 해상도: ~~1080×1920 (9:16)~~ → **1920×1080 (16:9)**
- video_core.py: make_ken_burns_clip에 size 파라미터 추가 (기본값 1080x1920 유지, landscape 시 1920x1080)
- make_video_v2.py: landscape=True 모드 — 바 높이(14%/10%), 자막 폰트 크기, 타이틀 위치 landscape 비율 적용
- generate_image_longform.py: Pexels orientation portrait → **landscape**
- generate_script_longform.py: 프롬프트 9:16 → 16:9, pexels_query landscape 기준으로 변경
- ai_orchestrator_v2.py: --mode 옵션 3종 확정
  - `shorts` (기본값): 숏폼만
  - `long`: 롱폼만 (16:9)
  - `both`: 롱폼+숏폼 순차

2026-05-06 — v3.2 숏폼 길이 35~50초 + fal.ai Flux 전환
- 숏폼 목표 길이: ~~22~26초~~ → **35~50초** (정보량 확보, 완시율 유지 균형)
- 씬별 duration 상향: Hook 3→5, 과학설명 5→8, 감정충격 3→5, 저장유도 2→4, 루프 1→3
- narration 글자수 규칙 추가: 전체 165자 이내 (5자/초 기준), 씬별 상한 명시
- make_video_v2.py 경고 기준: 30초 초과 → 55초 초과 / 18초 미만 → 30초 미만
- 숏폼 이미지: ~~DALL-E 3 ($0.08/장)~~ → **fal.ai Flux.1 Dev ($0.025/장, 69% 절감)**
- generate_image_v2.py: `_call_flux()` fal-client 기반으로 전면 교체
- generate_image_longform.py 신규: 롱폼 전용 Pexels 무료 이미지 (pexels_query 키워드 검색)
- ai_orchestrator_v2.py: --mode both 추가 (롱폼=Pexels, 숏폼=Flux 독립 생성)
- n8n_workflow_health_daily_both.json 신규: Wait 90분, 롱폼+숏폼 YouTube 업로드 2개

2026-05-05 — v3.0 image_style AI 자율 선택 시스템 + CLAUDE.md 현행화
- CLAUDE.md 전체 검토 후 코드와 불일치 항목 수정:
  - 상단 바: ~~"건강 상식 연구소"~~ → hook 텍스트 2줄 (흰색 56px / 오렌지 68px)
  - 하단 바: ~~@health.lab.kr~~ → WATERMARK + SLOGAN (코드 실제 출력 기준)
  - 길이: ~~22~26초~~ → 18~30초 유효(경고 기준), 22~26초 최적
- generate_image_v2.py: ~~단일 BASE_SUFFIX~~ → photo/digital/object 3종 suffix 분리
- generate_script_v2.py: ~~씬 위치 기준 고정 image_style~~ → 씬 내용 기준 AI 자율 판단
  - scene5(감정충격): object 고정 유지 (부정적 감정 씬 content_policy 차단)
  - ~~scene6(저장유도): object 고정~~ → photo/digital/object 자율 선택 (긍정 씬, 차단 위험 없음)
  - scene7(루프트리거): ~~자유 선택~~ → scene1 Hook과 동일 image_style 강제 (시각적 루프 연결)
- run_custom_v2.py: 달리기 후 뇌 변화 스크립트 — 카툰 프롬프트 → 씬별 realistic 프롬프트 + image_style 적용

2026-05-05 — v2.9 이미지 스타일 실사/시네마틱 전환
- generate_image_v2.py: 귀여운 장기 카툰 → 실사/시네마틱 스타일로 전환
  - `_BASE_SUFFIX`: photorealistic cinematic style, dramatic professional lighting
  - content_policy_violation 자동 감지 → safe_fallback (오브젝트 기반) 자동 전환
- generate_script_v2.py: image_prompt 규칙 카툰→실사, 사람은 뒷모습·실루엣·부분만, scene4/5 오브젝트 기반 강제
- JSON 템플릿 image_prompt 예시: cute cartoon → cinematic sports/health photography 예시로 교체

2026-05-05 — v2.8 좋아요 설계 전략 + 테스트 스크립트 + n8n 02:00
- make_video_v2.py: CTA 오버레이 추가 — 마지막 1.2초 "공감됐으면 좋아요  저장해두세요" (`#FFD700`, 36px, drawtext `enable='gte(t,{cta_start})'`)
- generate_script_v2.py: scene5 → 좋아요+저장 동시 촉구 (💾👍), 좋아요+저장 동시 유도 문구 강제
- likes_strategy.md (pipeline-core): CTA overlay 스펙, Closing 4패턴, Scene6 업그레이드 근거 문서화
- test_run_realistic.py 신규: 실사/시네마틱 DALL-E 스타일 테스트 (달리기 후 뇌 변화)
  - 실제 런닝하는 사람 이미지 (스포츠 사진 스타일), scene4/5는 오브젝트 기반 (content_policy 방지)
  - content_policy_violation 자동 감지 → safe_fallback 프롬프트 자동 전환
  - 192.168.0.21 서버에서 실행
- test_run_stock.py 신규: Pexels 실사 영상 스타일 테스트 (달리기 후 뇌 변화)
  - uhd≥2160 → hd≥1080 → hd≥720 우선순위 4K 소스 다운로드 (화질 개선)
  - `size="large"`, `per_page=15` (Pexels API 4K 노출 최적화)
  - 7.7.7.254 서버에서 실행
- n8n 워크플로우: Cron 01:00 → 02:00 변경

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

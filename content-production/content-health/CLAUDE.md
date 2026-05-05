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
| 길이 | 25초 고정 (S급 루프 구조) |
| 이미지 | DALL-E 3 귀여운 장기/캐릭터 스타일 (실제 사람 금지) |

---

## S급 포맷 (25초 고정)

```
0~3초   🔥 Hook       — "의사들이 매일 하는데 우리만 모름"
4~8초   ✅ 과학설명1  — 핵심 메커니즘 + 수치
9~14초  ✅ 과학설명2  — 추가 효과 + 이모지
15~19초 ⚠️ 잘못된상식 — 반전 포인트 "근데 대부분이..."
20~22초 😱 감정충격   — "매일 이렇게 했던 당신..."
23~24초 💾 저장유도   — "저장해두고 내일부터 해봐"
25초    👀 루프트리거 — "처음부터 보면 복선 있음"
```

---

## 파일 구조

```
content-health/
├── CLAUDE.md
├── topics_health.json          # 건강 주제 풀 30개
├── health_used.json            # 서버 고유 — git 미포함
├── generate_script_v2.py       # Claude API → S급 대본 JSON
├── generate_image_v2.py        # DALL-E 3 → 귀여운 장기 캐릭터 이미지 (9:16)
├── make_video_v2.py            # FFmpeg → 25초 S급 영상 (v1 효과 이식)
├── ai_orchestrator_v2.py       # CLI 오케스트레이터 (자동화용)
├── run_custom_v2.py            # 사전 정의 스크립트 즉시 실행
├── get_episode_info_v2.py      # n8n SSH 노드용

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
| TTS | 3분할 (hook/body/closing) | ✅ 장면별 TTS + duration 패딩 |
| 해상도 | 1080×1920 25fps | ✅ 동일 |
| CRF | 18 | ✅ 동일 |

---

## 실행 명령어

```bash
HEALTH=/root/claude-code/content-production/content-health
RUNTIME=/root/content/runtime/health

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

## 알고리즘 수치 목표

| 지표 | 목표 | 적용 방법 |
|------|------|---------|
| 완시율 | 85%+ | 25초 이내 + 2초마다 새 정보 |
| 좋아요율 | 5%+ | 공감 자막 "매일 이렇게 했던 당신" |
| 반복시청 | 발생 | 루프트리거 마지막 장면 |
| 저장 | 발생 | 23~24초 저장유도 |
| 공유 | 발생 | 잘못된 상식 반전 + 감정충격 |

---

## 주의사항

- DALL-E image_prompt: 실제 사람 얼굴 금지 (cute cartoon 스타일만)
- `health_used.json` — 서버 고유, git push 금지
- BGM 재사용: `/root/auto_pipeline/bgm/bgm_dramatic_ambient.mp3`
- config.py 재사용: `/root/auto_pipeline/config.py` 복사

---

## 마지막 업데이트

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

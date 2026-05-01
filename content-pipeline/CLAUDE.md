# 컨텐츠 자동화 파이프라인 — Claude 컨텍스트

> 이 파일을 읽으면 이전 대화 없이도 즉시 프로젝트 작업 가능.
> 업데이트 후 반드시 git push.

---

## 프로젝트 개요

| 항목 | 내용 |
|------|------|
| 채널명 | 매일의 설계 (@life-architecture) |
| 콘셉트 | 30~40대 직장인 대상 철학/뇌과학/명상 일인 |
| 목표 | 100만 조회수 / 완전 자동화 완성 시스템 |
| 플랫폼 | 유튜브 일인 / 틱톡 / 인스타릴스 |
| 개발자 | 김동천 · KDC Lab |

---

## 서버 정보

| 서버 | IP | 역할 | OS |
|------|-----|------|-----|
| zbx-proxy-dc1 | 192.168.0.21 | 메인 | Ubuntu 24.04 aarch64 |
| arkime-dc2 | 7.7.7.254 | 백업 | Ubuntu 22.04 aarch64 |

- **작업 디렉토리**: `/root/auto_pipeline/`
- **에피소드 디렉토리**: `/root/auto_pipeline/episodes/ep001~ep020/`
- **rsync 자동 동기화**: 매일 새벽 3시 (sync_to_backup.sh)

---

## 파일 구조

```
/root/auto_pipeline/
├── config.py                  # API Key, 경로 설정
├── generate_script.py         # GPT-4o 초안 → Claude 검수/교정 → script.json
├── ai_orchestrator.py         # 전체 파이프라인 오케스트레이터 (단일/배치 CLI)
├── generate_image.py          # DALL-E 3 이미지 생성
├── generate_tts.py            # TTS + ASS 자막 생성
├── make_video.py              # FFmpeg 영상 합성
├── run_all.py                 # 배치 실행 (전체 에피소드)
├── sync_to_backup.sh          # 백업 서버 동기화
├── batch_report.json          # 배치 실행 결과 리포트 (자동 생성)
├── bgm/
│   ├── bgm_philosophy.mp3
│   ├── bgm_dark_cinematic.mp3
│   └── bgm_dramatic_ambient.mp3
└── episodes/
    └── ep001~ep020/
        ├── script.json        # 최종 대본 (_meta, 품질 점수 포함)
        ├── review_log.json    # Claude 검수 결과 (자동 생성)
        ├── bg1~bg8.jpg
        ├── voice_ko.mp3
        ├── subtitles_tts.ass
        ├── segments.json
        └── output_final.mp4
```

---

## 대본 생성 파이프라인 구조 (v2 — 2026-05-01 변경)

```
[이전] Claude 초안 → GPT-4o 검수
[현재] GPT-4o 초안 → Claude 검수/교정/저장
```

| 단계 | 역할 | 모델 |
|------|------|------|
| ① 초안 생성 | 바이럴 최적화 대본 작성 (100만 조회수 프레임) | GPT-4o |
| ② 검수/교정 | 규칙 위반 탐지·자동 교정, 품질 점수 평가, script.json 저장 | Claude Sonnet |

### Claude 검수 항목
- `R1` hook 8자 이내 / `R2` script_ko 3~5문장·60~100자·문장별 18자 이하 / `R3` closing_ko 10자 이내
- `R4` 설명형 문장 탐지 → 직격형 교정
- `R5` 금지어·비속어·법적 위험 요소 탐지·수정
- `R6` scenes 8개 보장

### 품질 지표 (review_log.json에 기록)
| 지표 | 설명 |
|------|------|
| scroll_stop_power | hook의 스크롤 정지 유도력 (1~10) |
| emotional_attack | 감정 자극 강도 (1~10) |
| repeat_value | 반복 시청 가치 (1~10) |

---

## 기술 스택

| 항목 | 기술 |
|------|------|
| 대본 생성 | GPT-4o (초안) + Claude Sonnet (검수/교정) |
| 이미지 생성 | DALL-E 3 HD (8장, 9:16) |
| 음성 합성 | Edge TTS (HyunsuNeural/SunHiNeural) + ElevenLabs API |
| 자막 | ASS 블러박스 자막 (단어별 \kf, 흰색→브론즈) |
| 영상 합성 | FFmpeg (Ken Burns + drawbox + ass 자막) |
| 서버 | Raspberry Pi 4 (aarch64) |
| 언어 | Python 3.10 |
| 폰트 | NotoSansCJK-Bold.ttc |

---

## config.py 핵심 설정

```python
FONT_PATH = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
WATERMARK = "© 2026 매일의 설계"
ELEVENLABS_API_KEY = "..."
ELEVENLABS_SEULKI_VOICE_ID = "ksaI0TCD9BstzEzlxj4q"

BGM_MAP = {
    "docsul": ".../bgm_dark_cinematic.mp3",
    "janas":  ".../bgm_dramatic_ambient.mp3",
    "list":   ".../bgm_philosophy.mp3",
    "seulki": ".../bgm_dramatic_ambient.mp3",
}

VOICE_MAP = {
    "docsul":  "ko-KR-HyunsuNeural",
    "janas":   "ko-KR-SunHiNeural",
    "list":    "ko-KR-SunHiNeural",
    "seulki":  "elevenlabs",  # ElevenLabs Seulki
    "default": "ko-KR-HyunsuNeural",
}
```

---

## 영상 레이아웃 (EP005~ 기준)

```
[상단 검정 바 22%] → 제목 t1(흰색) + t2(주황) 가운데 정렬
[이미지 영역 56%] → Ken Burns 효과 + ASS 블러박스 자막
[하단 검정 바 22%] → 워터마크 + "이전보다 나은 오늘을 설계하자"
```

### make_video.py 핵심 파라미터
```python
INTRO_DURATION = 1.5          # 인트로 없음 (제거됨)
top_bar_h = int(1920 * 0.22)  # 상단 검정 바
bot_bar_h = int(1920 * 0.22)  # 하단 검정 바
title_y1  = int(1920 * 0.09)  # 제목1 y위치
title_y2  = int(1920 * 0.09) + 90  # 제목2 y위치
watermark_y = int(1920 - bot_bar_h + bot_bar_h * 0.20)
slogan_y    = watermark_y + 45
ASS MarginV = 480             # 자막 위치 (이미지 영역 내 하단)
```

---

## 대본 생성 규칙 (100만 조회수 적용)

```
[100만 조회수 적용 규칙]
- 첫 문장 반드시 8자 이내 (즉시 공격형)
- script_ko 3~5문장 (총 60~100자)
- 각 문장 18자 이하
- 설명형 금지 (일화형·감정형이 맞다 X)
- closing_ko 10자 이내 1문장
- 목표 영상 길이: 18~25초

[구조]
1. 직격 1문장 (8자 이내)
2. 사실 공감 1문장
3. 뒤집기/전환 1문장
4. 행동 이구 1문장
```

---

## TTS 구조 (generate_tts.py)

- **3분할**: hook / body / closing
- **split_script()**: `script["hook"]` → hook, `script_ko` 나머지 → body, `closing_ko` → closing
- **자막 타이밍**: 글자 수에 비례 배분 (균등 분배 X)
- **ASS 블러박스**: 단어별 `\kf` 태그 (흰색→브론즈)
- **ElevenLabs 분기**: `selected_voice == "elevenlabs"` 시 `_tts_elevenlabs()` 호출

---

## 에피소드 현황

| EP | 주제 | 스타일 | 상태 |
|----|------|--------|------|
| EP001 | 일희일비가 경고한 착한 척하는 사람의 말로 | docsul | ✅ 완료 |
| EP002 | 뇌과학이 말한 고통의 버티는 단 하나의 방법 | docsul | ✅ 완료 |
| EP003 | 당신의 하루가 바뀌지 않는 진짜 이유 | docsul | ✅ 완료 |
| EP004 | 30대가 되면 자연스럽게 사라지는 것들 | list | ✅ 완료 |
| EP005 | 직장 상사가 뒤집어 한 마디 | janas | ✅ 완료 |
| EP006 | 번아웃이 오기 전 몸이 보내는 신호들 | list | ✅ 완료 |
| EP007 | 호의적 압박이 대화한 한 마디 | janas | ✅ 완료 |
| EP008 | 아침주의자가 결국 아무것도 못 하는 이유 | docsul | ✅ 완료 |
| EP008_seulki | 아침주의자 (ElevenLabs Seulki 버전) | seulki | ✅ 완료 |
| EP009 | 공적 아버지가 뒤집어 한 마디 | janas | ✅ 완료 |
| EP010 | 스트레스를 받아도 큰 적 내는 사람들의 비밀 | seulki | 🔄 진행 중 |
| EP011 | 참을수록 망망해지는 이유 | docsul | ⏳ 대기 |
| EP012 | 일희일비가 운전을 믿지 않을 이유 | docsul | ⏳ 대기 |
| EP013 | 뇌과학이 말한 진짜 강한 사람의 조건 | docsul | ⏳ 대기 |
| EP014 | 자기믿음가이 절대 부자 못 되는 구조 | docsul | ⏳ 대기 |
| EP015 | 팀장이 대화하며만 일 시키는 이유 | janas | ⏳ 대기 |
| EP016 | 퇴사하려다 막히는 그런 밤 | janas | ⏳ 대기 |
| EP017 | 40대 되면 후회하는 30대의 실수들 | list | ⏳ 대기 |
| EP018 | 돈 못 버는 사람이 매일 하는 말 | list | ⏳ 대기 |
| EP019 | 진짜 번아웃이 온 사람들의 증상 | list | ⏳ 대기 |
| EP020 | 착한 척하는 사람 옆에 있으면 생기는 일 | docsul | ⏳ 대기 |

---

## 에피소드당 비용 (실측)

| 항목 | 비용 |
|------|------|
| Claude API | ~$0.045 |
| GPT-4o | ~$0.06 |
| DALL-E 3 HD (8장) | ~$0.64 |
| ElevenLabs | ~$0.03 |
| **합계** | **~$0.775/편 (약 1,100원)** |

---

## 현재 진행 상황

- EP001~EP009 완료, EP008_seulki 완료
- EP010 (seulki 스타일) 진행 중
- EP011~EP020 대기 중 (100만 조회수 대본 구조 적용 예정)
- ElevenLabs AI 보이스 연구 중 (차별화 음성)

### 다음 할 일

- [ ] EP010 완성 확인 및 다운로드
- [ ] ElevenLabs AI 로봇 음성 연구 (차별화 음성)
- [ ] EP011~ 100만 조회수 대본 구조 적용
- [ ] run_all.py로 EP011~EP020 배치 실행
- [ ] 자동 동기화 (sync_to_backup.sh) cron 등록 확인
- [ ] arkime-dc2 최신 파일 rsync 동기화

---

## 노션 페이지

- 개발일지: https://www.notion.so/340cdf28986281359e2ceb38293db4fa
- 대본 검토: https://www.notion.so/340cdf28986281b39c4dc97e3a9c6819
- 백업 서버: https://www.notion.so/340cdf28986281a697b2e786261409a6

---

## 주요 명령어

```bash
# ── 단일 에피소드 전체 파이프라인 ───────────────────────────
cd /root/auto_pipeline
python3 ai_orchestrator.py --ep ep011 --topic "참을수록 망가지는 이유" --style docsul

# ── 대본만 생성 (영상 없이) ─────────────────────────────────
python3 ai_orchestrator.py --ep ep011 --topic "..." --style docsul --script-only

# ── 대본 단독 테스트 (generate_script.py 직접 실행) ──────────
python3 generate_script.py --topic "주제 입력" --style docsul --ep-dir ./test_ep

# ── 배치 실행 (EP011~EP020) ──────────────────────────────────
cd /root/auto_pipeline && nohup python3 -u ai_orchestrator.py --batch > batch.log 2>&1 &

# ── 배치 로그 확인 ────────────────────────────────────────────
tail -f /root/auto_pipeline/batch.log

# ── 배치 결과 리포트 확인 ─────────────────────────────────────
cat /root/auto_pipeline/batch_report.json | python3 -m json.tool

# ── 검수 결과 확인 (에피소드별) ──────────────────────────────
cat /root/auto_pipeline/episodes/ep011/review_log.json

# ── 백업 동기화 ───────────────────────────────────────────────
/root/auto_pipeline/sync_to_backup.sh

# ── 영상 다운로드 (로컬에서) ─────────────────────────────────
scp root@192.168.0.21:/root/auto_pipeline/episodes/ep011/output_final.mp4 ./ep011.mp4
```

---

## 작업 규칙

1. **새 에피소드 추가 시** 에피소드 현황 테이블 업데이트
2. **배치 실행 전** run_all.py에 ep 범위 확인
3. **비용 추적** 에피소드당 $0.775 기준
4. **백업 동기화** 작업 후 sync_to_backup.sh 실행 확인

---

## 마지막 업데이트

2026-05-01 — 대본 파이프라인 v2 적용 (GPT-4o 초안 → Claude 검수), EP001~EP009 완료, EP010 진행 중

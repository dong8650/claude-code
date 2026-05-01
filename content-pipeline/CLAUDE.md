# 컨텐츠 자동화 파이프라인 — Claude 컨텍스트

> 이 파일을 읽으면 이전 대화 없이도 즉시 프로젝트 작업 가능.
> 업데이트 후 반드시 git push.

---

## 프로젝트 개요

| 항목 | 내용 |
|------|------|
| 채널명 | 매일의 설계 (@life-architecture) |
| 콘셉트 | 30~40대 직장인 대상 철학/심리/현실 충격 쇼츠 |
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

## 파일 구조

```
/root/auto_pipeline/
├── config.py                  # API Key, 경로 설정
├── topics.json                # Seed Topic Pool — 검증된 주제 30개
├── generate_script.py         # GPT-4o 각색 → Claude 검수/교정 → Quality Gate
├── quality_gate.py            # Hard Gate + Drop + Soft Gate (Claude 의미 판단)
├── ai_orchestrator.py         # 오케스트레이터 — 배치/단일 CLI
├── generate_image.py          # DALL-E 3 이미지 생성
├── generate_tts.py            # TTS + ASS 자막 생성
├── make_video.py              # FFmpeg 영상 합성
├── sync_to_backup.sh          # 백업 서버 동기화
├── batch_report.json          # 배치 실행 결과 (자동 생성)
├── bgm/
│   ├── bgm_philosophy.mp3
│   ├── bgm_dark_cinematic.mp3
│   └── bgm_dramatic_ambient.mp3
└── episodes/
    └── YYYYMMDD_NNN/
        ├── script.json        # 최종 대본 (topic_id, scores 포함)
        ├── script_review.json # Quality Gate 결과
        ├── generation_log.json
        ├── bg1~bg8.jpg
        ├── voice_ko.mp3
        ├── subtitles_tts.ass
        └── output_final.mp4
```

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
generate_image → generate_tts → make_video
```

### GPT 역할: 각색가 (발명가 아님)
- topic/angle/target_emotion을 풀에서 받아 각색
- topic을 다른 주제로 바꾸거나 임의 생성 금지
- angle이 대본의 핵심 관점, target_emotion이 직격 목표

### Claude 검수 항목 (R1~R10)
- `R1` hook 공백 제외 12자 이내
- `R2` script_ko 4~5문장, 총 60~120자, 문장별 18자 이하
- `R3` closing_ko 15자 이내
- `R4` 설명형 문장 → 직격형 교정
- `R5` 금지어·비속어·법적 위험
- `R6` scenes 8개 보장
- `R7` 클리셰 감지
- `R8` ranking/money 추상 표현 → 수치 교정
- `R9` 내면 직격 표현 보강
- `R10` ranking 타입 수치 기반 항목 보장
- **★ R3 역설 보호**: hook 핵심어 역설 반전 closing은 교정 금지

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

```json
{
  "id": "emotion_001",
  "content_type": "emotion",
  "topic": "참을수록 망가지는 이유",
  "angle": "억압이 자아를 지운다",
  "target_emotion": "찔림",
  "render_mode": "static",
  "last_used": null,
  "use_count": 0
}
```

| content_type | 수량 | 예시 |
|---|---|---|
| emotion | 9 | 참을수록 망가지는 이유, 착한 사람이 손해 보는 구조 |
| ranking | 9 | 40대 되면 후회하는 30대 결정 TOP3 |
| money | 6 | 월급 300만원의 진짜 수명, 3억이면 몇 년 버티냐 |
| quote | 6 | 노력하면 더 망하는 사람, 착하게 살아서 잘 됐냐 |

**CONTENT_RATIO**: emotion 30% / ranking 30% / money 20% / quote 20%
**배치 내 중복 사용 금지** / **최근 7일 사용 topic 제외**

---

## script.json 필드

```json
{
  "ep_id": "20260501_004",
  "topic_id": "money_002",
  "content_type": "money",
  "topic": "월급 300만원의 진짜 수명",
  "angle": "세후 실수령의 현실",
  "target_emotion": "충격",
  "hook": "월급250만의 실상",
  "script_ko": "300만원 월급, 세후 250만원...",
  "closing_ko": "증발이 시작이다",
  "final_status": "PASS",
  "view_score": 8,
  "_meta": { "scores": { "scroll_stop_power": 8, "emotional_attack": 9, "repeat_value": 7 } }
}
```

---

## 기술 스택

| 항목 | 기술 |
|------|------|
| 대본 생성 | GPT-4o (각색) + Claude Sonnet (검수/교정) |
| 품질 게이트 | Quality Gate v3 (Hard + Drop + Soft) |
| 이미지 생성 | DALL-E 3 HD (8장, 9:16) |
| 음성 합성 | Edge TTS (HyunsuNeural/SunHiNeural) + ElevenLabs API |
| 자막 | ASS 블러박스 자막 (단어별 \kf, 흰색→브론즈) |
| 영상 합성 | FFmpeg (Ken Burns + drawbox + ass 자막) |
| 서버 | Ubuntu 24.04 aarch64 (ARM) |
| 언어 | Python 3.10 |
| 폰트 | NotoSansCJK-Bold.ttc |

---

## config.py 핵심 설정

```python
FONT_PATH = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
WATERMARK = "© 2026 매일의 설계"
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
    "seulki":  "elevenlabs",
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

---

## TTS 구조 (generate_tts.py)

- **3분할**: hook / body / closing
- **자막 타이밍**: 글자 수에 비례 배분
- **ASS 블러박스**: 단어별 `\kf` 태그 (흰색→브론즈)
- **ElevenLabs 분기**: `selected_voice == "elevenlabs"` 시 `_tts_elevenlabs()` 호출

---

## 에피소드 현황

| EP | 주제 | 스타일 | 상태 |
|----|------|--------|------|
| ep001 | 일희일비가 경고한 착한 척하는 사람의 말로 | docsul | ✅ 완료 |
| ep002 | 뇌과학이 말한 고통의 버티는 단 하나의 방법 | docsul | ✅ 완료 |
| ep003 | 당신의 하루가 바뀌지 않는 진짜 이유 | docsul | ✅ 완료 |
| ep004 | 30대가 되면 자연스럽게 사라지는 것들 | list | ✅ 완료 |
| ep005 | 직장 상사가 뒤집어 한 마디 | janas | ✅ 완료 |
| ep006 | 번아웃이 오기 전 몸이 보내는 신호들 | list | ✅ 완료 |
| ep007 | 호의적 압박이 대화한 한 마디 | janas | ✅ 완료 |
| ep008 | 아침주의자가 결국 아무것도 못 하는 이유 | docsul | ✅ 완료 |
| ep008_seulki | 아침주의자 (ElevenLabs Seulki) | seulki | ✅ 완료 |
| ep009 | 공적 아버지가 뒤집어 한 마디 | janas | ✅ 완료 |
| ep010 | 스트레스 받아도 버티는 사람들의 비밀 | seulki | 🔄 진행 중 |
| 20260501_004 | 월급 300만원의 진짜 수명 (money_002) | docsul | ✅ PASS |
| 20260501_005 | 노력하면 더 망하는 사람 (quote_001) | janas | ✅ PASS |
| 20260501_006 | 직장에서 조용히 도태되는 신호 TOP3 (ranking_002) | list | ✅ PASS |

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

## 주요 명령어

```bash
# ── 배치 실행 (대본만, 10편) ──────────────────────────────
cd /root/auto_pipeline
python3 ai_orchestrator.py --batch --count 10 --script-only

# ── 배치 실행 (전체 파이프라인, nohup) ───────────────────
nohup python3 -u ai_orchestrator.py --batch --count 10 --auto > batch.log 2>&1 &

# ── 배치 시퀀스 번호 지정 (기존 ep 충돌 방지) ────────────
python3 ai_orchestrator.py --batch --count 3 --script-only --start-seq 7

# ── 단일 에피소드 — topic_id 지정 ────────────────────────
python3 ai_orchestrator.py --ep 20260501_010 --topic-id emotion_001

# ── 단일 에피소드 — content-type 지정 (pool 자동 선택) ───
python3 ai_orchestrator.py --ep 20260501_010 --content-type ranking --script-only

# ── 대본 단독 테스트 ─────────────────────────────────────
python3 generate_script.py --topic-id emotion_001 --topics-file topics.json

# ── 배치 로그 확인 ───────────────────────────────────────
tail -f /root/auto_pipeline/batch.log

# ── 배치 결과 리포트 ─────────────────────────────────────
cat /root/auto_pipeline/batch_report.json | python3 -m json.tool

# ── topics.json 사용 이력 확인 ───────────────────────────
python3 -c "
import json
ts = json.load(open('topics.json'))
for t in ts:
    if t.get('use_count', 0) > 0:
        print(t['id'], t['use_count'], t['last_used'][:10])
"

# ── 백업 동기화 ──────────────────────────────────────────
/root/auto_pipeline/sync_to_backup.sh

# ── 영상 다운로드 (로컬에서) ─────────────────────────────
scp root@192.168.0.21:/root/auto_pipeline/episodes/20260501_004/output_final.mp4 ./ep.mp4
```

---

## 작업 규칙

1. **배치 실행 시** `--start-seq`로 기존 ep 디렉토리 충돌 확인
2. **FAIL 대본** 절대 영상 단계 진행 금지 (Quality Gate가 차단)
3. **topics.json 수정 시** use_count/last_used 보존
4. **비용 추적** 에피소드당 $0.775 기준
5. **백업 동기화** 작업 후 sync_to_backup.sh 실행 확인

---

## 노션 페이지

- 개발일지: https://www.notion.so/340cdf28986281359e2ceb38293db4fa
- 대본 검토: https://www.notion.so/340cdf28986281b39c4dc97e3a9c6819
- 백업 서버: https://www.notion.so/340cdf28986281a697b2e786261409a6

---

## 마지막 업데이트

2026-05-01 — v3.1 Seed Topic Pool 적용 완료. topics.json 30개 검증 주제, Quality Gate v3, CONTENT_RATIO 배치, topic_id 추적. ep001~ep009 + 20260501_004~006 완료.

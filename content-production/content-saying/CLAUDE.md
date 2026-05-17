# content-saying — 매일의 설계 명언편

> 니체·쇼펜하우어 공개 도메인 명언 × Ken Burns × Edge TTS docsul
> 이미지: Wikimedia Commons 공개 도메인 사진 (저작권 없음)
> 번역: 원문(독일어)에서 직접 의역 — 출판사 번역본 미사용

---

## 채널 정체성

| 항목 | 내용 |
|------|------|
| 채널명 | 매일의 설계 |
| 콘셉트 | 철학자의 말, 오늘 하루에 대입 |
| 대상 | 30~40대 — 지치고 회의적인 직장인 |
| 길이 | 22~30초 목표 |
| 이미지 | Wikimedia 공개 도메인 사진 (비용 0) |
| TTS | Edge TTS ko-KR-HyunsuNeural (docsul, 비용 0) |
| 번역 | Claude API — 원문 의역 (에피소드당 ~$0.001) |

---

## 영상 구조 (3 클립)

```
clip1  인트로   (~3s)   "니체가 말했다"          — 철학자 사진 zoom-in
clip2  명언     (~18s)  quote_ko 낭독 (-15% 속도) — 다른 사진 zoom-out (가장 느리게)
clip3  여운     (~5s)   echo_ko 한마디            — 다시 zoom-in, 어두운 오버레이
```

- 상단 바: `{철학자} | {책 이름}` (14% 검정 바)
- 하단 바: 워터마크 `© 2026 매일의 설계` (10% 검정 바)
- 자막 스타일: intro=크림색, quote=흰색 대형, echo=오렌지
- BGM: bgm_dark_cinematic.mp3 (volume 0.10)

---

## 파일 구조

```
content-saying/
├── CLAUDE.md
├── topics_saying.json          # 명언 풀 40개 (니체 20 + 쇼펜하우어 20)
├── config_template.py          # 서버 config.py 템플릿
├── setup_images.py             # Wikimedia 사진 다운로드 (최초 1회)
├── generate_script.py          # 명언 선택 + Claude echo 생성
├── generate_tts.py             # Edge TTS 3분할 (intro/quote/echo)
├── make_video.py               # Ken Burns + 자막 + BGM 합성
└── ai_orchestrator.py          # 파이프라인 CLI
```

---

## 서버 최초 세팅

```bash
# 1. 런타임 디렉토리 생성
mkdir -p /root/content/runtime/saying/{episodes,images}

# 2. config.py 배치 (config_template.py 참고)
vi /root/content/runtime/saying/config.py

# 3. topics_saying.json 복사
cp /root/claude-code/content-production/content-saying/topics_saying.json \
   /root/content/runtime/saying/

# 4. BGM은 mindset 것 공유 사용 (별도 설치 불필요)

# 5. Wikimedia 사진 다운로드
cd /root/claude-code/content-production/content-saying
python3 setup_images.py
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

# 백그라운드
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
| 이미지 | $0 (Wikimedia 공개 도메인) |
| TTS | $0 (Edge TTS 무료) |
| echo 생성 (Claude) | ~$0.001 |
| **총합** | **~$0.001/편** |

---

## 철학자 확장 계획

| 철학자 | 추가 시기 | 비고 |
|--------|---------|------|
| 니체 + 쇼펜하우어 | ✅ 현재 | 각 20개 |
| 칸트 | 검증 후 | 딱딱한 문장 → echo로 풀어야 함 |
| 마르쿠스 아우렐리우스 | 검증 후 | 《명상록》— 감성 높음 |
| 알베르 카뮈 | 검증 후 | 실존주의, 공유율 높음 |

---

## 마지막 업데이트

2026-05-18 — v1.0 초기 파이프라인 구축
- topics_saying.json: 니체 20개 + 쇼펜하우어 20개
- 공개 도메인 사진 + Ken Burns 3클립 구조
- Edge TTS docsul (무료), 명언 파트 -15% 속도
- Claude API echo 생성 (에피소드당 ~$0.001)

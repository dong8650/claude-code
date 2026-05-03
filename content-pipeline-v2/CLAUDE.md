# content-pipeline-v2 — S급 드라마 쇼츠 파이프라인

> v1(매일의 설계 자기계발)과 독립 운영. Claude API 전용 (OpenAI 불필요).

---

## 콘셉트

| 항목 | 내용 |
|------|------|
| 채널 | 매일의 설계 (@life-architecture) |
| 포맷 | 한국 드라마 명대사 / 복선해석 / 반전요약 |
| 목표 | S급 영상 (반복재생·저장·공유 유발) |
| 길이 | 10초 (명대사) / 20초 (복선해석·반전요약) |
| 이미지 | DALL-E 3 — 드라마 분위기 재현 (실제 배우 금지) |
| 저작권 | AI 이미지 + 자막 + 나레이션 조합 → 안전 |

---

## S급 포맷 구조

### 명대사 (10초)
```
0~2초   Hook     — "이 대사 듣고 멈칫한 사람"
3~6초   핵심대사  — 드라마 명대사 자막 + 나레이션
7~9초   저장유도  — "저장해두고 힘들 때 꺼내봐요"
10초    루프트리거 — "처음부터 다시 보면 소름 돋음 👀"
```

### 복선해석 / 반전요약 (20초)
```
0~2초   Hook       — "이 장면이 복선인 거 아무도 말 안 해줬음"
3~13초  내용 설명  — 복선/반전 포인트 설명
14~17초 감정충격   — "복선이었다..."
18~19초 저장유도   — "저장 안 하면 다시 못 찾음"
20초    루프트리거 — "1초에 힌트 숨겨져 있음 👀"
```

---

## 파일 구조

```
content-pipeline-v2/
├── CLAUDE.md
├── topics_drama.json          # 드라마 주제 풀 30개
├── drama_used.json            # 서버 고유 — git 미포함
├── generate_script_v2.py      # Claude API → S급 대본 JSON
├── generate_image_v2.py       # DALL-E 3 → 드라마 분위기 이미지
├── make_video_v2.py           # FFmpeg → 10~20초 S급 영상
├── ai_orchestrator_v2.py      # CLI 오케스트레이터
├── get_episode_info_v2.py     # n8n SSH 노드용 메타데이터 출력
└── n8n/
    └── (워크플로우 추후 추가)

episodes_v2/                   # 서버 고유 — git 미포함
└── YYYYMMDD_NNN/
    ├── script_v2.json
    ├── bg1~bgN.jpg
    ├── voice_ko.mp3
    ├── subtitles_v2.ass
    └── output_final.mp4
```

### v1에서 공유하는 파일 (서버 경로)
- `generate_tts.py` — `/root/auto_pipeline/generate_tts.py` import
- `config.py` — `/root/auto_pipeline/config.py` import
- `bgm/` — `/root/auto_pipeline/bgm/` 재사용

---

## 드라마 주제 풀 (topics_drama.json)

| 드라마 | 콘텐츠 타입 | 테마 |
|--------|------------|------|
| 더 글로리 | 명대사 / 복선해석 / 반전요약 | 복수의 무게 |
| 눈물의 여왕 | 명대사 / 복선해석 | 사랑과 이별 |
| 이상한 변호사 우영우 | 명대사 | 다름의 가치 |
| 나의 해방일지 | 명대사 / 반전요약 | 해방의 의미 |
| 스물다섯 스물하나 | 명대사 / 복선해석 | 청춘의 끝 |
| 오징어 게임 | 명대사 / 복선해석 | 돈과 인간 |
| 무빙 | 명대사 / 복선해석 | 부모의 희생 |
| 닥터슬럼프 | 명대사 | 번아웃과 회복 |
| 선재 업고 튀어 | 명대사 / 복선해석 | 시간을 돌린다면 |
| 사랑의 불시착 | 명대사 / 반전요약 | 운명과 사랑 |
| + 20개 추가 | ... | ... |

---

## 실행 명령어

```bash
cd /root/auto_pipeline_v2

# 단일 실행 (자동 주제 선택)
python3 ai_orchestrator_v2.py --batch --count 1 --auto

# 특정 주제 지정
python3 ai_orchestrator_v2.py --topic glory_quote_revenge

# 배치 3편
python3 ai_orchestrator_v2.py --batch --count 3 --auto

# 백그라운드 실행 (n8n용)
setsid python3 -u ai_orchestrator_v2.py --batch --count 1 --auto \
  > /root/auto_pipeline_v2/daily_gen_v2.log 2>&1 </dev/null &
echo "PID=$!"
```

---

## 알고리즘 수치 목표

| 지표 | 목표 | 적용 방법 |
|------|------|---------|
| 완시율 | 85%+ | 10~20초 이내 유지 |
| 좋아요율 | 5%+ | 저장유도 자막 |
| 반복시청 | 발생 | 루프트리거 마지막 장면 |
| 저장 | 발생 | 7~9초 / 18~19초 저장유도 |
| 공유 | 발생 | 감정 충격 장면 |

---

## 주의사항

- DALL-E 이미지 프롬프트: 실제 배우/캐릭터 이름 절대 금지
- 드라마 원본 영상 클립 사용 금지 (Content ID 위험)
- OST 원곡 사용 금지 — BGM은 `/root/auto_pipeline/bgm/` 재사용
- `drama_used.json` — 서버 고유, git push 금지

---

## 마지막 업데이트

2026-05-04 — v2.0 초기 구조 생성
- topics_drama.json: 30개 주제 (명대사 16 / 복선해석 9 / 반전요약 5)
- S급 포맷: 10초(명대사) / 20초(복선해석·반전요약)
- Claude API 전용 (OpenAI 의존 제거)
- DALL-E 드라마 분위기 이미지 (배우 금지)
- 루프트리거 + 저장유도 자막 구조

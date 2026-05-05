# content-pipeline-core — 공통 아키텍처

> 모든 채널 파이프라인의 설계 기준 문서.
> 채널별 코드는 각 폴더에서 관리. 공통 config는 이 폴더의 config.example.py 참조.

---

## 레포 구조

```
claude-code/
├── content-pipeline-core/      ← 공통 아키텍처 기준 (이 폴더)
├── content-mindset/            ← 매일의 설계: 감정·철학·돈·인간관계 (내레이션/인포그래픽/다큐)
├── content-health/             ← 매일의 설계 건강편: 잘못된 건강 상식 뒤집기 (25초 쇼츠)
├── content-economy/            ← (예정) 경제·재테크
└── content-food-travel/        ← (예정) 먹방·여행
```

---

## 채널별 공통 구성 원칙

| 항목 | 위치 |
|------|------|
| API Key / 경로 설정 | `config.example.py` → 서버의 `config.py` |
| 주제 풀 | `topics_*.json` (각 채널 폴더) |
| 채널 브랜딩 | `make_video_*.py` 상단 상수 또는 `channel_config.py` |
| 영상 엔진 | `make_video_*.py` (각 채널 폴더) |
| n8n 워크플로 | 각 채널 폴더의 `n8n/` |

---

## 서버 디렉토리 구조

| 채널 | Git 폴더 | 서버 실행 디렉토리 |
|------|---------|----------------|
| content-mindset | `content-mindset/` | `/root/auto_pipeline/` |
| content-health | `content-health/` | `/root/auto_pipeline_v2/` |

---

## 공통 config.example.py

`content-mindset/config.example.py` 참조. 모든 채널이 동일한 config.py 구조 사용.

---

## 신규 채널 추가 체크리스트

- [ ] `content-{name}/` 폴더 생성
- [ ] `channel_config.py` — 브랜딩 상수 (CHANNEL_NAME, WATERMARK, SLOGAN)
- [ ] `topics_{name}.json` — 주제 풀
- [ ] `generate_script.py` — 채널 포맷에 맞는 Claude 프롬프트
- [ ] `CLAUDE.md` — 채널 문서
- [ ] 서버 디렉토리 `/root/auto_pipeline_{name}/` 생성
- [ ] n8n Git Sync 명령어 업데이트

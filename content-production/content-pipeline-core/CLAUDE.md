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
| **채널 공통 브랜딩** | **`channel_branding.py`** — WATERMARK / CHANNEL_NAME / CHANNEL_HANDLE |
| **좋아요 설계 전략** | **`likes_strategy.md`** — CTA overlay 스펙, Closing 4패턴, Scene6 업그레이드 |
| 영상 엔진 | `make_video_*.py` (각 채널 폴더) |
| n8n 워크플로 | 각 채널 폴더의 `n8n/` |

---

## 서버 디렉토리 구조

| 채널 | 코드 (git) | 런타임 데이터 |
|------|-----------|-------------|
| content-mindset | `/root/claude-code/content-production/content-mindset/` | `/root/content/runtime/mindset/` |
| content-health | `/root/claude-code/content-production/content-health/` | `/root/content/runtime/health/` |

**런타임 데이터 구조 (`/root/content/runtime/{채널}/`)**
```
config.py           ← API Keys (git 미포함)
topics.json         ← 주제 풀 (mindset 전용, 서버 고유)
*_used.json         ← 사용 이력
episodes/           ← 생성된 영상
bgm/                ← BGM 파일 (대용량, git 미포함)
```

---

## 공통 config.example.py

`content-mindset/config.example.py` 참조. 모든 채널이 동일한 config.py 구조 사용.

---

## 공통 인프라 문서 (infra/)

| 파일 | 내용 |
|------|------|
| `infra/n8n_requirements.md` | 서버 환경, n8n Docker 명령어, API Keys, Google Console 설정 |

> 채널별 n8n 워크플로우 가이드는 각 채널 폴더의 `n8n/` 에 위치.
> 양쪽 서버(192.168.0.21 / 7.7.7.254) Docker 명령어는 n8n_requirements.md에 포함.

---

## 신규 채널 추가 체크리스트

- [ ] `content-{name}/` 폴더 생성
- [ ] `channel_branding.py` (pipeline-core) — WATERMARK/CHANNEL_NAME 이미 정의됨, 채널 고유 SLOGAN만 로컬에 정의
- [ ] `topics_{name}.json` — 주제 풀
- [ ] `generate_script.py` — 채널 포맷에 맞는 Claude 프롬프트
- [ ] `CLAUDE.md` — 채널 문서
- [ ] 서버 런타임 디렉토리 `/root/content/runtime/{name}/` 생성
- [ ] n8n Docker 볼륨 `/root/content:/root/content` 마운트 확인

---

## Claude Code 유용한 기능

### 세션 관리
| 커맨드 | 설명 |
|--------|------|
| `/clear` | 컨텍스트 초기화 — 프로젝트 전환 시 사용. 이전 대화 쌓임 방지 |
| `/cost` | 현재 세션 비용 확인 |

**프로젝트 전환 패턴:**
```
/clear
메모리 확인하고 content-health 이어서 작업하자
```

### 작업 재개 (VSCode 종료 / 컴퓨터 재시작 후)
```
메모리 확인하고 [프로젝트명] 이어서 작업하자
```
메모리(MEMORY.md) + 프로젝트 CLAUDE.md + git log 기반으로 컨텍스트 자동 복원.

### 커스텀 슬래시 커맨드
각 채널 CLAUDE.md에 정의하면 `/커맨드명` 으로 반복 작업 자동화 가능.
```markdown
## Custom Commands
/health-meta: 이 주제로 YouTube 제목/설명란/고정댓글 작성. 설명란 꺾쇄괄호 금지.
```

### 병렬 요청
독립적인 작업은 한 번에 묶어서 요청하면 더 빠름.
```
영상 A 제목/설명/댓글이랑, 영상 B 제목/설명/댓글 동시에 알려줘
```

---

## CLAUDE.md + 메모리 + git push 조합 (핵심 패턴)

> 이 3가지 조합이 Claude Code를 단순 AI 채팅이 아닌 **장기 협업 파트너**로 만드는 핵심.
> 대화는 사라져도 프로젝트 상태와 협업 방식은 영구 보존된다.

---

### 1. CLAUDE.md — 프로젝트 두뇌

**역할**: Claude가 새 세션을 시작할 때 가장 먼저 읽는 프로젝트 설명서.
"이 프로젝트가 뭔지, 어떻게 동작하는지, 어떤 규칙이 있는지"를 담는다.

**잘 쓰는 법**:
- 코드 구조·실행 명령어·주의사항을 최신 상태로 유지
- 작업할 때마다 "작업 CLAUDE.md에 반영해줘" → Claude가 자동 업데이트
- 채널/프로젝트마다 독립 CLAUDE.md 유지 (content-health, nebular-orbit 등)

**효과**: 새 세션에서 "CLAUDE.md 읽고 이어서 작업해줘" 한 마디면 전체 컨텍스트 복원.

```
# 예시 CLAUDE.md 구조
- 프로젝트 정체성 (채널명, 목표, 포맷)
- 파일 구조
- 실행 명령어
- 주의사항 (금지 규칙, 알려진 이슈)
- 마지막 업데이트 이력
```

---

### 2. 메모리 — Claude의 장기 기억

**역할**: 프로젝트를 넘어 "나(사용자)에 대한 정보"를 Claude가 기억하는 공간.
대화가 끊겨도, 세션이 바뀌어도 나를 알고 있는 상태로 시작.

**저장 위치**: `/Users/mins/.claude/projects/-Users-mins/memory/`

**메모리 종류**:
| 타입 | 내용 | 예시 |
|------|------|------|
| `user` | 나의 역할·배경·선호 | "콘텐츠 자동화 파이프라인 개발자" |
| `feedback` | 내가 싫어하는/좋아하는 작업 방식 | "코드 수정 후 항상 git push까지 자동 처리" |
| `project` | 현재 진행 중인 프로젝트 현황 | "content-health Hook 순환 작업 중" |
| `reference` | 외부 시스템 위치 | "n8n은 192.168.0.21:5678" |

**잘 쓰는 법**:
- "이거 기억해줘" → 즉시 메모리 파일 생성
- "메모리 확인하고 시작해줘" → 이전 협업 방식 그대로 복원
- Claude가 실수하면 "앞으로 이렇게 해줘" → feedback 메모리로 저장됨

**효과**: 매번 "나는 이런 사람이고, 이렇게 작업하는 걸 좋아해" 설명할 필요 없음.

---

### 3. git push — 작업 결과 영구 보존

**역할**: Claude와 함께 만든 코드·문서를 원격 저장소에 즉시 백업.
컴퓨터가 꺼지거나 VSCode가 종료돼도 작업 내용이 사라지지 않는다.

**잘 쓰는 법**:
- 코드 수정 완료 시 "작업 commit하고 push해줘" 또는 Claude가 자동으로 처리
- CLAUDE.md 업데이트도 항상 push까지 포함
- 커밋 메시지에 작업 내용 요약 → git log가 작업 히스토리가 됨

**효과**: 서버에서 `git pull` 한 번으로 최신 코드 즉시 반영.

---

### 세 가지가 합쳐지면

```
[새 세션 시작]
    ↓
메모리 로드 → "이 사용자는 어떤 사람인지, 어떤 방식을 선호하는지" 파악
    ↓
CLAUDE.md 로드 → "이 프로젝트는 뭔지, 현재 상태는 어떤지" 파악
    ↓
git log 확인 → "마지막으로 뭘 했는지" 파악
    ↓
아무 설명 없이 바로 이어서 작업 가능
```

**한 줄 요약**: CLAUDE.md는 프로젝트 기억, 메모리는 사람 기억, git은 코드 기억.
셋이 합쳐지면 세션이 끊겨도 협업이 끊기지 않는다.

---

## 마지막 업데이트

2026-05-05 — likes_strategy.md 추가 + 좋아요 설계 전략 공통화
- likes_strategy.md 신규: CTA overlay 스펙 (`#FFD700`, 36px, 마지막 1.2초), Closing 4패턴 규칙 (공감형/저장형/승리감형/공유형), Scene6 좋아요+저장 동시 유도 근거 문서화
- 적용 채널: content-mindset (make_video.py, make_video_stock.py, generate_script.py), content-health (make_video_v2.py, generate_script_v2.py)

2026-05-05 — channel_branding.py 추가 + 공통 모듈 구조 확정
- channel_branding.py 신규: WATERMARK="© 2026 매일의 설계", CHANNEL_NAME, CHANNEL_HANDLE
- 모든 채널이 from channel_branding import WATERMARK 로 단일 출처 사용
- ffmpeg_utils.py / audio_core.py / video_core.py: content-health 검증 완료

2026-05-05 — 런타임 경로 분리 아키텍처 확정
- auto_pipeline, auto_pipeline_v2 의존성 완전 제거
- 코드: git repo에서 직접 실행 (`/root/claude-code/content-production/{채널}/`)
- 런타임 데이터: `/root/content/runtime/{채널}/` (config.py, used.json, episodes/, bgm/)
- n8n Docker 볼륨: `/root/auto_pipeline` 제거 → `/root/content`, `/root/claude-code` 추가
- infra 문서: content-mindset/n8n/ → content-pipeline-core/infra/ 로 이동
- n8n_workflow_daily_auto.json: Git Sync cp 제거, 전체 SSH 노드 경로 업데이트

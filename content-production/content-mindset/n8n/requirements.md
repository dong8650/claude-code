# 컨텐츠 자동화 파이프라인 — 환경 요구사항

> 이 파일을 읽으면 로컬/서버 환경을 즉시 파악 가능.
> 마지막 업데이트: 2026-05-03

---

## 서버 환경

| 항목 | 내용 |
|------|------|
| 메인 서버 IP | 192.168.0.21 |
| OS | Ubuntu 24.04 aarch64 (ARM) |
| 작업 디렉토리 | `/root/auto_pipeline/` |
| Python | 3.10 |
| 폰트 | NotoSansCJK-Bold.ttc (`/usr/share/fonts/opentype/noto/`) |

### 서버 필수 패키지
```bash
pip install anthropic openai requests pillow elevenlabs
apt install ffmpeg
```

---

## n8n 환경

| 항목 | 내용 |
|------|------|
| 버전 | 2.10.3 |
| 설치 방식 | Docker |
| 접속 URL | http://toss.fortiddns.com:8084 |
| 외부 접속 URL | http://kdclab.kr:8084 |
| Instance ID | fa16be5da17e330f0aa1b69589bacc58b212188d69021f2f9b3d4dee548c7a94 |
| OAuth Callback URL | http://toss.fortiddns.com:8084/rest/oauth2-credential/callback |

### n8n Docker 실행 명령어 (최종 확정)

```bash
docker run -d \
  --name n8n \
  --privileged \
  --user root \
  -p 8080:8080 \
  -e N8N_PORT=8080 \
  -e N8N_SECURE_COOKIE=false \
  -e N8N_HOST=kdclab.kr \
  -e N8N_PROTOCOL=http \
  -e WEBHOOK_URL=http://kdclab.kr:8084/ \
  -e GENERIC_TIMEZONE=Asia/Seoul \
  -e TZ=Asia/Seoul \
  -e N8N_RESTRICT_FILE_ACCESS_TO=/root \
  -v /root/.n8n:/root/.n8n \
  -v /root/auto_pipeline:/root/auto_pipeline \
  --restart always \
  n8nio/n8n
```

> **`--privileged` 필수 이유**: n8n Docker Hardened Image(DHI)는 seccomp + AppArmor 보안 프로파일을 동시에 적용함.
> `--security-opt seccomp=unconfined`만으로는 AppArmor 제한이 남아 포트 바인딩 실패.
> `--privileged`는 모든 보안 제한(seccomp + AppArmor + Capabilities)을 한번에 해제.

### n8n Docker 관리 명령어

```bash
# 컨테이너 확인
docker ps | grep n8n

# 재시작 (설정 변경 없이)
docker restart n8n

# 로그 확인
docker logs n8n --tail 50

# 재설치 (설정 변경 시)
docker stop n8n && docker rm n8n
# → 위의 "최종 확정" 명령어로 재시작

# 초기화 (문제 발생 시)
docker stop n8n && docker rm n8n
rm -rf /root/.n8n
mkdir /root/.n8n && chmod 777 /root/.n8n
# → 위의 "최종 확정" 명령어로 재시작
```

---

## Google Cloud Console 설정

| 항목 | 내용 |
|------|------|
| 프로젝트 | n8n-workflow |
| OAuth 클라이언트 | n8n-pipeline (YouTube용) |
| OAuth 클라이언트 | n8n-google-sheets (Google Sheets용) |
| 활성화된 API | YouTube Data API v3 |
| 테스트 사용자 | dong8650@gmail.com |

### 승인된 리디렉션 URI (등록 완료)
```
http://kdclab.kr:8084/rest/oauth2-credential/callback
http://toss.fortiddns.com:8084/rest/oauth2-credential/callback
```

---

## n8n Credentials 목록

| 이름 | 타입 | 용도 |
|------|------|------|
| YouTube account | YouTube OAuth2 API | 영상 업로드 |
| Slack account | Slack API | 업로드 알림 (미설정) |

---

## n8n 워크플로우 목록

| 파일 | 워크플로우명 | 상태 |
|------|------------|------|
| `n8n_workflow_youtube_upload.json` | YouTube Auto-Upload | 설정 중 |

---

## API Keys (서버 config.py에만 존재)

| 서비스 | 변수명 | 비고 |
|--------|--------|------|
| Anthropic | `CLAUDE_API_KEY` | Claude Sonnet 사용 |
| OpenAI | `OPENAI_API_KEY` | GPT-4o 사용 |
| ElevenLabs | `ELEVENLABS_API_KEY` | Seulki 보이스 |
| Pixabay | `PIXABAY_API_KEY` | 이미지 검색 |
| Pexels | `PEXELS_API_KEY` | 스톡 영상 |

---

## config.py 추가 설정 필요 항목

```python
N8N_WEBHOOK_URL = "http://toss.fortiddns.com:8084/webhook/youtube-upload"
```

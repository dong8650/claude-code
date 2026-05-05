# Legacy File Report — /root/auto_pipeline

생성일: 2026-05-01

## 판정 기준

메인 플로우: `ai_orchestrator.py` → `generate_script.py` → `generate_image.py` → `generate_tts.py` → `make_video.py`

---

## 레거시 후보 파일 분석

| 파일 | 크기 | 판정 | 이유 |
|------|------|------|------|
| `1_generate_script.py` | 1,966B | **LEGACY** | 구 Claude 단독 대본 생성. GPT→Claude 구조 이전 버전. |
| `2_download_videos.py` | 1,607B | **LEGACY** | Pixabay/Pexels 영상 다운로드. DALL-E 이미지로 대체됨. |
| `3_generate_tts.py` | 982B | **LEGACY** | 구 TTS 스크립트 (최소 버전). `generate_tts.py`로 대체됨. |
| `4_make_video.py` | 5,042B | **LEGACY** | 구 영상 합성 스크립트. `make_video.py`로 대체됨. |
| `download_videos.py` | 2,107B | **LEGACY** | Pexels/Pixabay 다운로드. DALL-E로 대체됨. |
| `generate_script_20260412.py` | 9,165B | **LEGACY** | 날짜 명시된 구 버전. `generate_script.py`로 대체됨. |
| `generate_scripts_only.py` | 5,687B | **LEGACY** | 구 배치 대본 생성기. 고정 EPISODES 리스트 기반. 현재 `ai_orchestrator.py --batch --script-only`로 대체. |
| `generate_hook_variants.py` | 2,011B | **보류** | Hook 변형 생성 유틸. 현재 메인 플로우에 미포함. 향후 A/B 테스트용으로 활용 가능. |
| `record_metrics.py` | 2,441B | **보류** | 조회수/완주율/좋아요 수동 기록 유틸. 메인 플로우 외부 도구. 사용 여부 사용자 판단. |
| `rerender.py` | 6,332B | **보류** | 기존 에피소드 재렌더링. Whisper 의존. 메인 플로우 외부 도구. |
| `run_all.py` | 3,817B | **LEGACY** | 구 배치 실행기. 고정 EPISODES 리스트 + orchestrate 함수 (현재 없음). `ai_orchestrator.py --batch`로 완전 대체. |

---

## 권장 조치

### 즉시 legacy/ 이동 대상 (7개)
```
1_generate_script.py
2_download_videos.py
3_generate_tts.py
4_make_video.py
download_videos.py
generate_script_20260412.py
generate_scripts_only.py
run_all.py
```

### 보류 (사용자 판단 필요, 3개)
```
generate_hook_variants.py  — A/B 테스트 시 활용 가능
record_metrics.py          — 수동 성과 기록 도구
rerender.py                — 개별 에피소드 재렌더링 도구
```

---

## 이동 명령 (서버 실행)

```bash
mkdir -p /root/auto_pipeline/legacy
mv /root/auto_pipeline/1_generate_script.py \
   /root/auto_pipeline/2_download_videos.py \
   /root/auto_pipeline/3_generate_tts.py \
   /root/auto_pipeline/4_make_video.py \
   /root/auto_pipeline/download_videos.py \
   /root/auto_pipeline/generate_script_20260412.py \
   /root/auto_pipeline/generate_scripts_only.py \
   /root/auto_pipeline/run_all.py \
   /root/auto_pipeline/legacy/
```

승인 후 실행. 삭제하지 않음.

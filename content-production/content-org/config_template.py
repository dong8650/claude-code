# config_template.py
# ==================
# 서버 배포 시 /root/content/runtime/{CHANNEL_ID}/config.py 로 복사 후 수정
# git에 절대 커밋하지 말 것 — API keys 포함

# ── API Keys ───────────────────────────────────────────────
CLAUDE_API_KEY = "sk-ant-..."
FAL_API_KEY    = "..."

# ── 채널 식별자 ─────────────────────────────────────────────
# TODO: 채널명으로 변경 (예: "saying", "history", "stoic")
CHANNEL_ID = "org"

# ── 런타임 경로 ─────────────────────────────────────────────
RUNTIME_DIR  = f"/root/content/runtime/{CHANNEL_ID}"
EPISODES_DIR = f"{RUNTIME_DIR}/episodes"

# ── 공유 자산 ───────────────────────────────────────────────
# BGM: mindset 채널과 공유 사용 (별도 파일 없으면 아래 경로 그대로)
BGM_PATH  = "/root/content/runtime/mindset/bgm/bgm_dark_cinematic.mp3"

# 폰트: 서버 공통 경로
FONT_PATH = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"

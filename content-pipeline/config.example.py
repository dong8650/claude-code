# config.py 예시 — 실제 키는 서버의 config.py에만 존재
# 이 파일은 secrets 제외 버전으로 Git 관리

PIXABAY_API_KEY         = "YOUR_PIXABAY_API_KEY"
CLAUDE_API_KEY          = "YOUR_ANTHROPIC_API_KEY"
ELEVENLABS_API_KEY      = "YOUR_ELEVENLABS_API_KEY"
OPENAI_API_KEY          = "YOUR_OPENAI_API_KEY"
PEXELS_API_KEY          = "YOUR_PEXELS_API_KEY"

# ElevenLabs Seulki Voice ID
VOICE_ID                = "ksaI0TCD9BstzEzlxj4q"
ELEVENLABS_SEULKI_VOICE_ID = "ksaI0TCD9BstzEzlxj4q"

# 영상 설정
VIDEO_WIDTH  = 1080
VIDEO_HEIGHT = 1920
FPS          = 25
BGM_VOLUME   = 0.12
FONT_PATH    = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
WATERMARK    = "© 2026 매일의 설계"
BGM_PATH     = "/root/auto_pipeline/bgm/bgm_philosophy.mp3"
ENDING_PATH  = "/root/auto_pipeline/bgm/ending_card_text.mp4"

BGM_MAP = {
    "docsul": "/root/auto_pipeline/bgm/bgm_dark_cinematic.mp3",
    "janas":  "/root/auto_pipeline/bgm/bgm_dramatic_ambient.mp3",
    "list":   "/root/auto_pipeline/bgm/bgm_philosophy.mp3",
}

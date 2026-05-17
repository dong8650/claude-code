"""
generate_tts.py
===============
Edge TTS docsul (ko-KR-HyunsuNeural)
3분할: intro / quote / echo
명언 파트 -15% — 극적 무게감
voice_ko.mp3 기존 존재 시 skip
"""
import asyncio
import re
import subprocess
import sys
from pathlib import Path

import edge_tts

sys.path.insert(0, "/root/content/runtime/saying")
from config import RUNTIME_DIR

VOICE = "ko-KR-HyunsuNeural"
RATE  = {"intro": "-5%", "quote": "-25%", "echo": "-10%"}
VOLUME = "+2%"


def _strip_emoji(text: str) -> str:
    """이모지·특수문자 제거 — TTS 오류 방지."""
    return re.sub(
        r'[^가-힣ᄀ-ᇿa-zA-Z0-9\s←-⇿!?.,\'"·/():~%\+\-\*\^]',
        '', text
    ).strip()


async def _tts(text: str, path: str, rate: str):
    comm = edge_tts.Communicate(text, VOICE, rate=rate, volume=VOLUME)
    await comm.save(path)


def _duration(path: str) -> float:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        capture_output=True, text=True
    )
    try:
        return float(r.stdout.strip())
    except Exception:
        return 0.0


def generate_tts(script: dict, ep_dir: str) -> dict:
    ep = Path(ep_dir)
    ep.mkdir(parents=True, exist_ok=True)

    intro_path  = str(ep / "tts_intro.mp3")
    quote_path  = str(ep / "tts_quote.mp3")
    echo_path   = str(ep / "tts_echo.mp3")
    sil_path    = str(ep / "sil.mp3")
    concat_file = str(ep / "tts_concat.txt")
    voice_path  = str(ep / "voice_ko.mp3")

    # ⑥ TTS skip 로직 — 모두 있으면 재생성 안 함
    parts_exist = all(
        Path(p).exists() for p in [intro_path, quote_path, echo_path, voice_path]
    )
    if parts_exist:
        intro_dur = _duration(intro_path)
        quote_dur = _duration(quote_path)
        echo_dur  = _duration(echo_path)
        total_dur = intro_dur + 0.5 + quote_dur + echo_dur
        print(f"  ✅ TTS skip (기존): {total_dur:.1f}초")
        return {
            "intro_dur":  intro_dur,
            "quote_dur":  quote_dur,
            "echo_dur":   echo_dur,
            "total_dur":  total_dur,
            "voice_path": voice_path,
        }

    print(f"  🎙️ TTS 생성 중...")

    # ⑦ 이모지 제거 후 TTS
    asyncio.run(_tts(_strip_emoji(script["intro_ko"]), intro_path, RATE["intro"]))
    asyncio.run(_tts(_strip_emoji(script["quote_ko"]), quote_path, RATE["quote"]))
    asyncio.run(_tts(_strip_emoji(script["echo_ko"]),  echo_path,  RATE["echo"]))

    intro_dur = _duration(intro_path)
    quote_dur = _duration(quote_path)
    echo_dur  = _duration(echo_path)

    # intro 뒤 0.5초 무음 — 명언 시작 전 호흡
    subprocess.run([
        "ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
        "-t", "0.5", "-q:a", "9", "-acodec", "libmp3lame", sil_path
    ], capture_output=True)

    with open(concat_file, "w") as f:
        for p in [intro_path, sil_path, quote_path, echo_path]:
            f.write(f"file '{p}'\n")

    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", concat_file, "-acodec", "copy", voice_path
    ], capture_output=True)

    total_dur = intro_dur + 0.5 + quote_dur + echo_dur
    print(f"  📊 intro:{intro_dur:.1f}s  quote:{quote_dur:.1f}s  echo:{echo_dur:.1f}s  총:{total_dur:.1f}s")
    print(f"  ✅ TTS 완료: {voice_path}")

    return {
        "intro_dur":  intro_dur,
        "quote_dur":  quote_dur,
        "echo_dur":   echo_dur,
        "total_dur":  total_dur,
        "voice_path": voice_path,
    }

"""
generate_tts.py
===============
Edge TTS docsul (ko-KR-HyunsuNeural)
3분할: intro / quote / echo
명언 파트는 더 느리게 (-15%) — 극적 효과
"""
import asyncio
import os
import subprocess
import sys
from pathlib import Path

import edge_tts

VOICE = "ko-KR-HyunsuNeural"

RATE = {
    "intro": "-5%",
    "quote": "-15%",   # 명언 — 가장 느리게, 무게감
    "echo":  "-8%",
}
VOLUME = "+2%"


async def _tts(text: str, path: str, rate: str):
    comm = edge_tts.Communicate(text, VOICE, rate=rate, volume=VOLUME)
    await comm.save(path)


def _duration(path: str) -> float:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        capture_output=True, text=True
    )
    return float(r.stdout.strip())


def generate_tts(script: dict, ep_dir: str) -> dict:
    ep = Path(ep_dir)
    ep.mkdir(parents=True, exist_ok=True)

    intro_path  = str(ep / "tts_intro.mp3")
    quote_path  = str(ep / "tts_quote.mp3")
    echo_path   = str(ep / "tts_echo.mp3")
    voice_path  = str(ep / "voice_ko.mp3")
    concat_file = str(ep / "tts_concat.txt")

    print(f"  🎙️ TTS 생성 중...")
    asyncio.run(_tts(script["intro_ko"], intro_path, RATE["intro"]))
    asyncio.run(_tts(script["quote_ko"], quote_path, RATE["quote"]))
    asyncio.run(_tts(script["echo_ko"],  echo_path,  RATE["echo"]))

    intro_dur = _duration(intro_path)
    quote_dur = _duration(quote_path)
    echo_dur  = _duration(echo_path)
    total_dur = intro_dur + quote_dur + echo_dur

    # 0.5초 무음 — intro 뒤에 호흡
    sil_path = str(ep / "sil.mp3")
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

    total_dur += 0.5
    print(f"  📊 intro:{intro_dur:.1f}s  quote:{quote_dur:.1f}s  echo:{echo_dur:.1f}s  총:{total_dur:.1f}s")
    print(f"  ✅ TTS 완료: {voice_path}")

    return {
        "intro_dur":  intro_dur,
        "quote_dur":  quote_dur,
        "echo_dur":   echo_dur,
        "total_dur":  total_dur,
        "voice_path": voice_path,
    }

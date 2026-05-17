"""
generate_tts.py
===============
Edge TTS (ko-KR-HyunsuNeural)
3분할: intro / quote / echo
quote는 문장별 개별 TTS → sentence_durs 반환 (자막 싱크용)
voice_ko.mp3 기존 존재 시 skip
"""
import asyncio
import json
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


def _split_sentences(text: str) -> list:
    """문장 단위 분리 (마침표/느낌표/물음표 기준)."""
    parts = re.split(r'(?<=[.!?])\s+', text.strip())
    return [s.strip() for s in parts if s.strip()]


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
    sent_durs_file = ep / "tts_sentence_durs.json"

    # ⑥ TTS skip 로직 — 모두 있으면 재생성 안 함
    parts_exist = all(
        Path(p).exists() for p in [intro_path, quote_path, echo_path, voice_path]
    )
    if parts_exist:
        intro_dur = _duration(intro_path)
        quote_dur = _duration(quote_path)
        echo_dur  = _duration(echo_path)
        total_dur = intro_dur + 0.5 + quote_dur + echo_dur
        sentence_durs = json.loads(sent_durs_file.read_text()) if sent_durs_file.exists() else None
        print(f"  ✅ TTS skip (기존): {total_dur:.1f}초")
        return {
            "intro_dur":     intro_dur,
            "quote_dur":     quote_dur,
            "echo_dur":      echo_dur,
            "total_dur":     total_dur,
            "voice_path":    voice_path,
            "sentence_durs": sentence_durs,
        }

    print(f"  🎙️ TTS 생성 중...")

    asyncio.run(_tts(_strip_emoji(script["intro_ko"]), intro_path, RATE["intro"]))
    asyncio.run(_tts(_strip_emoji(script["echo_ko"]),  echo_path,  RATE["echo"]))

    # quote — 문장별 개별 TTS 생성 → 각 문장 길이 측정 후 연결
    quote_stripped = _strip_emoji(script["quote_ko"])
    sentences = _split_sentences(quote_stripped) or [quote_stripped]

    sent_paths, sentence_durs = [], []
    for idx, sent in enumerate(sentences):
        sp = str(ep / f"tts_q{idx}.mp3")
        asyncio.run(_tts(sent, sp, RATE["quote"]))
        sent_paths.append(sp)
        sentence_durs.append(_duration(sp))

    # 문장별 mp3 → tts_quote.mp3 연결
    concat_quote = str(ep / "tts_concat_quote.txt")
    with open(concat_quote, "w") as f:
        for sp in sent_paths:
            f.write(f"file '{sp}'\n")
    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", concat_quote, "-acodec", "copy", quote_path
    ], capture_output=True)

    sent_durs_file.write_text(json.dumps(sentence_durs))

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
    print(f"       문장별: {[f'{d:.1f}s' for d in sentence_durs]}")
    print(f"  ✅ TTS 완료: {voice_path}")

    return {
        "intro_dur":     intro_dur,
        "quote_dur":     quote_dur,
        "echo_dur":      echo_dur,
        "total_dur":     total_dur,
        "voice_path":    voice_path,
        "sentence_durs": sentence_durs,
    }

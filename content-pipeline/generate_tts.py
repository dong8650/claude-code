import asyncio
import edge_tts
import json
import os
import re
import subprocess
import requests

# ElevenLabs 설정
try:
    from config import ELEVENLABS_API_KEY, ELEVENLABS_SEULKI_VOICE_ID
    ELEVENLABS_AVAILABLE = True
except ImportError:
    ELEVENLABS_AVAILABLE = False

VOICE_MAP = {
    "docsul":  "ko-KR-HyunsuNeural",
    "janas":   "ko-KR-SunHiNeural",
    "list":    "ko-KR-SunHiNeural",
    "seulki":  "elevenlabs",
    "default": "ko-KR-HyunsuNeural",
}

INTRO_DURATION = 1.5

def get_duration(path: str) -> float:
    r = subprocess.run([
        "ffprobe", "-i", path,
        "-show_entries", "format=duration",
        "-v", "quiet", "-of", "csv=p=0"
    ], capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except:
        return 0.0

def make_silence(path: str, duration: float):
    subprocess.run([
        "ffmpeg", "-y", "-f", "lavfi",
        "-i", "anullsrc=r=44100:cl=stereo",
        "-t", str(duration), "-q:a", "9",
        "-acodec", "libmp3lame", path
    ], capture_output=True)

def split_script(script: dict) -> dict:
    """
    의미 기준 고정 분리:
    - hook_text    = script["hook"] 그대로 (1문장)
    - body_text    = script_ko에서 hook 제거 후 전체 (사례+철학자+해석)
    - closing_text = closing_ko 1문장만
    철학자 인용문/사례는 반드시 body에 포함
    """
    hook_text  = script.get("hook", "").strip()
    full       = script.get("script_ko", "").strip()
    closing_ko = script.get("closing_ko", "").strip()

    # script_ko 줄 단위로 분리
    lines = [l.strip() for l in full.split("\n") if l.strip()]

    # hook 중복 제거: 첫 줄이 hook과 동일하거나 포함되면 제거
    if lines and (lines[0] == hook_text or hook_text in lines[0]):
        lines = lines[1:]

    # body = script_ko 전체 (hook 제거 후)
    # closing = closing_ko 1문장만 (본문 잘라내기 금지)
    body_text    = "\n".join(lines)
    closing_text = closing_ko if closing_ko else (lines[-1] if lines else "")

    # closing이 body와 중복되면 body에서 제거
    if closing_ko and lines and lines[-1] in closing_ko:
        body_text = "\n".join(lines[:-1])

    return {
        "hook":    hook_text,
        "body":    body_text,
        "closing": closing_text,
    }

def split_to_subtitle_lines(text: str, max_lines: int = 4) -> list:
    parts = re.split(r'(?<=[,!?.。])\s*|\n+', text.strip())
    lines = [p.strip() for p in parts if p.strip()]
    while len(lines) > max_lines:
        idx = min(range(len(lines) - 1), key=lambda i: len(lines[i]) + len(lines[i+1]))
        lines[idx] = lines[idx] + " " + lines[idx + 1]
        lines.pop(idx + 1)
    return lines

def assign_durations_by_chars(lines: list, total_duration: float) -> list:
    char_counts = [max(len(l), 1) for l in lines]
    total_chars = sum(char_counts)
    return [total_duration * (c / total_chars) for c in char_counts]

def make_kf_line(text: str, total_dur: float) -> str:
    words = text.split()
    if not words:
        return text
    char_counts = [max(len(w), 1) for w in words]
    total_chars = sum(char_counts)
    result = []
    for w, c in zip(words, char_counts):
        kf = int(total_dur * (c / total_chars) * 100)
        result.append(f"{{\\kf{kf}}}{w}")
    return " ".join(result)

def _tts_elevenlabs(text: str, path: str):
    """ElevenLabs Seulki 음성 생성"""
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_SEULKI_VOICE_ID}"
    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json"
    }
    body = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75,
            "style": 0.3,
            "use_speaker_boost": True
        }
    }
    r = requests.post(url, headers=headers, json=body)
    if r.status_code == 200:
        with open(path, "wb") as f:
            f.write(r.content)
    else:
        raise Exception(f"ElevenLabs 오류: {r.status_code} {r.text}")

async def _tts(text: str, path: str, voice: str, rate: str, volume: str):
    communicate = edge_tts.Communicate(text, voice, rate=rate, volume=volume)
    await communicate.save(path)

def generate_tts(text_or_script, output_path: str, voice=None, style="default"):
    output_dir = os.path.dirname(os.path.abspath(output_path))
    selected_voice = VOICE_MAP.get(style, VOICE_MAP["default"])
    script = text_or_script if isinstance(text_or_script, dict) else {"script_ko": text_or_script}

    # 1. 의미 기준 3분할
    parts = split_script(script)
    print(f"  📋 hook    ({len(parts['hook'])}자): {parts['hook'][:30]}...")
    print(f"  📋 body    ({len(parts['body'])}자): {parts['body'][:30]}...")
    print(f"  📋 closing ({len(parts['closing'])}자): {parts['closing'][:30]}...")

    hook_path    = os.path.join(output_dir, "tts_hook.mp3")
    body_path    = os.path.join(output_dir, "tts_body.mp3")
    closing_path = os.path.join(output_dir, "tts_closing.mp3")

    print("  🎙️ TTS 3분할 생성 중... (원문: script_ko 기준)")
    if selected_voice == "elevenlabs":
        print("  🎤 ElevenLabs Seulki 음성 사용")
        _tts_elevenlabs(parts["hook"],    hook_path)
    else:
        asyncio.run(_tts(parts["hook"],    hook_path,    selected_voice, "-8%", "+2%"))
    if selected_voice == "elevenlabs":
        _tts_elevenlabs(parts["body"],    body_path)
    else:
        asyncio.run(_tts(parts["body"],    body_path,    selected_voice, "+3%", "+0%"))
    if selected_voice == "elevenlabs":
        _tts_elevenlabs(parts["closing"], closing_path)
    else:
        asyncio.run(_tts(parts["closing"], closing_path, selected_voice, "-5%", "+0%"))

    # 2. 실제 길이 측정
    hook_dur    = get_duration(hook_path)
    body_dur    = get_duration(body_path)
    closing_dur = get_duration(closing_path)
    print(f"  📊 hook:{hook_dur:.2f}초 body:{body_dur:.2f}초 closing:{closing_dur:.2f}초")

    # 3. concat (무음 포함)
    s02 = os.path.join(output_dir, "sil_02.mp3")
    s03 = os.path.join(output_dir, "sil_03.mp3")
    make_silence(s02, 0.2)
    make_silence(s03, 0.3)

    concat = os.path.join(output_dir, "tts_concat.txt")
    with open(concat, "w") as f:
        f.write(f"file '{hook_path}'\n")
        f.write(f"file '{s03}'\n")
        f.write(f"file '{body_path}'\n")
        f.write(f"file '{s02}'\n")
        f.write(f"file '{closing_path}'\n")

    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", concat, "-c", "copy", output_path
    ], capture_output=True)

    total_dur = get_duration(output_path)
    print(f"✅ TTS 완료: {output_path} ({total_dur:.2f}초)")

    # 4. 자막 생성 (글자 수 비례 + 단어별 kf)
    hook_lines    = split_to_subtitle_lines(parts["hook"],    max_lines=2)
    body_lines    = split_to_subtitle_lines(parts["body"],    max_lines=8)
    closing_lines = split_to_subtitle_lines(parts["closing"], max_lines=2)

    hook_durs    = assign_durations_by_chars(hook_lines,    hook_dur)
    body_durs    = assign_durations_by_chars(body_lines,    body_dur)
    closing_durs = assign_durations_by_chars(closing_lines, closing_dur)

    timeline = []
    cursor   = 0.0

    def add_lines(lines, durs, cur):
        for line, dur in zip(lines, durs):
            timeline.append({
                "text":     line,
                "start":    round(cur, 3),
                "end":      round(cur + dur, 3),
                "duration": round(dur, 3),
            })
            cur += dur
        return cur

    cursor = add_lines(hook_lines,    hook_durs,    cursor)
    cursor += 0.3
    cursor = add_lines(body_lines,    body_durs,    cursor)
    cursor += 0.2
    cursor = add_lines(closing_lines, closing_durs, cursor)

    print(f"  📝 자막 {len(timeline)}줄 생성")

    # 5. ASS 생성
    ass_path = os.path.join(output_dir, "subtitles_tts.ass")
    _build_ass(timeline, ass_path)
    print(f"  ✅ 자막 완료 (단어별 노래방 효과 + 오탈자 0%)")

    # segments.json
    seg_json = os.path.join(output_dir, "segments.json")
    with open(seg_json, "w", encoding="utf-8") as f:
        json.dump({
            "intro_duration": INTRO_DURATION,
            "total_duration": total_dur + INTRO_DURATION,
            "voice_duration": total_dur,
        }, f, ensure_ascii=False, indent=2)

    return ass_path

def _build_ass(timeline: list, output_path: str):
    header  = "[Script Info]\n"
    header += "ScriptType: v4.00+\n"
    header += "PlayResX: 1080\n"
    header += "PlayResY: 1920\n"
    header += "Collisions: Normal\n\n"
    header += "[V4+ Styles]\n"
    header += "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
    header += "Style: Karaoke,NotoSansCJK-Bold,58,&H0000FFFF,&H00FFFFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,3,0,2,60,60,480,1\n\n"
    header += "[Events]\n"
    header += "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"

    def to_ass(secs: float) -> str:
        h = int(secs // 3600)
        m = int((secs % 3600) // 60)
        s = secs % 60
        return f"{h}:{m:02d}:{s:05.2f}"

    lines = []
    for seg in timeline:
        kf_text = make_kf_line(seg["text"], seg["duration"])
        lines.append(
            f"Dialogue: 0,{to_ass(seg['start'])},{to_ass(seg['end'])},Karaoke,,0,0,0,,{kf_text}"
        )

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(header)
        f.write("\n".join(lines))

if __name__ == "__main__":
    with open("script.json", encoding="utf-8") as f:
        script = json.load(f)
    generate_tts(script, "voice_ko.mp3")

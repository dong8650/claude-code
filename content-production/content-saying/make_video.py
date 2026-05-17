"""
make_video.py
=============
content-saying 영상 합성
pipeline-core 공통 모듈 사용 (video_core / audio_core / ffmpeg_utils)

① pipeline-core 공통 모듈
② portrait_safe Ken Burns
③ 상단 바 2줄 (철학자 흰색 / 책 오렌지)
④ 하단 바 2줄 (WATERMARK + SLOGAN)
⑤ 자막 3종 스타일 (Intro 크림 / Quote 흰색 대형 / Echo 오렌지)
⑥ TTS skip (voice_ko.mp3 있으면 재생성 안 함 — generate_tts.py 처리)
⑦ 이모지 제거 (generate_tts.py 처리)
⑧ BGM 페이드아웃 (끝 2초 전 자동)
⑨ 자막 싱크: sentence_durs 기반 문장별 비례 배분
"""
import re
import subprocess
import sys
from pathlib import Path

# ① pipeline-core 공통 모듈
_CORE = Path(__file__).parent.parent / "content-pipeline-core"
sys.path.insert(0, str(_CORE))
from ffmpeg_utils import get_duration, run_cmd
from video_core import make_ken_burns_clip, concat_clips, assemble_video
from channel_branding import WATERMARK

import sys as _sys
_sys.path.insert(0, "/root/content/runtime/saying")
from config import BGM_PATH, FONT_PATH

SLOGAN        = "매일, 철학이 말을 걸다"
TOP_BAR_RATIO = 0.22   # mindset과 동일
BOT_BAR_RATIO = 0.22   # mindset과 동일

W, H = 1080, 1920


# ⑦ 이모지 제거 (자막용)
def _strip_emoji(text: str) -> str:
    return re.sub(
        r'[^가-힣ᄀ-ᇿa-zA-Z0-9\s←-⇿!?.,\'"·/():~%\+\-\*\^]',
        '', text
    ).strip()


def _kf_line(text: str, dur_cs: int) -> str:
    """단어별 \kf 카라오케 태그 삽입."""
    words = text.split()
    if not words:
        return text
    per_word = max(10, dur_cs // len(words))
    return " ".join(f"{{\\kf{per_word}}}{w}" for w in words)


def _chunk_quote(text: str, max_chars: int = 22) -> list:
    """명언을 자막 줄 단위로 분할 — 문장 경계 우선, 글자수 보조."""
    import re
    # 1단계: 문장 단위 분리 (마침표/느낌표/물음표 뒤)
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    sentences = [s.strip() for s in sentences if s.strip()]

    chunks = []
    for sentence in sentences:
        if len(sentence) <= max_chars:
            chunks.append(sentence)
        else:
            # 2단계: 긴 문장은 공백 기준으로 추가 분할
            while len(sentence) > max_chars:
                split_at = max_chars
                for i in range(min(max_chars + 5, len(sentence)) - 1, max_chars // 2, -1):
                    if sentence[i] == ' ':
                        split_at = i
                        break
                chunks.append(sentence[:split_at].strip())
                sentence = sentence[split_at:].strip()
            if sentence:
                chunks.append(sentence)
    return [c for c in chunks if c]


def _ts(sec: float) -> str:
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = sec % 60
    return f"{h}:{m:02d}:{s:05.2f}"


# ⑤ 자막 3종 스타일
def build_ass(script: dict, ep_dir: Path, durations: dict) -> Path:
    top_bar_h = int(H * TOP_BAR_RATIO)
    bot_bar_h = int(H * BOT_BAR_RATIO)
    content_h = H - top_bar_h - bot_bar_h
    mid_y     = top_bar_h + content_h // 2

    fs_intro, fs_quote, fs_echo = 56, 64, 58

    intro_dur = durations["intro_dur"] + 0.5
    quote_dur = durations["quote_dur"]
    echo_dur  = durations["echo_dur"]

    t0_intro = 0.0
    t0_quote = intro_dur
    t0_echo  = t0_quote + quote_dur

    intro_text = _strip_emoji(script["intro_ko"])
    quote_text = _strip_emoji(script["quote_ko"])
    echo_text  = _strip_emoji(script["echo_ko"])

    lines = [
        "[Script Info]",
        "ScriptType: v4.00+",
        f"PlayResX: {W}",
        f"PlayResY: {H}",
        "Collisions: Normal",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, "
        "BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, "
        "BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        # Intro — 크림색, 하단
        f"Style: Intro,NotoSansCJK-Bold,{fs_intro},&H00C8E6F5,&H000000FF,&H00000000,&HAA000000,"
        f"-1,0,0,0,100,100,2,0,3,3,2,2,60,60,{bot_bar_h + 40},1",
        # Quote — 흰색, 하단 배치 (alignment=2)
        f"Style: Quote,NotoSansCJK-Bold,{fs_quote},&H00FFFFFF,&H000000FF,&H00000000,&HAA000000,"
        f"-1,0,0,0,100,100,1,0,3,3,2,2,80,80,{bot_bar_h + 40},1",
        # Echo — 오렌지, 하단
        f"Style: Echo,NotoSansCJK-Bold,{fs_echo},&H00008CFF,&H000000FF,&H00000000,&HAA000000,"
        f"-1,0,0,0,100,100,2,0,3,3,2,2,60,60,{bot_bar_h + 40},1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
        f"Dialogue: 0,{_ts(t0_intro)},{_ts(t0_quote - 0.05)},Intro,,0,0,0,,{intro_text}",
    ]

    # Quote — 문장 단위 순차 표시 (흰색, ⑨ sentence_durs 기반 싱크)
    quote_chunks = _chunk_quote(quote_text)
    n = max(1, len(quote_chunks))
    sentence_durs = durations.get("sentence_durs")

    if sentence_durs:
        # 문장별 실제 TTS 길이로 각 chunk 표시 시간 배분
        sentences_raw = [s.strip() for s in re.split(r'(?<=[.!?])\s+', quote_text) if s.strip()]
        if not sentences_raw:
            sentences_raw = [quote_text]
        chunk_durs = []
        sent_idx, chars_accum = 0, 0
        for chunk in quote_chunks:
            if sent_idx >= len(sentences_raw):
                sent_idx = len(sentences_raw) - 1
            sent = sentences_raw[sent_idx]
            sent_dur = sentence_durs[sent_idx] if sent_idx < len(sentence_durs) else quote_dur / n
            sent_chars = max(1, len(sent))
            chunk_durs.append(sent_dur * (len(chunk) / sent_chars))
            chars_accum += len(chunk)
            if chars_accum >= sent_chars * 0.85 and sent_idx < len(sentences_raw) - 1:
                sent_idx += 1
                chars_accum = 0
        t_cur = t0_quote
        for chunk, dur in zip(quote_chunks, chunk_durs):
            lines.append(f"Dialogue: 0,{_ts(t_cur)},{_ts(t_cur + dur - 0.05)},Quote,,0,0,0,,{chunk}")
            t_cur += dur
    else:
        # fallback: 균등 분배
        chunk_dur = quote_dur / n
        for j, chunk in enumerate(quote_chunks):
            t_start = t0_quote + j * chunk_dur
            t_end   = t0_quote + (j + 1) * chunk_dur - 0.05
            lines.append(f"Dialogue: 0,{_ts(t_start)},{_ts(t_end)},Quote,,0,0,0,,{chunk}")

    lines += [
        f"Dialogue: 0,{_ts(t0_echo)},{_ts(t0_echo + echo_dur - 0.05)},Echo,,0,0,0,,{echo_text}",
    ]

    ass_path = ep_dir / "subtitles.ass"
    ass_path.write_text("\n".join(lines), encoding="utf-8")
    return ass_path


def make_video(script: dict, ep_dir: str, durations: dict) -> str:
    ep        = Path(ep_dir)
    voice_dur = durations["total_dur"]
    philosopher = script.get("philosopher", "")
    book        = script.get("book", "")

    # ③ 상단 바 2줄 — 철학자(흰색 작게) / 책 이름(오렌지 크게)
    top_bar_h  = int(H * TOP_BAR_RATIO)
    bot_bar_h  = int(H * BOT_BAR_RATIO)
    title_y1   = int(H * 0.09)
    title_y2   = title_y1 + 90
    title_fs1  = 64   # 철학자 이름 (흰색)
    title_fs2  = 76   # 책 이름 (오렌지)
    wm_y       = int(H - bot_bar_h + bot_bar_h * 0.20)
    sl_y       = wm_y + 42

    intro_dur = durations["intro_dur"] + 0.5
    quote_dur = durations["quote_dur"]
    echo_dur  = durations["echo_dur"]

    print(f"나레이션: {voice_dur:.2f}초 | {philosopher} — {book[:20]}")

    # ── [1/5] Ken Burns 클립 (3개) ─────────────────────────────
    print("[1/5] 이미지 클립 생성...")
    clip_files     = []
    clip_durations = []
    for i, dur in enumerate([intro_dur, quote_dur, echo_dur]):
        img = ep / f"bg{i+1}.jpg"
        if not img.exists():
            img = ep / "bg1.jpg"
        out = ep / f"clip{i+1}.mp4"
        # ② portrait_safe=True — 가로 이미지도 9:16으로 강제 변환
        clip_dur = make_ken_burns_clip(img, dur, i, out, portrait_safe=True)
        if clip_dur > 0:
            clip_files.append(out)
            clip_durations.append(clip_dur)
            print(f"  ✅ clip{i+1}.mp4 ({clip_dur:.1f}초, {'줌인' if i%2==0 else '줌아웃'})")

    # ── [2/5] 클립 연결 ────────────────────────────────────────
    print("[2/5] 클립 연결...")
    video_only = ep / "video_only.mp4"
    concat_clips(clip_files, video_only)
    print("  ✅ 클립 연결 완료")

    # ── [3/5] BGM 믹싱 + ⑧ 페이드아웃 ─────────────────────────
    print("[3/5] BGM 믹싱...")
    voice_file = ep / "voice_ko.mp3"
    bgm_mixed  = ep / "voice_with_bgm.mp3"
    fade_start = max(0.0, voice_dur - 2.0)

    run_cmd([
        "ffmpeg", "-y",
        "-i", str(voice_file),
        "-stream_loop", "-1", "-i", BGM_PATH,
        "-filter_complex",
        f"[0:a]volume=1.0[v];"
        f"[1:a]volume=0.10,afade=t=out:st={fade_start}:d=2[b];"
        f"[v][b]amix=inputs=2:duration=first[aout]",
        "-map", "[aout]",
        "-ar", "44100", "-ac", "2",
        "-t", str(voice_dur),
        str(bgm_mixed)
    ], "bgm_mix")
    print("  ✅ BGM 완료 (페이드아웃 적용)")

    # ── [4/5] 자막 ────────────────────────────────────────────
    print("[4/5] 자막 생성...")
    ass_path = build_ass(script, ep, durations)
    print(f"  ✅ 자막 완료")

    # ── [5/5] 최종 합성 ───────────────────────────────────────
    print("[5/5] 최종 출력...")
    font = FONT_PATH

    # ③④ 상하 바 + 브랜딩
    vf = (
        f"drawbox=x=0:y=0:w={W}:h={top_bar_h}:color=black@1.0:t=fill,"
        f"drawbox=x=0:y={H-bot_bar_h}:w={W}:h={bot_bar_h}:color=black@1.0:t=fill,"
        f"ass='{ass_path}',"
        f"drawtext=fontfile={font}:text='{philosopher}':fontsize={title_fs1}:"
        f"fontcolor=white@0.90:x=(w-text_w)/2:y={title_y1}:borderw=2:bordercolor=black@0.6,"
        f"drawtext=fontfile={font}:text='{book}':fontsize={title_fs2}:"
        f"fontcolor=#FF8C00:x=(w-text_w)/2:y={title_y2}:borderw=2:bordercolor=black@0.6,"
        f"drawtext=fontfile={font}:text='{WATERMARK}':fontsize=26:"
        f"fontcolor=white@0.45:x=(w-text_w)/2:y={wm_y}:borderw=1:bordercolor=black@0.3,"
        f"drawtext=fontfile={font}:text='{SLOGAN}':fontsize=24:"
        f"fontcolor=white@0.65:x=(w-text_w)/2:y={sl_y}:borderw=1:bordercolor=black@0.3"
    )

    output = ep / "output_final.mp4"
    assemble_video(video_only, bgm_mixed, vf, output, voice_dur)
    return str(output)

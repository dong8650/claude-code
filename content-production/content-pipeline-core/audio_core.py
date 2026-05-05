"""
audio_core.py — 공통 오디오 처리 코어
=======================================
BGM 믹싱. content-mindset의 검증된 패턴:
  - BGM: -stream_loop -1 (무한 루프) → voice_dur에 맞춰 하드컷
  - amix duration=first + -t voice_dur 이중 보호

이 방식이 보장하는 것:
  - BGM 파일이 voice보다 짧아도 루프로 커버
  - BGM 파일이 voice보다 길어도 정확히 voice_dur에서 종료
  - -c:a copy 없음 → 오디오 길이 정밀 제어 가능
"""
from pathlib import Path
from ffmpeg_utils import run_cmd


def mix_bgm(
    voice_file: Path,
    bgm_file: Path,
    output_file: Path,
    voice_dur: float,
    voice_volume: float = 1.0,
    bgm_volume: float = 0.18,
) -> Path:
    """
    BGM + voice 믹싱.

    voice_file:   TTS 음성 파일 (mp3)
    bgm_file:     BGM 파일 (mp3) — 길이 무관 (-stream_loop -1 처리)
    output_file:  출력 mp3
    voice_dur:    하드컷 기준 길이(초) = get_duration(voice_file)
    voice_volume: 기본 1.0
    bgm_volume:   기본 0.18

    Returns: output_file Path
    """
    run_cmd([
        "ffmpeg", "-y",
        "-i", str(voice_file),
        "-stream_loop", "-1", "-i", str(bgm_file),   # BGM 무한 루프
        "-filter_complex",
        f"[0:a]volume={voice_volume}[v];[1:a]volume={bgm_volume}[b];"
        f"[v][b]amix=inputs=2:duration=first[aout]",
        "-map", "[aout]",
        "-ar", "44100", "-ac", "2",
        "-t", str(voice_dur),                         # 하드컷 — BGM 여분 완전 차단
        str(output_file)
    ], "bgm_mix")
    return output_file

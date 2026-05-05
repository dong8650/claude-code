"""
ffmpeg_utils.py — 공통 FFmpeg 유틸리티
=======================================
모든 채널에서 공유. get_duration, run_cmd, make_silence.

import 방법 (각 채널 make_video.py 상단):
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent / "content-pipeline-core"))
    from ffmpeg_utils import get_duration, run_cmd, make_silence
"""
import subprocess


def get_duration(path: str) -> float:
    """ffprobe로 파일 실제 길이(초) 측정."""
    r = subprocess.run([
        "ffprobe", "-i", path,
        "-show_entries", "format=duration",
        "-v", "quiet", "-of", "csv=p=0"
    ], capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except Exception:
        return 0.0


def run_cmd(cmd: list, label: str = "") -> bool:
    """FFmpeg/ffprobe 명령 실행. 실패 시 마지막 300자 출력."""
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"  ❌ FFmpeg 오류 [{label}]: {r.stderr[-300:]}")
        return False
    return True


def make_silence(path: str, duration: float):
    """무음 MP3 생성 (빈 나레이션 장면용)."""
    subprocess.run([
        "ffmpeg", "-y", "-f", "lavfi",
        "-i", "anullsrc=r=44100:cl=stereo",
        "-t", str(duration), "-q:a", "9",
        "-acodec", "libmp3lame", path
    ], capture_output=True)

"""
video_core.py — 공통 영상 합성 코어
=====================================
Ken Burns, 클립 연결, 최종 영상 조립.

content-mindset make_video.py의 검증된 패턴 기반.
content-health의 portrait_safe 전처리 추가.
"""
from pathlib import Path
from ffmpeg_utils import run_cmd, get_duration


def make_ken_burns_clip(
    img_path: Path,
    duration: float,
    index: int,
    out_path: Path,
    portrait_safe: bool = True,
    size: str = "1080x1920",
    contrast: float = 1.05,
    saturation: float = 1.0,
    brightness: float = -0.02,
) -> float:
    """
    Ken Burns zoompan 클립 생성.
    - 짝수 index: 줌인 (1.0 → 1.3)
    - 홀수 index: 줌아웃 (1.3 → 1.0)
    - portrait_safe=True: 이미지를 size 비율로 강제 변환 후 Ken Burns 적용
    - size: 출력 해상도 ("1080x1920" portrait / "1920x1080" landscape)
    Returns: 실제 생성된 클립 길이(초). 실패 시 0.0.
    """
    frames = max(int(duration * 25), 1)
    zoom_expr = (
        "min(zoom+0.0008,1.3)" if index % 2 == 0
        else "if(eq(on,1),1.3,max(zoom-0.0008,1.0))"
    )
    W, H = size.split("x")

    # portrait_safe: 어떤 방향의 이미지든 size 비율로 변환 (crop center)
    pre = (
        f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
        if portrait_safe else ""
    )

    vf = (
        f"{pre}"
        f"scale=8000:-1,"
        f"zoompan=z='{zoom_expr}':d={frames}:"
        f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={W}x{H},"
        f"eq=contrast={contrast}:saturation={saturation}:brightness={brightness},fps=25"
    )

    ok = run_cmd([
        "ffmpeg", "-y",
        "-loop", "1", "-i", str(img_path),
        "-t", str(duration),
        "-vf", vf,
        "-c:v", "libx264", "-crf", "18", "-preset", "medium",
        "-pix_fmt", "yuv420p", str(out_path)
    ], f"ken_burns_{index}")

    return get_duration(str(out_path)) if ok else 0.0


def concat_clips(clip_files: list, output_path: Path) -> float:
    """클립 파일 목록을 concat demuxer로 연결. Returns 실제 길이(초)."""
    txt = output_path.parent / "_concat_list.txt"
    txt.write_text("\n".join(f"file '{c}'" for c in clip_files), encoding="utf-8")
    run_cmd([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", str(txt), "-c", "copy", str(output_path)
    ], "concat")
    return get_duration(str(output_path))


def assemble_video(
    video_only: Path,
    audio_file: Path,
    vf_overlay: str,
    output: Path,
    voice_dur: float,
) -> Path:
    """
    최종 영상 조립 (2단계):

    Step 1 — mux: video_only + audio_file → _base.mp4
        - -t voice_dur 하드컷: BGM 여분 완전 차단
        - -c:a aac: 오디오 재인코딩으로 정확한 트림 보장

    Step 2 — overlay: _base.mp4 + vf_overlay → output
        - vf_overlay: drawbox + ass 자막 + drawtext 등 채널별 오버레이
        - -c:a aac + -t voice_dur: 오디오 길이 재보정

    audio_file: BGM 믹싱된 mp3 (mix_bgm() 결과)
    voice_dur:  실제 음성 길이(초) — 영상 하드컷 기준
    """
    base_mp4 = output.parent / "_base.mp4"

    # Step 1: mux
    ok1 = run_cmd([
        "ffmpeg", "-y",
        "-i", str(video_only),
        "-i", str(audio_file),
        "-map", "0:v:0", "-map", "1:a:0",
        "-c:v", "copy",
        "-c:a", "aac", "-ar", "44100", "-ac", "2",
        "-t", str(voice_dur),
        str(base_mp4)
    ], "mux")

    if not ok1:
        print("  ❌ mux 실패")
        return output

    # Step 2: overlay + re-encode
    ok2 = run_cmd([
        "ffmpeg", "-y", "-i", str(base_mp4),
        "-vf", vf_overlay,
        "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k",
        "-t", str(voice_dur),
        str(output)
    ], "final")

    if ok2:
        actual = get_duration(str(output))
        print(f"\n✅ 완성: {output}")
        print(f"   실제 길이: {actual:.1f}초 (음성 기준: {voice_dur:.1f}초)")
    else:
        print("  ❌ 최종 출력 실패")

    return output

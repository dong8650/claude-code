"""
make_video_v2.py
================
S급 쇼츠 영상 합성 (10초/20초)
- 장면별 이미지 + 자막 + 나레이션
- 루프 구조: 마지막 장면이 첫 장면으로 자연스럽게 연결
- 자막: 크고 임팩트 있는 스타일 (화면 1/3 이상)
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

BASE_DIR = Path(__file__).parent
FONT_PATH = "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc"
FONT_FALLBACK = "/root/auto_pipeline/NotoSansCJK-Bold.ttc"


def _get_font() -> str:
    for p in [FONT_PATH, FONT_FALLBACK]:
        if Path(p).exists():
            return p
    return "NotoSansCJK-Bold"


def build_ass_subtitle(scenes: list, font_path: str) -> str:
    lines = [
        "[Script Info]",
        "ScriptType: v4.00+",
        "PlayResX: 1080",
        "PlayResY: 1920",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        f"Style: Main,{Path(font_path).stem},72,&H00FFFFFF,&H000000FF,&H00000000,&HAA000000,-1,0,0,0,100,100,2,0,3,3,2,5,60,60,80,1",
        f"Style: Hook,{Path(font_path).stem},84,&H00FF8C00,&H000000FF,&H00000000,&HAA000000,-1,0,0,0,100,100,2,0,3,4,2,5,60,60,80,1",
        f"Style: Loop,{Path(font_path).stem},64,&H0000FFFF,&H000000FF,&H00000000,&HAA000000,-1,0,0,0,100,100,2,0,3,3,2,2,60,60,80,1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]

    current = 0.0
    for i, scene in enumerate(scenes):
        dur = scene["duration"]
        start = _ts(current)
        end = _ts(current + dur - 0.1)
        caption = scene.get("caption", "").replace("\n", "\\N")

        if i == 0:
            style = "Hook"
        elif i == len(scenes) - 1:
            style = "Loop"
        else:
            style = "Main"

        lines.append(f"Dialogue: 0,{start},{end},{style},,0,0,0,,{caption}")
        current += dur

    return "\n".join(lines)


def _ts(sec: float) -> str:
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = sec % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def make_video(ep_dir: Path, script: dict, bgm_path: str = None) -> Path:
    scenes = script["scenes"]
    total_dur = script.get("total_duration", sum(s["duration"] for s in scenes))
    font_path = _get_font()

    ass_content = build_ass_subtitle(scenes, font_path)
    ass_file = ep_dir / "subtitles_v2.ass"
    ass_file.write_text(ass_content, encoding="utf-8")

    # 각 장면별 클립 생성
    clip_files = []
    for i, scene in enumerate(scenes):
        img = ep_dir / f"bg{i+1}.jpg"
        if not img.exists():
            img = ep_dir / "bg1.jpg"  # fallback
        clip_out = ep_dir / f"clip{i+1}.mp4"
        dur = scene["duration"]

        cmd = [
            "ffmpeg", "-y",
            "-loop", "1", "-i", str(img),
            "-t", str(dur),
            "-vf", f"scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=30",
            "-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p",
            "-an", str(clip_out)
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        clip_files.append(clip_out)

    # 클립 concat
    concat_list = ep_dir / "concat.txt"
    concat_list.write_text("\n".join(f"file '{c}'" for c in clip_files), encoding="utf-8")
    concat_out = ep_dir / "concat.mp4"
    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", str(concat_list), "-c", "copy", str(concat_out)
    ], check=True, capture_output=True)

    # 나레이션 합치기
    voice_file = ep_dir / "voice_ko.mp3"
    output = ep_dir / "output_final.mp4"

    vf_filter = f"ass={ass_file}"

    if voice_file.exists():
        audio_inputs = ["-i", str(voice_file)]
        if bgm_path and Path(bgm_path).exists():
            audio_inputs += ["-i", bgm_path]
            amix = f"[1:a]volume=0.8[v];[2:a]volume=0.2[b];[v][b]amix=inputs=2:duration=first[aout]"
            audio_map = ["-filter_complex", amix, "-map", "0:v", "-map", "[aout]"]
        else:
            audio_map = ["-map", "0:v", "-map", "1:a"]

        cmd = (
            ["ffmpeg", "-y", "-i", str(concat_out)]
            + audio_inputs
            + ["-vf", vf_filter]
            + audio_map
            + ["-c:v", "libx264", "-preset", "fast", "-c:a", "aac",
               "-t", str(total_dur), str(output)]
        )
    else:
        cmd = [
            "ffmpeg", "-y", "-i", str(concat_out),
            "-vf", vf_filter,
            "-c:v", "libx264", "-preset", "fast",
            "-t", str(total_dur), "-an", str(output)
        ]

    subprocess.run(cmd, check=True, capture_output=True)
    return output


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--ep", required=True)
    parser.add_argument("--script", required=True)
    parser.add_argument("--bgm", default=None)
    args = parser.parse_args()

    ep_dir = Path(args.ep)
    script = json.loads(Path(args.script).read_text(encoding="utf-8"))
    out = make_video(ep_dir, script, args.bgm)
    print(f"✅ 완성: {out}")

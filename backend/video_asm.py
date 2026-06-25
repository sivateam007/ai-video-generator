"""Assemble slides + audio into final MP4 video using ffmpeg."""
import os, subprocess, shutil
from pathlib import Path

def get_duration(path: str, ffprobe: str = None) -> float:
    if ffprobe is None:
        ffprobe = _find_ffprobe()
    r = subprocess.run([
        ffprobe, "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", path
    ], capture_output=True, text=True, timeout=30)
    try:
        return float(r.stdout.strip()) if r.returncode == 0 and r.stdout.strip() else 5.0
    except:
        return 5.0

def assemble_video(
    slides_dir: str,
    audio_files: list[str],
    output_path: str,
    on_progress=None
) -> str:
    ffmpeg = _find_ffmpeg()
    ffprobe = _find_ffprobe()

    slide_files = sorted(Path(slides_dir).glob("slide_*.png"))
    if not slide_files:
        raise RuntimeError("No slide images found!")

    seg_dir = Path(slides_dir).parent / "_segments"
    os.makedirs(str(seg_dir), exist_ok=True)
    seg_files = []

    # First audio is the title gap; remaining map 1:1 to slides
    audio_idx = 0
    for slide_idx, slide_path in enumerate(slide_files, 1):
        audio_path = audio_files[audio_idx] if audio_idx < len(audio_files) else None
        audio_idx += 1

        if not audio_path or not os.path.exists(audio_path):
            print(f"  Slide {slide_idx:02d}: no audio, using 3s silence")
            audio_path = str(seg_dir / f"_silence_{slide_idx:02d}.mp3")
            subprocess.run([
                ffmpeg, "-y", "-f", "lavfi",
                "-i", "anullsrc=r=24000:cl=mono",
                "-t", "3.0", audio_path
            ], capture_output=True, timeout=30)

        dur = get_duration(audio_path, ffprobe)
        if dur < 0.5:
            dur = 3.0

        seg = str(seg_dir / f"seg_{slide_idx:02d}.mp4")
        subprocess.run([
            ffmpeg, "-y", "-loop", "1", "-i", str(slide_path),
            "-i", audio_path,
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-preset", "veryfast", "-crf", "23",
            "-vf", "scale=1280:720:force_original_aspect_ratio=disable",
            "-c:a", "aac", "-b:a", "128k",
            "-t", str(round(dur, 2)),
            seg
        ], capture_output=True, timeout=600)
        seg_files.append(seg)
        print(f"  Segment {slide_idx:02d} ({dur:.1f}s)")

        if on_progress:
            on_progress(f"segment_{slide_idx:02d}")

    if not seg_files:
        raise RuntimeError("No video segments generated!")

    # Concat all segments
    concat_file = str(seg_dir / "_concat.txt")
    with open(concat_file, "w") as f:
        for seg in seg_files:
            f.write(f"file '{seg}'\n")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    subprocess.run([
        ffmpeg, "-y", "-f", "concat", "-safe", "0",
        "-i", concat_file,
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-preset", "veryfast", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k",
        "-movflags", "+faststart",
        output_path
    ], capture_output=True, timeout=600)

    # Cleanup
    for seg in seg_files:
        os.unlink(seg)
    os.unlink(concat_file)
    shutil.rmtree(str(seg_dir), ignore_errors=True)

    dur = get_duration(output_path)
    size_mb = os.path.getsize(output_path) / (1024 * 1024)
    mins, secs = int(dur // 60), int(dur % 60)
    print(f"\nOutput: {output_path}")
    print(f"Duration: {mins:02d}:{secs:02d} ({dur:.1f}s)")
    print(f"Size: {size_mb:.1f} MB")

    return output_path

def _find_ffmpeg() -> str:
    base = r"C:\Users\siva\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin"
    for p in [f"{base}\\ffmpeg.exe", "ffmpeg", "ffmpeg.exe"]:
        if os.path.exists(p) if '\\' in p else True:
            return p
    return "ffmpeg"

def _find_ffprobe() -> str:
    base = r"C:\Users\siva\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin"
    for p in [f"{base}\\ffprobe.exe", "ffprobe", "ffprobe.exe"]:
        if os.path.exists(p) if '\\' in p else True:
            return p
    return "ffprobe"

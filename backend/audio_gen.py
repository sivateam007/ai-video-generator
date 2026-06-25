"""Generate Tamil narration audio for each slide using Gemini TTS."""
import asyncio, os, subprocess
from pathlib import Path
from google import genai
from google.genai import types

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
AUDIO_SAMPLE_RATE = 24000

async def generate_audio(slides: list[dict], output_dir: str, on_progress=None) -> list[str]:
    """Generate MP3 audio files for each slide. Returns list of file paths."""
    os.makedirs(output_dir, exist_ok=True)
    audio_files = []

    try:
        if not GEMINI_API_KEY:
            print("WARNING: No GEMINI_API_KEY set. Generating silent audio.")
            return _generate_silent(slides, output_dir)

        client = genai.Client(api_key=GEMINI_API_KEY)

        # Title gap
        silent_gap = os.path.join(output_dir, "_gap.mp3")
        _make_silence(silent_gap, 5.0)
        audio_files.append(silent_gap)
        if on_progress:
            await on_progress("audio_title_gap")

        for i, slide in enumerate(slides):
            narration = slide.get("narration", "")
            if not narration:
                gap = os.path.join(output_dir, f"_gap_{i:02d}.mp3")
                _make_silence(gap, 3.0)
                audio_files.append(gap)
                continue

            out_file = os.path.join(output_dir, f"slide_{i+1:02d}.mp3")
            success = await _gen_single(client, narration, out_file, i + 1)

            if not success:
                gap = os.path.join(output_dir, f"_gap_{i:02d}.mp3")
                _make_silence(gap, 3.0)
                audio_files.append(gap)
            else:
                audio_files.append(out_file)

            if on_progress:
                await on_progress(f"audio_slide_{i+1:02d}")

            await asyncio.sleep(0.5)
    except Exception as e:
        print(f"Audio generation error: {e}")
        # Fallback to silent for remaining slides
        if len(audio_files) < len(slides) + 1:
            for j in range(len(audio_files) - 1, len(slides)):
                gap = os.path.join(output_dir, f"_gap_{j:02d}.mp3")
                try:
                    _make_silence(gap, 3.0)
                except:
                    pass
                audio_files.append(gap)

    return audio_files

async def _gen_single(client, text: str, out_path: str, idx: int) -> bool:
    print(f"  Audio [{idx:02d}]...", end=' ', flush=True)
    try:
        async with client.aio.live.connect(
            model='gemini-3.1-flash-live-preview',
            config=types.LiveConnectConfig(
                response_modalities=['AUDIO'],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name='aoede')
                    )
                )
            )
        ) as session:
            await session.send_client_content(
                turns={"role": "user", "parts": [{"text": f"Read this text aloud exactly. Do not add any extra words. Speak only the exact text below:\n\n{text}"}]},
                turn_complete=True
            )
            chunks = []
            async for response in session.receive():
                if response.data:
                    chunks.append(response.data)

        if not chunks:
            print("no data"); return False

        raw = out_path.replace('.mp3', '.raw')
        with open(raw, "wb") as f:
            for c in chunks:
                f.write(c)

        ffmpeg = _find_ffmpeg()
        subprocess.run([
            ffmpeg, "-y", "-f", "s16le", "-ar", str(AUDIO_SAMPLE_RATE), "-ac", "1",
            "-i", raw, out_path
        ], capture_output=True, timeout=60)
        os.unlink(raw)
        print("OK")
        return True
    except Exception as e:
        print(f"FAILED: {str(e)[:60]}")
        return False

def _make_silence(out_path: str, duration: float):
    ffmpeg = _find_ffmpeg()
    subprocess.run([
        ffmpeg, "-y", "-f", "lavfi", "-i", f"anullsrc=r={AUDIO_SAMPLE_RATE}:cl=mono",
        "-t", str(duration), out_path
    ], capture_output=True, timeout=30)

def _find_ffmpeg() -> str:
    for p in [
        r"C:\Users\siva\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin\ffmpeg.exe",
        "ffmpeg", "ffmpeg.exe"
    ]:
        if os.path.exists(p) if '\\' in p else True:
            return p
    return "ffmpeg"

def _generate_silent(slides: list[dict], output_dir: str) -> list[str]:
    paths = []
    gap = os.path.join(output_dir, "_gap.mp3")
    _make_silence(gap, 5.0)
    paths.append(gap)
    for i in range(len(slides)):
        p = os.path.join(output_dir, f"slide_{i+1:02d}.mp3")
        _make_silence(p, 5.0)
        paths.append(p)
    return paths

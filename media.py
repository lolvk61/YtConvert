"""Media commands shared by the five tools."""

import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory
from urllib.parse import parse_qs, urlsplit


ROOT = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / ".deps"))
HIDDEN = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def executable(name):
    local = ROOT / "bin" / f"{name}.exe"
    return str(local) if local.is_file() else shutil.which(name)


def require(name):
    path = executable(name)
    if not path:
        raise ValueError(f"Не найден {name}. Запустите install-tools.cmd и повторите.")
    return path


def timestamp(value):
    value = value.strip().replace(",", ".")
    if not re.fullmatch(r"(?:\d+:){0,2}\d+(?:\.\d+)?", value):
        raise ValueError("Укажите время в секундах или в формате ЧЧ:ММ:СС.")
    parts = list(map(float, value.split(":")))
    if any(part >= 60 for part in parts[1:]):
        raise ValueError("Минуты и секунды после двоеточия должны быть меньше 60.")
    result = sum(part * 60 ** index for index, part in enumerate(reversed(parts)))
    if not math.isfinite(result):
        raise ValueError("Укажите конечное время.")
    return result


def youtube_url(value):
    url = urlsplit(value)
    host = url.hostname or ""
    if url.scheme not in {"https", "http"} or url.username or url.password:
        raise ValueError("Вставьте полную ссылку на видео YouTube.")
    parts = url.path.strip("/").split("/")
    video_id = ""
    if host == "youtu.be" and len(parts) == 1:
        video_id = parts[0]
    elif host == "youtube.com" or host.endswith(".youtube.com"):
        if parts == ["watch"]:
            video_id = parse_qs(url.query).get("v", [""])[0]
        elif len(parts) == 2 and parts[0] in {"shorts", "live", "embed", "v"}:
            video_id = parts[1]
    if not re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id):
        raise ValueError("Вставьте ссылку на отдельное видео YouTube.")
    return f"https://www.youtube.com/watch?v={video_id}"


def run(command, on_line):
    recent = []
    with subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          text=True, encoding="utf-8", errors="replace",
                          creationflags=HIDDEN) as process:
        for line in process.stdout:
            line = line.strip()
            if line:
                recent.append(line)
                recent = recent[-12:]
                on_line(line)
        if process.wait():
            raise ValueError("\n".join(recent) or "Обработка завершилась с ошибкой.")


def download(url, folder, height, status, extension="mp4"):
    from yt_dlp import YoutubeDL
    from yt_dlp.utils import match_filter_func

    ffmpeg = require("ffmpeg")
    require("ffprobe")
    runtime = executable("deno") or executable("node")
    if not runtime:
        raise ValueError("Не найден Deno или Node.js. Запустите install-tools.cmd.")
    runtime_name = Path(runtime).stem

    def progress(info):
        if info["status"] == "downloading":
            total = info.get("total_bytes") or info.get("total_bytes_estimate")
            if total:
                status(f"Скачивание · {info.get('downloaded_bytes', 0) / total:.0%}")
        elif info["status"] == "finished":
            status("Подготовка видео…")

    with TemporaryDirectory(prefix=".ytconvert-", dir=folder) as temp:
        selector = (f"bv[height<={height}][ext=mp4]+ba[ext=m4a]/"
                    f"b[height<={height}][ext=mp4]/bv[height<={height}]+ba/b[height<={height}]")
        options = {
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "retries": 3,
            "fragment_retries": 3,
            "socket_timeout": 30,
            "windowsfilenames": True,
            "format": selector,
            "ffmpeg_location": ffmpeg,
            "js_runtimes": {runtime_name: {"path": runtime}},
            "merge_output_format": "mp4",
            "outtmpl": str(Path(temp) / "%(title).100s [%(id)s].%(ext)s"),
            "progress_hooks": [progress],
            "match_filter": match_filter_func("!is_live"),
            "postprocessors": [{"key": "FFmpegVideoRemuxer", "preferedformat": "mp4"}],
        }
        with YoutubeDL(options) as downloader:
            info = downloader.extract_info(url, download=True)
        if not info:
            raise ValueError("Видео недоступно. Текущие прямые трансляции не поддерживаются.")
        candidates = list(Path(temp).glob("*.mp4"))
        if len(candidates) != 1:
            raise ValueError("Не удалось найти скачанный файл.")
        source = candidates[0]
        if extension != "mp4":
            converted = source.with_suffix("." + extension)
            mode = "video" if extension in {"mkv", "webm", "mov", "avi"} else "extract"
            convert(mode, source, converted, 0, None, 0, 0, status)
            source = converted
        index = 1
        target = folder / source.name
        while True:
            try:
                source.rename(target)
                return target
            except FileExistsError:
                index += 1
                target = folder / f"{source.stem} ({index}){source.suffix}"


def ensure_tools(status):
    """Install external command-line tools locally on first use."""
    if executable("ffmpeg") and executable("ffprobe") and (
            executable("deno") or executable("node")):
        return
    status("Первый запуск · скачивание компонентов FFmpeg и Deno…")
    script = ROOT / "setup-tools.ps1"
    run(["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
         "-File", str(script)], lambda line: None)


def convert(mode, source, target, start, end, fps, width, status):
    ffmpeg = require("ffmpeg")
    probe = subprocess.run(
        [require("ffprobe"), "-v", "error", "-show_streams", "-show_format", "-of", "json",
         str(source)], capture_output=True, encoding="utf-8", errors="replace",
        creationflags=HIDDEN)
    if probe.returncode:
        raise ValueError(probe.stderr.strip() or "Не удалось прочитать файл.")
    info = json.loads(probe.stdout)
    streams = {stream["codec_type"] for stream in info["streams"]
               if not stream.get("disposition", {}).get("attached_pic")}
    required = {"extract": {"video", "audio"}, "gif": {"video"},
                "video": {"video"}, "audio": {"audio"}}[mode]
    if not required <= streams:
        raise ValueError("В файле отсутствует нужная видео- или аудиодорожка.")

    raw_duration = info["format"].get("duration", "N/A")
    duration = float(raw_duration) if raw_duration != "N/A" else None
    if duration is not None and (start >= duration or end is not None and end > duration + 0.05):
        raise ValueError(f"Границы выходят за длительность файла ({duration:.3f} с).")
    length = (end if end is not None else duration)
    length = length - start if length is not None else None

    command = [ffmpeg, "-hide_banner", "-nostdin", "-loglevel", "error", "-nostats",
               "-progress", "pipe:1", "-xerror", "-abort_on", "empty_output"]
    if start:
        command += ["-ss", f"{start:.9f}"]
    if end is not None:
        command += ["-t", f"{end - start:.9f}"]
    command += ["-i", str(source)]
    if mode == "gif":
        gif_filter = f"fps={fps},scale=w='min({width},iw)':h=-1:flags=lanczos"
    elif mode == "video":
        command += ["-map", "0:V:0", "-map", "0:a:0?", "-vf",
                    "pad=ceil(iw/2)*2:ceil(ih/2)*2", "-c:v", "libx264", "-pix_fmt",
                    "yuv420p", "-c:a", "aac"]
        extension = target.suffix.lower()
        if extension == ".webm":
            command += ["-c:v", "libvpx-vp9", "-crf", "32", "-b:v", "0", "-c:a", "libopus"]
        elif extension == ".avi":
            command += ["-c:v", "mpeg4", "-q:v", "3", "-c:a", "libmp3lame"]
        elif extension in {".mp4", ".mov"}:
            command += ["-movflags", "+faststart"]
    else:
        codec = {"mp3": "libmp3lame", "wav": "pcm_s16le", "m4a": "aac", "flac": "flac", "ogg": "libvorbis", "opus": "libopus", "aac": "aac"}
        command += ["-map", "0:a:0", "-vn", "-c:a", codec[target.suffix[1:].lower()]]

    def on_line(line):
        if length and re.fullmatch(r"out_time_us=\d+", line):
            elapsed = int(line.split("=")[1]) / 1_000_000
            status(f"Обработка · {min(99, int(elapsed / length * 100))}%")

    with TemporaryDirectory(prefix=".media-", dir=target.parent) as temp:
        output = Path(temp) / target.name
        if mode == "gif":
            palette = Path(temp) / "palette.png"
            status("Подготовка палитры GIF…")
            run(command + ["-map", "0:V:0", "-vf", f"{gif_filter},palettegen",
                           "-frames:v", "1", "-update", "1", str(palette)], lambda line: None)
            command += ["-i", str(palette), "-filter_complex",
                        f"[0:V:0]{gif_filter}[frames];[frames][1:v]paletteuse[gif]",
                        "-map", "[gif]", "-an", "-loop", "0"]
        run(command + [str(output)], on_line)
        if not output.is_file() or not output.stat().st_size:
            raise ValueError("Обработка не создала выходной файл.")
        os.replace(output, target)
    return target

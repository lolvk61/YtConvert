"""Exercise the same media functions and Qt playback used by the packaged app."""

import json
from pathlib import Path
import subprocess
import tempfile
import time
import traceback

import media


def run_selftest(arguments):
    result_path = Path(arguments[arguments.index("--self-test") + 1]).resolve()
    result_path.parent.mkdir(parents=True, exist_ok=True)
    results = {}
    try:
        from app import QApplication, Studio, STYLE, QUrl, QMediaPlayer
        app = QApplication([])
        app.setStyle("Fusion")
        app.setStyleSheet(STYLE)
        window = Studio()
        window.show_tool("video", "Обрезка видео")
        window.show()

        def process_for(seconds):
            deadline = time.monotonic() + seconds
            while time.monotonic() < deadline:
                app.processEvents()
                time.sleep(.01)

        with tempfile.TemporaryDirectory(dir=result_path.parent) as directory:
            directory = Path(directory)
            source = directory / "sample.mp4"
            subprocess.run([
                media.require("ffmpeg"), "-v", "error", "-f", "lavfi", "-i",
                "testsrc2=size=320x180:rate=24", "-f", "lavfi", "-i",
                "sine=frequency=440", "-t", "3", "-c:v", "libx264", "-c:a", "aac",
                str(source),
            ], check=True, creationflags=media.HIDDEN)
            for extension in ("mp4", "mkv", "webm", "mov", "avi",
                              "mp3", "wav", "m4a", "flac", "ogg", "opus", "aac", "gif"):
                mode = "video" if extension in ("mp4", "mkv", "webm", "mov", "avi") else "audio"
                if extension == "gif":
                    mode = "gif"
                output = directory / f"result.{extension}"
                media.convert(mode, source, output, .5, 1.5, 12, 320, lambda message: None)
                probe = subprocess.check_output([
                    media.require("ffprobe"), "-v", "error", "-show_entries", "format=duration",
                    "-of", "json", str(output),
                ], creationflags=media.HIDDEN)
                duration = float(json.loads(probe)["format"]["duration"])
                assert abs(duration - 1) < .2, (extension, duration)
                results[extension] = duration
            window.player.setSource(QUrl.fromLocalFile(str(source)))
            window.empty.hide()
            window.video.show()
            window.player.play()
            process_for(1.5)
            assert window.player.position() > 0, window.player.errorString()
            assert window.video.videoSink().videoFrame().isValid(), "No decoded video frame"
            window.begin.setText("0.5")
            window.end.setText("1.2")
            window.play_fragment()
            process_for(1.5)
            assert window.player.playbackState() != QMediaPlayer.PlayingState
            assert window.preview_end is None
            results["playback_and_fragment"] = "passed"
            window.player.stop()
            window.player.setSource(QUrl())
            process_for(.2)
            window.show_tool("video", "Обрезка видео")
            process_for(.2)
            window.grab().save(str(result_path.parent / "trim.png"))
            window.show_tool("download", "Скачивание с YouTube")
            process_for(.2)
            window.grab().save(str(result_path.parent / "download.png"))
            if "--network" in arguments:
                output = media.download(
                    "https://www.youtube.com/watch?v=aqz-KE-bpKQ",
                    directory, 360, lambda message: None, extension="mkv")
                assert output.stat().st_size > 0
                results["youtube_mkv"] = output.stat().st_size
            window.close()
        results["passed"] = True
    except Exception:
        results["passed"] = False
        results["error"] = traceback.format_exc()
    result_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0 if results["passed"] else 1

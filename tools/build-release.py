"""Build the portable Windows x64 release from a clean Python environment."""

import hashlib
from importlib import metadata
import os
from pathlib import Path
import shutil
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".deps"))
os.environ["PYTHONPATH"] = str(ROOT / ".deps") + os.pathsep + os.environ.get("PYTHONPATH", "")
# Avoid collecting unrelated ICU/OpenSSL DLLs from developer tools on PATH.
windows = Path(os.environ["SystemRoot"])
os.environ["PATH"] = os.pathsep.join(map(str, (
    windows / "System32", windows,
    ROOT / ".deps" / "PySide6", ROOT / ".deps" / "shiboken6", Path(sys.base_prefix),
)))

from PIL import Image
from PyInstaller.__main__ import run


def main():
    os.chdir(ROOT)
    version = "1.0.0"
    image = Image.open(ROOT / "assets" / "app.png")
    image.save(ROOT / "assets" / "app.ico",
               sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    command = [
        "--noconfirm", "--clean", "--onedir", "--windowed", "--noupx",
        "--name", "YtConvert", "--icon", str(ROOT / "assets" / "app.ico"),
        "--distpath", str(ROOT / "dist"),
        "--workpath", str(ROOT / "build"),
        "--specpath", str(ROOT),
        "--paths", str(ROOT / ".deps"),
        "--collect-all", "yt_dlp", "--collect-all", "yt_dlp_ejs",
        "--copy-metadata", "yt-dlp", "--copy-metadata", "yt-dlp-ejs",
        "--exclude-module", "tkinter", "--exclude-module", "PySide6.QtWebEngineCore",
        "--exclude-module", "PySide6.QtWebEngineWidgets",
        str(ROOT / "app.py"),
    ]
    if "--package-only" not in sys.argv:
        run(command)
    output = ROOT / "dist" / "YtConvert"
    for name in ("LICENSE", "README.md", "README.en.md", "THIRD-PARTY-NOTICES.md",
                 "setup-tools.ps1", "install-tools.cmd"):
        shutil.copy2(ROOT / name, output / name)
    shutil.copytree(ROOT / "assets", output / "assets", dirs_exist_ok=True)
    shutil.copytree(ROOT / "docs", output / "docs", dirs_exist_ok=True)
    shutil.copytree(ROOT / "licenses", output / "licenses", dirs_exist_ok=True)
    licenses = output / "licenses"
    licenses.mkdir(exist_ok=True)
    for package in ("PySide6-Essentials", "PySide6-Addons", "shiboken6", "yt-dlp",
                    "yt-dlp-ejs", "certifi", "requests", "urllib3", "idna",
                    "charset-normalizer", "brotli", "mutagen", "pycryptodomex", "websockets"):
        distribution = metadata.distribution(package)
        for file in distribution.files or []:
            if any(word in str(file).lower() for word in ("license", "copying")):
                source = Path(distribution.locate_file(file))
                if source.is_file():
                    destination = licenses / package / str(file).replace("/", "_")
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, destination)
    python_license = Path(sys.base_prefix) / "LICENSE.txt"
    if python_license.is_file():
        shutil.copy2(python_license, licenses / "Python-LICENSE.txt")
    archive = ROOT / "dist" / f"YtConvert-v{version}-win-x64.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as bundle:
        for file in sorted(output.rglob("*")):
            if file.is_file() and "bin" not in file.relative_to(output).parts:
                bundle.write(file, file.relative_to(output.parent))
    with archive.open("rb") as file:
        digest = hashlib.file_digest(file, "sha256").hexdigest()
    (ROOT / "dist" / "SHA256SUMS.txt").write_text(f"{digest}  {archive.name}\n", encoding="utf-8")
    print(f"Created {archive}")


if __name__ == "__main__":
    main()

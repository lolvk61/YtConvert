# Third-party components

YtConvert source code and its application icon are licensed under MIT. Bundled
dependencies retain their own licenses. Copies supplied by their distributions
are collected into the portable release's `licenses` directory.

| Component | License | Source |
| --- | --- | --- |
| Python 3.14 | PSF | https://www.python.org/downloads/source/ |
| Qt / PySide6 / Shiboken 6.12 | LGPLv3 and component-specific notices | https://download.qt.io/archive/qt/6.12/ |
| yt-dlp 2026.10.26 | Unlicense | https://github.com/yt-dlp/yt-dlp/tree/2026.10.26 |
| yt-dlp-ejs 0.8.0 | Unlicense | https://github.com/yt-dlp/ejs |
| Requests and its dependencies | Apache-2.0, MIT, BSD, MPL-2.0 | See bundled license files |
| Brotli | MIT | https://github.com/google/brotli |
| Mutagen | GPLv2 or later | https://github.com/quodlibet/mutagen |
| PyCryptodome | BSD and public-domain components | https://github.com/Legrandin/pycryptodome |
| Websockets | BSD | https://github.com/python-websockets/websockets |
| PyInstaller bootloader | GPL with distribution exception | https://pyinstaller.org/en/stable/license.html |

Qt libraries are distributed as replaceable shared DLLs in `_internal`.
The application places no restriction on modifying or reverse engineering
these libraries for debugging such modifications. Qt source archives and build
instructions are available from the Qt project. Preserve the applicable license
notices when redistributing a modified build.

The external FFmpeg and Deno command-line programs are downloaded separately by
`setup-tools.ps1` on first use. FFmpeg builds come from
https://www.gyan.dev/ffmpeg/builds/ and Deno comes from
https://github.com/denoland/deno/releases. These executables are not included in
the YtConvert ZIP.

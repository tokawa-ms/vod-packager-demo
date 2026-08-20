<div align="center">

# vod-packager

**A Python CLI for creating multi-bitrate VoD assets with FFmpeg and Shaka Packager**

[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Packaging](https://img.shields.io/badge/Packaging-CMAF%20%7C%20DASH%20%7C%20HLS-5C4EE5)](https://www.iso.org/standard/79106.html)
[![FFmpeg](https://img.shields.io/badge/FFmpeg-external-007808?logo=ffmpeg&logoColor=white)](https://ffmpeg.org/)
[![Shaka Packager](https://img.shields.io/badge/Shaka%20Packager-external-4285F4)](https://github.com/shaka-project/shaka-packager)

[日本語](README.md) | English

</div>

## Overview

`vod-packager` converts a local video into an Adaptive Bitrate (ABR) package:

1. Inspect the input with FFprobe
2. Encode multiple H.264/AAC fragmented MP4 renditions with FFmpeg
3. Generate shared CMAF segments, an MPEG-DASH MPD, and HLS playlists with
   Shaka Packager
4. Validate the artifacts and safely promote them to a per-run GUID directory

> [!IMPORTANT]
> FFmpeg, FFprobe, and Shaka Packager are **not bundled** with this project.
> Use executables installed by the user through PATH or explicit CLI options.

## Features

- Default 1080p / 720p / 480p / 360p ABR ladder
- Automatic removal of renditions above the source resolution
- Six-second aligned GOPs and CMAF segments
- Fragmented MP4 media segments shared by DASH and HLS
- Video-only packaging for sources without audio
- JSON configuration for bitrates, segment duration, and encoder preset
- Progress logs for probing, each rendition, audio, packaging, and validation
- Safe external process execution without a command shell
- Per-run GUID directories that fully isolate each output
- Staging and artifact validation to prevent incomplete output
- Windows, macOS, and Linux support

## Requirements

| Tool | Requirement |
|---|---|
| Python | 3.11 or newer |
| FFmpeg / FFprobe | A build with the `libx264` and AAC encoders |
| Shaka Packager | A version supporting segmented MP4, DASH, and HLS output |

Executables are discovered through PATH. Use `--ffmpeg-path`,
`--ffprobe-path`, and `--packager-path` when they are installed elsewhere.

## Installation

```powershell
git clone <repository-url>
cd vod-packager
python -m pip install -e .
```

Confirm that the external tools are available:

```powershell
ffmpeg -version
ffprobe -version
packager --version
```

## Quick start

```powershell
vod-packager .\input.mp4
```

An independent test tool can serve a generated package on localhost and
preview its ABR playback with Plyr. The server is not part of the
`vod-packager` package.

```powershell
python .\tools\preview_server\server.py .\output\<GUID> --open-browser
```

The server listens at `http://localhost:8000/` by default. It combines Plyr's
UI with the hls.js HLS engine, supporting automatic bitrate adaptation and
manual selection from the quality menu. Use `--port 8080` to choose another
port. The player JavaScript and CSS are loaded from jsDelivr, so the initial
page load requires an internet connection. Media is served only from
localhost, and the server binds to `127.0.0.1`. Press `Ctrl+C` to stop it.

The Python module entry point is equivalent:

```powershell
python -m vod_packager .\input.mp4
```

Specify the output root and executable paths explicitly:

```powershell
vod-packager .\input.mp4 -o .\output `
  --ffmpeg-path C:\tools\ffmpeg\bin\ffmpeg.exe `
  --ffprobe-path C:\tools\ffmpeg\bin\ffprobe.exe `
  --packager-path C:\tools\shaka\packager.exe
```

When `--output` is omitted, `output` in the current directory is used as the
output root. Every run is stored in a new GUID directory, and the completed
path is printed on success:

```text
Output: C:\project\output\4f1e975b-2767-4fc1-a8b0-01ebbf3c9c76
```

Progress is streamed to standard error throughout processing:

```text
[vod-packager] Probing input media
[vod-packager] Source: 1920x1080, 29.970 fps, 120.0 s, audio=yes
[vod-packager] Renditions: 1080p (1080p), 720p (720p), 480p (480p), 360p (360p)
[vod-packager] [1/4] Encoding video: 1080p at 5000k
[vod-packager] [1/4] Video complete: 1080p
[vod-packager] Encoding audio: AAC-LC at 128k
[vod-packager] Packaging CMAF segments and DASH/HLS manifests
[vod-packager] Validating generated package
[vod-packager] Completed successfully
```

## Output

```text
output/
├── <GUID-1>/
│   ├── manifest.mpd
│   ├── master.m3u8
│   ├── video/
│   │   ├── 1080p/
│   │   │   ├── init.mp4
│   │   │   ├── playlist.m3u8
│   │   │   ├── segment_1.m4s
│   │   │   ├── segment_2.m4s
│   │   │   └── ...
│   │   ├── 720p/
│   │   ├── 480p/
│   │   └── 360p/
│   └── audio/
│       ├── init.mp4
│       ├── playlist.m3u8
│       ├── segment_1.m4s
│       ├── segment_2.m4s
│       └── ...
└── <GUID-2>/
    └── ...
```

The `audio` directory is omitted for video-only input. Renditions above the
source height are omitted. Sources below 360p produce one `source` rendition.
Repeated runs under the same output root use different GUID directories, so
artifacts never mix and previous results are never overwritten.

During processing, intermediate and unvalidated files are written under
`output/.<GUID>.staging-work/`. After validation succeeds, the completed
package is promoted to `output/<GUID>/`. Staging is normally removed on
success or failure and is retained after failure only with `--keep-work-dir`.

## Default encoding ladder

| Name | Height | Bitrate | Max rate | Buffer |
|---|---:|---:|---:|---:|
| 1080p | 1080 | 5000k | 5350k | 7500k |
| 720p | 720 | 2800k | 2996k | 4200k |
| 480p | 480 | 1400k | 1498k | 2100k |
| 360p | 360 | 800k | 856k | 1200k |

- Video: H.264 High Profile, `yuv420p`
- Audio: AAC-LC, 128 kbps, 48 kHz, stereo
- Segment duration: six seconds

## Configuration

See [`examples/config.json`](examples/config.json) for a complete example:

```powershell
vod-packager .\input.mp4 -o .\output --config .\examples\config.json
```

```json
{
  "segment_duration": 6,
  "video_codec": "libx264",
  "video_preset": "medium",
  "audio_bitrate": "128k",
  "renditions": [
    {
      "name": "720p",
      "height": 720,
      "bitrate": "2800k",
      "maxrate": "2996k",
      "bufsize": "4200k"
    }
  ]
}
```

Unknown fields, duplicate rendition names, invalid bitrates, and rendition
names that could be interpreted as paths are rejected.

## CLI options

```text
vod-packager INPUT
  [--output OUTPUT_ROOT]
  [--config FILE]
  [--ffmpeg-path FILE]
  [--ffprobe-path FILE]
  [--packager-path FILE]
  [--keep-work-dir]
  [--verbose]
  [--version]

```

| Option | Description |
|---|---|
| `-o`, `--output` | Root for per-run GUID directories. Default: `output` |
| `--config` | JSON configuration file |
| `--*-path` | Path to each external executable |
| `--keep-work-dir` | Preserve intermediate files after failure |
| `--verbose` | Print external commands and tool output |
| `--version` | Print the application version |

### Exit codes

| Code | Meaning |
|---:|---|
| 0 | Packaging succeeded |
| 2 | Input, configuration, output, or tool validation failed |
| 3 | FFmpeg, FFprobe, or Shaka Packager failed |
| 4 | Generated artifact validation failed |
| 130 | Interrupted by the user |

## Failure safety

The tool creates a staging directory inside the output root and only promotes
it to its GUID directory after all conversion and validation steps succeed.
Every run uses a new GUID, so existing packages are never replaced or deleted.
Failed-run intermediates are removed by default and retained in staging only
when `--keep-work-dir` is used.

## Development

Unit tests:

```powershell
python -m unittest discover -s tests -v
```

Standalone preview server unit tests:

```powershell
python -m unittest discover -s .\tools\preview_server\tests -v
```

The preview server tests cover serving the player page and HLS manifest,
streaming MIME types, rejection of unmounted and directory traversal access,
package directory validation, graph sample reset on seek, buffer/ABR settings,
and expected client disconnects when a segment download is cancelled. This
test suite remains independent of the `src\vod_packager` unit tests.

Integration tests using FFmpeg, FFprobe, and Shaka Packager:

```powershell
$env:VOD_PACKAGER_RUN_INTEGRATION = "1"
python -m unittest tests.test_integration -v
```

## External tools and distribution

This repository and its Python package do not contain FFmpeg, FFprobe, or
Shaka Packager binaries, source code, or libraries. They do not download those
tools automatically. The application only starts executables supplied by the
user through `subprocess`; it does not statically or dynamically link against
FFmpeg libraries.

Under this design, the original Python source in this repository can be
provided under the MIT License. FFmpeg is licensed under the LGPL or GPL,
depending on its build options. An FFmpeg build containing the default
`libx264` encoder generally carries GPL obligations. Shaka Packager also has
its own license terms. If you redistribute any of these tools together with
this application in an installer, container, archive, or similar package, you
must comply with each project's terms and reassess that distribution.

> [!CAUTION]
> This information is not legal advice. Consult qualified counsel for
> commercial distribution, bundled binaries, and codec patent questions in
> your jurisdiction.

## Limitations

- One local input file
- The first video stream and first optional audio stream only
- No DRM, subtitles, multiple audio tracks, remote URLs, or live/low-latency
  packaging
- No hardware encoders, deinterlacing, or HDR tone mapping
- No automatic installation of FFmpeg or Shaka Packager

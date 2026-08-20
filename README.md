<div align="center">

# vod-packager

**FFmpeg と Shaka Packager で、マルチビットレートの VoD 配信素材を生成する Python CLI**

[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Packaging](https://img.shields.io/badge/Packaging-CMAF%20%7C%20DASH%20%7C%20HLS-5C4EE5)](https://www.iso.org/standard/79106.html)
[![FFmpeg](https://img.shields.io/badge/FFmpeg-external-007808?logo=ffmpeg&logoColor=white)](https://ffmpeg.org/)
[![Shaka Packager](https://img.shields.io/badge/Shaka%20Packager-external-4285F4)](https://github.com/shaka-project/shaka-packager)

日本語 | [English](README-EN.md)

</div>

## 概要

`vod-packager` は、ローカル動画を Adaptive Bitrate（ABR）配信用に変換する
コマンドラインツールです。

1. FFprobe で入力映像を解析
2. FFmpeg で H.264/AAC の複数 bitrate fragmented MP4 を生成
3. Shaka Packager で共通 CMAF segment、MPEG-DASH MPD、HLS playlist を生成
4. 成果物を検証し、実行ごとの GUID directory へ安全に反映

> [!IMPORTANT]
> FFmpeg、FFprobe、Shaka Packager は本プロジェクトに**同梱されません**。
> 利用者がインストールした実行ファイルを PATH または CLI option で指定します。

## 主な機能

- 1080p / 720p / 480p / 360p の既定 ABR ladder
- 入力解像度を超える rendition の自動除外
- 6 秒間隔で整列した GOP と CMAF segment
- DASH と HLS で共有可能な fragmented MP4 media segment
- 音声なし動画の video-only packaging
- JSON による bitrate、segment duration、encoder preset の変更
- 入力解析、各 rendition、音声、packaging、検証の進捗 log
- shell を経由しない安全な外部 process 実行
- 実行ごとの GUID directory による出力の完全な分離
- staging と成果物検証による不完全な出力の防止
- Windows、macOS、Linux 対応

## 動作要件

| Tool | 要件 |
|---|---|
| Python | 3.11 以上 |
| FFmpeg / FFprobe | `libx264` encoder と AAC encoder を利用可能な build |
| Shaka Packager | segmented MP4、DASH、HLS 出力をサポートする version |

実行ファイルは PATH から探索されます。PATH にない場合は
`--ffmpeg-path`、`--ffprobe-path`、`--packager-path` で指定できます。

## インストール

```powershell
git clone <repository-url>
cd vod-packager
python -m pip install -e .
```

外部 tool が認識されることを確認します。

```powershell
ffmpeg -version
ffprobe -version
packager --version
```

## クイックスタート

```powershell
vod-packager .\input.mp4
```

独立した test tool を使い、生成済み package を localhost で配信して Plyr で
ABR 再生を確認できます。この server は `vod-packager` package には含まれません。

```powershell
python .\tools\preview_server\server.py .\output\<GUID> --open-browser
```

既定では `http://localhost:8000/` で待ち受けます。Plyr の UI と hls.js の
HLS 再生 engine を組み合わせ、回線状況に応じた自動 bitrate 切り替えと
quality menu からの手動切り替えに対応します。`--port 8080` で port を変更
できます。Player の JavaScript と CSS は jsDelivr から取得するため、初回の
表示には internet 接続が必要です。Media file は localhost からのみ配信され、
server は `127.0.0.1` に bind されます。終了するには `Ctrl+C` を押します。

Python module としても実行できます。

```powershell
python -m vod_packager .\input.mp4
```

出力 root と実行ファイルを明示する例:

```powershell
vod-packager .\input.mp4 -o .\output `
  --ffmpeg-path C:\tools\ffmpeg\bin\ffmpeg.exe `
  --ffprobe-path C:\tools\ffmpeg\bin\ffprobe.exe `
  --packager-path C:\tools\shaka\packager.exe
```

`--output` を省略した場合、current directory の `output` が出力 root になります。
各実行は新しい GUID directory に格納され、成功時に実際の出力 path が表示されます。

```text
Output: C:\project\output\4f1e975b-2767-4fc1-a8b0-01ebbf3c9c76
```

処理中は次のような進捗が標準エラーへ逐次表示されます。

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

## 出力構成

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

入力に音声がない場合、`audio` directory は生成されません。入力より高い
rendition は除外され、360p 未満の入力では `source` rendition が生成されます。
同じ出力 root で何度実行しても、異なる GUID directory に格納されるため、
成果物が混在したり既存結果を上書きしたりすることはありません。

処理中は `output/.<GUID>.staging-work/` に中間 file と未検証の成果物を作成し、
検証成功後に `output/<GUID>/` へ切り替えます。通常、staging directory は
完了時または失敗時に削除され、`--keep-work-dir` を指定した失敗時のみ残ります。

## 既定の encoding ladder

| Name | Height | Bitrate | Max rate | Buffer |
|---|---:|---:|---:|---:|
| 1080p | 1080 | 5000k | 5350k | 7500k |
| 720p | 720 | 2800k | 2996k | 4200k |
| 480p | 480 | 1400k | 1498k | 2100k |
| 360p | 360 | 800k | 856k | 1200k |

- Video: H.264 High Profile、`yuv420p`
- Audio: AAC-LC、128 kbps、48 kHz、stereo
- Segment duration: 6 秒

## 設定のカスタマイズ

完全な設定例は [`examples/config.json`](examples/config.json) にあります。

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

不明な field、重複した rendition 名、不正な bitrate、path として解釈できる
rendition 名はエラーとして拒否されます。

## CLI option

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

| Option | 説明 |
|---|---|
| `-o`, `--output` | GUID directory を作成する出力 root。既定値: `output` |
| `--config` | JSON 設定 file |
| `--*-path` | 各外部 tool の実行 file |
| `--keep-work-dir` | 失敗時の中間 file を保持 |
| `--verbose` | 外部 command と tool の出力を表示 |
| `--version` | version を表示 |

### Exit code

| Code | 意味 |
|---:|---|
| 0 | Packaging 成功 |
| 2 | 入力、設定、出力、外部 tool の検証エラー |
| 3 | FFmpeg、FFprobe、Shaka Packager の実行エラー |
| 4 | 生成された成果物の検証エラー |
| 130 | 利用者による中断 |

## 失敗時の安全性

出力 root 内に staging directory を作成し、すべての変換と検証が成功した
後にだけ GUID directory へ切り替えます。各実行は新しい GUID を使用するため、
既存 package の置換や削除は行いません。失敗した実行の中間 file は既定で
削除され、`--keep-work-dir` 指定時のみ staging directory に保持されます。

## 開発

Unit test:

```powershell
python -m unittest discover -s tests -v
```

独立した preview server の unit test:

```powershell
python -m unittest discover -s .\tools\preview_server\tests -v
```

Preview server tests は、player page と HLS manifest の配信、streaming file の
MIME type、mount 外および directory traversal access の拒否、package directory
の検証、seek 時の graph sample reset、buffer/ABR 設定、client が segment
download を中断した際の想定内 disconnect 処理を確認します。この test suite は
`src\vod_packager` の unit tests から独立しています。

FFmpeg、FFprobe、Shaka Packager を使用する integration test:

```powershell
$env:VOD_PACKAGER_RUN_INTEGRATION = "1"
python -m unittest tests.test_integration -v
```

## 外部ツールと配布上の注意

この repository と Python package に、FFmpeg、FFprobe、Shaka Packager の
binary、source code、library は含まれていません。また、それらを自動 download
する機能もありません。本ツールは利用者が別途用意した executable を
`subprocess` で起動するだけで、FFmpeg library への静的・動的 link は行いません。

この構成では、本 repository 独自の Python source code は MIT License で
提供できます。FFmpeg は build option により LGPL または GPL が適用され、
既定の `libx264` を含む FFmpeg build は一般に GPL の条件を伴います。
Shaka Packager にも独自の license 条件があります。これらを本ツールと一緒に
installer、container、archive などで再配布する場合は、各 project の license
条件を別途満たし、配布形態を再評価してください。

> [!CAUTION]
> この説明は法的助言ではありません。商用配布、binary 同梱、codec patent
> などが関係する場合は、利用地域の専門家へ確認してください。

## 制限事項

- 対象は単一のローカル入力 file
- 最初の video stream と最初の audio stream のみ使用
- DRM、字幕、複数音声、remote URL、live/low-latency 配信は未対応
- Hardware encoder、deinterlace、HDR tone mapping は未対応
- FFmpeg と Shaka Packager の自動導入は未対応

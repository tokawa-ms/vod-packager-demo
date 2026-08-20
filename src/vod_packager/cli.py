"""Command-line interface."""

import argparse
import sys
from pathlib import Path
from typing import Sequence

from . import __version__
from .errors import INTERRUPTED_EXIT_CODE, VodPackagerError
from .models import PackageOptions
from .pipeline import package_vod


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="vod-packager",
        description="Create multi-bitrate DASH and HLS CMAF VoD packages.",
    )
    parser.add_argument("input", type=Path, help="local input media file")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("output"),
        help="output root directory (default: output)",
    )
    parser.add_argument("--config", type=Path)
    parser.add_argument("--ffmpeg-path", type=Path)
    parser.add_argument("--ffprobe-path", type=Path)
    parser.add_argument("--packager-path", type=Path)
    parser.add_argument("--keep-work-dir", action="store_true")
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("--version", action="version", version=__version__)
    return parser


def parse_args(argv: Sequence[str] | None = None) -> PackageOptions:
    args = build_parser().parse_args(argv)
    return PackageOptions(
        input_path=args.input,
        output_dir=args.output,
        config_path=args.config,
        ffmpeg_path=args.ffmpeg_path,
        ffprobe_path=args.ffprobe_path,
        packager_path=args.packager_path,
        keep_work_dir=args.keep_work_dir,
        verbose=args.verbose,
    )


def main(argv: Sequence[str] | None = None) -> int:
    try:
        output_dir = package_vod(parse_args(argv))
    except KeyboardInterrupt:
        print("error: interrupted", file=sys.stderr)
        return INTERRUPTED_EXIT_CODE
    except VodPackagerError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return exc.exit_code
    print(f"Output: {output_dir}")
    return 0

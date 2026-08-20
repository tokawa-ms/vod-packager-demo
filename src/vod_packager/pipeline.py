"""End-to-end VoD packaging pipeline."""

import shutil
import sys
from pathlib import Path

from .commands import (
    build_audio_command,
    build_packager_command,
    build_video_command,
    select_renditions,
)
from .config import load_config
from .errors import ValidationError
from .layout import create_output_layout, promote_output, validate_output_path
from .models import PackageOptions
from .probe import probe_media
from .process import CommandRunner
from .tools import check_tool_versions, resolve_tools
from .validation import validate_outputs


def _progress(message: str) -> None:
    print(f"[vod-packager] {message}", file=sys.stderr, flush=True)


def _validate_input(input_path: Path) -> Path:
    resolved = input_path.expanduser().resolve()
    if not resolved.is_file():
        raise ValidationError(f"input file does not exist: {resolved}")
    return resolved


def package_vod(options: PackageOptions) -> Path:
    input_path = _validate_input(options.input_path)
    output_root = options.output_dir.expanduser().resolve()
    validate_output_path(input_path, output_root)

    _progress(f"Input: {input_path}")
    _progress("Loading configuration")
    config = load_config(options.config_path)
    _progress("Checking FFmpeg, FFprobe, and Shaka Packager")
    tools = resolve_tools(
        options.ffmpeg_path, options.ffprobe_path, options.packager_path
    )
    runner = CommandRunner(options.verbose)
    check_tool_versions(tools, runner)
    _progress("Probing input media")
    media = probe_media(tools.ffprobe, input_path, runner)
    renditions = select_renditions(media, config)
    _progress(
        f"Source: {media.width}x{media.height}, "
        f"{float(media.frame_rate):.3f} fps, {media.duration:.1f} s, "
        f"audio={'yes' if media.has_audio else 'no'}"
    )
    _progress(
        "Renditions: "
        + ", ".join(f"{rendition.name} ({rendition.height}p)" for rendition in renditions)
    )
    layout = create_output_layout(input_path, output_root, renditions, media.has_audio)
    _progress(f"Run ID: {layout.run_id}")

    succeeded = False
    try:
        for index, rendition in enumerate(renditions, start=1):
            _progress(
                f"[{index}/{len(renditions)}] Encoding video: "
                f"{rendition.name} at {rendition.bitrate}"
            )
            runner.run(
                build_video_command(
                    tools,
                    input_path,
                    layout.video_intermediate(rendition),
                    rendition,
                    media,
                    config,
                )
            )
            _progress(f"[{index}/{len(renditions)}] Video complete: {rendition.name}")
        if media.has_audio:
            _progress(f"Encoding audio: AAC-LC at {config.audio_bitrate}")
            runner.run(
                build_audio_command(
                    tools, input_path, layout.audio_intermediate, config
                )
            )
            _progress("Audio complete")
        else:
            _progress("No audio stream; creating a video-only package")
        _progress("Packaging CMAF segments and DASH/HLS manifests")
        runner.run(
            build_packager_command(
                tools, layout, renditions, media.has_audio, config
            ),
            cwd=layout.staging_dir,
        )
        _progress("Validating generated package")
        validate_outputs(layout, renditions, media.has_audio)
        _progress(f"Publishing run to {layout.output_dir}")
        promote_output(layout)
        succeeded = True
    finally:
        if layout.staging_dir.exists() and (
            succeeded or not options.keep_work_dir
        ):
            try:
                shutil.rmtree(layout.staging_dir)
            except OSError as exc:
                print(
                    f"warning: could not remove staging directory "
                    f"{layout.staging_dir}: {exc}",
                    file=sys.stderr,
                )
    _progress("Completed successfully")
    return layout.output_dir

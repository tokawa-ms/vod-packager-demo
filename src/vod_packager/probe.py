"""FFprobe metadata extraction."""

import json
from fractions import Fraction
from pathlib import Path
from typing import Any

from .errors import ValidationError
from .models import MediaInfo
from .process import CommandRunner


def _positive_int(value: Any, name: str) -> int:
    try:
        result = int(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"invalid {name} in FFprobe output") from exc
    if result <= 0:
        raise ValidationError(f"invalid {name} in FFprobe output")
    return result


def _frame_rate(stream: dict[str, Any]) -> Fraction:
    for field in ("avg_frame_rate", "r_frame_rate"):
        value = stream.get(field)
        if value and value != "0/0":
            try:
                rate = Fraction(value)
            except (ValueError, ZeroDivisionError):
                continue
            if rate > 0:
                return rate
    raise ValidationError("FFprobe did not report a valid video frame rate")


def probe_media(
    ffprobe: Path, input_path: Path, runner: CommandRunner
) -> MediaInfo:
    result = runner.run(
        [
            ffprobe,
            "-v",
            "error",
            "-show_streams",
            "-show_format",
            "-of",
            "json",
            input_path,
        ]
    )
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise ValidationError("FFprobe returned invalid JSON") from exc
    streams = data.get("streams")
    if not isinstance(streams, list):
        raise ValidationError("FFprobe output does not contain streams")
    video = next(
        (stream for stream in streams if stream.get("codec_type") == "video"), None
    )
    if video is None:
        raise ValidationError("input does not contain a video stream")
    audio = any(stream.get("codec_type") == "audio" for stream in streams)
    raw_duration = video.get("duration") or data.get("format", {}).get("duration")
    try:
        duration = float(raw_duration)
    except (TypeError, ValueError) as exc:
        raise ValidationError("FFprobe did not report a valid duration") from exc
    if duration <= 0:
        raise ValidationError("FFprobe did not report a positive duration")
    return MediaInfo(
        width=_positive_int(video.get("width"), "video width"),
        height=_positive_int(video.get("height"), "video height"),
        frame_rate=_frame_rate(video),
        duration=duration,
        has_audio=audio,
    )


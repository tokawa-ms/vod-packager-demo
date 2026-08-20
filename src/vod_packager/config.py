"""Strict JSON configuration loading."""

import json
import re
from pathlib import Path
from typing import Any

from .errors import ValidationError
from .models import EncodingConfig, Rendition

_ROOT_FIELDS = {
    "segment_duration",
    "video_codec",
    "video_preset",
    "audio_bitrate",
    "renditions",
}
_RENDITION_FIELDS = {"name", "height", "bitrate", "maxrate", "bufsize"}
_NAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,31}$")
_BITRATE_PATTERN = re.compile(r"^[1-9][0-9]*[kKmM]$")


def _expect_object(value: Any, context: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValidationError(f"{context} must be a JSON object")
    return value


def _validate_bitrate(value: Any, context: str) -> str:
    if not isinstance(value, str) or not _BITRATE_PATTERN.fullmatch(value):
        raise ValidationError(f"{context} must match {_BITRATE_PATTERN.pattern}")
    return value


def _load_renditions(value: Any) -> tuple[Rendition, ...]:
    if not isinstance(value, list) or not value:
        raise ValidationError("renditions must be a non-empty array")
    renditions: list[Rendition] = []
    names: set[str] = set()
    for index, raw_value in enumerate(value):
        raw = _expect_object(raw_value, f"renditions[{index}]")
        unknown = set(raw) - _RENDITION_FIELDS
        missing = _RENDITION_FIELDS - set(raw)
        if unknown:
            raise ValidationError(
                f"renditions[{index}] has unknown fields: {', '.join(sorted(unknown))}"
            )
        if missing:
            raise ValidationError(
                f"renditions[{index}] is missing fields: {', '.join(sorted(missing))}"
            )
        name = raw["name"]
        if not isinstance(name, str) or not _NAME_PATTERN.fullmatch(name):
            raise ValidationError(f"renditions[{index}].name is invalid")
        if name in names:
            raise ValidationError(f"duplicate rendition name: {name}")
        height = raw["height"]
        if isinstance(height, bool) or not isinstance(height, int) or height <= 0:
            raise ValidationError(f"renditions[{index}].height must be a positive integer")
        renditions.append(
            Rendition(
                name,
                height,
                _validate_bitrate(raw["bitrate"], f"renditions[{index}].bitrate"),
                _validate_bitrate(raw["maxrate"], f"renditions[{index}].maxrate"),
                _validate_bitrate(raw["bufsize"], f"renditions[{index}].bufsize"),
            )
        )
        names.add(name)
    return tuple(renditions)


def load_config(path: Path | None) -> EncodingConfig:
    if path is None:
        return EncodingConfig()
    try:
        raw_value = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ValidationError(f"cannot read config file {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ValidationError(f"invalid JSON in config file {path}: {exc}") from exc
    raw = _expect_object(raw_value, "config")
    unknown = set(raw) - _ROOT_FIELDS
    if unknown:
        raise ValidationError(f"config has unknown fields: {', '.join(sorted(unknown))}")

    defaults = EncodingConfig()
    segment_duration = raw.get("segment_duration", defaults.segment_duration)
    if (
        isinstance(segment_duration, bool)
        or not isinstance(segment_duration, (int, float))
        or segment_duration <= 0
    ):
        raise ValidationError("segment_duration must be a positive number")

    def string_field(name: str, default: str) -> str:
        value = raw.get(name, default)
        if not isinstance(value, str) or not value.strip():
            raise ValidationError(f"{name} must be a non-empty string")
        return value

    return EncodingConfig(
        segment_duration=float(segment_duration),
        video_codec=string_field("video_codec", defaults.video_codec),
        video_preset=string_field("video_preset", defaults.video_preset),
        audio_bitrate=_validate_bitrate(
            raw.get("audio_bitrate", defaults.audio_bitrate), "audio_bitrate"
        ),
        renditions=(
            _load_renditions(raw["renditions"])
            if "renditions" in raw
            else defaults.renditions
        ),
    )


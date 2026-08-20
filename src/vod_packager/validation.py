"""Generated artifact validation."""

from pathlib import Path

from .errors import OutputValidationError
from .models import OutputLayout, Rendition


def _require_file(path: Path) -> None:
    if not path.is_file() or path.stat().st_size == 0:
        raise OutputValidationError(f"required output is missing or empty: {path}")


def _require_segments(directory: Path) -> None:
    segments = tuple(directory.glob("segment_*.m4s"))
    if not segments:
        raise OutputValidationError(f"no media segments were generated in {directory}")
    for segment in segments:
        _require_file(segment)


def validate_outputs(
    layout: OutputLayout,
    renditions: tuple[Rendition, ...],
    has_audio: bool,
) -> None:
    _require_file(layout.final_dir / "manifest.mpd")
    _require_file(layout.final_dir / "master.m3u8")
    for rendition in renditions:
        directory = layout.video_dir(rendition)
        _require_file(directory / "init.mp4")
        _require_file(directory / "playlist.m3u8")
        _require_segments(directory)
    if has_audio:
        _require_file(layout.audio_dir / "init.mp4")
        _require_file(layout.audio_dir / "playlist.m3u8")
        _require_segments(layout.audio_dir)


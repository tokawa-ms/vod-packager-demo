"""Immutable domain models."""

from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path


@dataclass(frozen=True)
class Rendition:
    name: str
    height: int
    bitrate: str
    maxrate: str
    bufsize: str


DEFAULT_RENDITIONS = (
    Rendition("1080p", 1080, "5000k", "5350k", "7500k"),
    Rendition("720p", 720, "2800k", "2996k", "4200k"),
    Rendition("480p", 480, "1400k", "1498k", "2100k"),
    Rendition("360p", 360, "800k", "856k", "1200k"),
)


@dataclass(frozen=True)
class EncodingConfig:
    segment_duration: float = 6.0
    video_codec: str = "libx264"
    video_preset: str = "medium"
    audio_bitrate: str = "128k"
    renditions: tuple[Rendition, ...] = DEFAULT_RENDITIONS


@dataclass(frozen=True)
class MediaInfo:
    width: int
    height: int
    frame_rate: Fraction
    duration: float
    has_audio: bool


@dataclass(frozen=True)
class ToolPaths:
    ffmpeg: Path
    ffprobe: Path
    packager: Path


@dataclass(frozen=True)
class OutputLayout:
    output_root: Path
    output_dir: Path
    run_id: str
    staging_dir: Path
    work_dir: Path
    final_dir: Path

    def video_intermediate(self, rendition: Rendition) -> Path:
        return self.work_dir / f"video_{rendition.name}.mp4"

    @property
    def audio_intermediate(self) -> Path:
        return self.work_dir / "audio.mp4"

    def video_dir(self, rendition: Rendition) -> Path:
        return self.final_dir / "video" / rendition.name

    @property
    def audio_dir(self) -> Path:
        return self.final_dir / "audio"


@dataclass(frozen=True)
class PackageOptions:
    input_path: Path
    output_dir: Path
    config_path: Path | None
    ffmpeg_path: Path | None
    ffprobe_path: Path | None
    packager_path: Path | None
    keep_work_dir: bool
    verbose: bool

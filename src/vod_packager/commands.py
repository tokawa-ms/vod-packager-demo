"""Pure FFmpeg and Shaka Packager command builders."""

from pathlib import Path

from .errors import ValidationError
from .models import EncodingConfig, MediaInfo, OutputLayout, Rendition, ToolPaths


def select_renditions(
    media: MediaInfo, config: EncodingConfig
) -> tuple[Rendition, ...]:
    selected = tuple(
        rendition for rendition in config.renditions if rendition.height <= media.height
    )
    if selected:
        return selected
    source_height = media.height - (media.height % 2)
    if source_height < 2:
        raise ValidationError("video height must be at least 2 pixels")
    smallest = min(config.renditions, key=lambda rendition: rendition.height)
    return (
        Rendition(
            "source",
            source_height,
            smallest.bitrate,
            smallest.maxrate,
            smallest.bufsize,
        ),
    )


def build_video_command(
    tools: ToolPaths,
    input_path: Path,
    output_path: Path,
    rendition: Rendition,
    media: MediaInfo,
    config: EncodingConfig,
) -> list[str]:
    gop = max(1, round(float(media.frame_rate) * config.segment_duration))
    segment_duration = f"{config.segment_duration:g}"
    return [
        str(tools.ffmpeg),
        "-hide_banner",
        "-y",
        "-i",
        str(input_path),
        "-map",
        "0:v:0",
        "-an",
        "-vf",
        f"scale=-2:{rendition.height}",
        "-c:v",
        config.video_codec,
        "-preset",
        config.video_preset,
        "-profile:v",
        "high",
        "-pix_fmt",
        "yuv420p",
        "-b:v",
        rendition.bitrate,
        "-maxrate",
        rendition.maxrate,
        "-bufsize",
        rendition.bufsize,
        "-g",
        str(gop),
        "-keyint_min",
        str(gop),
        "-sc_threshold",
        "0",
        "-force_key_frames",
        f"expr:gte(t,n_forced*{segment_duration})",
        "-movflags",
        "+frag_keyframe+empty_moov+default_base_moof",
        str(output_path),
    ]


def build_audio_command(
    tools: ToolPaths,
    input_path: Path,
    output_path: Path,
    config: EncodingConfig,
) -> list[str]:
    return [
        str(tools.ffmpeg),
        "-hide_banner",
        "-y",
        "-i",
        str(input_path),
        "-map",
        "0:a:0",
        "-vn",
        "-c:a",
        "aac",
        "-profile:a",
        "aac_low",
        "-b:a",
        config.audio_bitrate,
        "-ar",
        "48000",
        "-ac",
        "2",
        "-movflags",
        "+frag_keyframe+empty_moov+default_base_moof",
        str(output_path),
    ]


def _relative(path: Path, layout: OutputLayout) -> str:
    return path.relative_to(layout.staging_dir).as_posix()


def build_packager_command(
    tools: ToolPaths,
    layout: OutputLayout,
    renditions: tuple[Rendition, ...],
    has_audio: bool,
    config: EncodingConfig,
) -> list[str]:
    command = [str(tools.packager)]
    for rendition in renditions:
        output_dir = layout.video_dir(rendition)
        command.append(
            ",".join(
                [
                    f"in={_relative(layout.video_intermediate(rendition), layout)}",
                    "stream=video",
                    f"init_segment={_relative(output_dir / 'init.mp4', layout)}",
                    f"segment_template={_relative(output_dir / 'segment_$Number$.m4s', layout)}",
                    f"playlist_name={_relative(output_dir / 'playlist.m3u8', layout)}",
                ]
            )
        )
    if has_audio:
        command.append(
            ",".join(
                [
                    f"in={_relative(layout.audio_intermediate, layout)}",
                    "stream=audio",
                    f"init_segment={_relative(layout.audio_dir / 'init.mp4', layout)}",
                    f"segment_template={_relative(layout.audio_dir / 'segment_$Number$.m4s', layout)}",
                    f"playlist_name={_relative(layout.audio_dir / 'playlist.m3u8', layout)}",
                    "hls_group_id=audio",
                    "hls_name=English",
                ]
            )
        )
    command.extend(
        [
            "--segment_duration",
            f"{config.segment_duration:g}",
            "--mpd_output",
            _relative(layout.final_dir / "manifest.mpd", layout),
            "--hls_master_playlist_output",
            _relative(layout.final_dir / "master.m3u8", layout),
        ]
    )
    return command

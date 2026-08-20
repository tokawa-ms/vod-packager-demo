import unittest
from fractions import Fraction
from pathlib import Path

from vod_packager.commands import (
    build_audio_command,
    build_packager_command,
    build_video_command,
    select_renditions,
)
from vod_packager.models import (
    EncodingConfig,
    MediaInfo,
    OutputLayout,
    Rendition,
    ToolPaths,
)


class CommandTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tools = ToolPaths(Path("ffmpeg"), Path("ffprobe"), Path("packager"))
        self.config = EncodingConfig()

    def media(self, height: int, width: int = 1920, audio: bool = True) -> MediaInfo:
        return MediaInfo(width, height, Fraction(30000, 1001), 12.0, audio)

    def test_selects_only_non_upscaled_renditions(self) -> None:
        cases = {
            2160: ["1080p", "720p", "480p", "360p"],
            1080: ["1080p", "720p", "480p", "360p"],
            720: ["720p", "480p", "360p"],
            240: ["source"],
        }
        for height, expected in cases.items():
            with self.subTest(height=height):
                self.assertEqual(
                    expected,
                    [r.name for r in select_renditions(self.media(height), self.config)],
                )

    def test_source_fallback_has_even_height_and_custom_bitrate(self) -> None:
        config = EncodingConfig(
            renditions=(Rendition("only-4k", 2160, "9000k", "9500k", "12000k"),)
        )
        selected = select_renditions(self.media(1079), config)
        self.assertEqual(1078, selected[0].height)
        self.assertEqual("9000k", selected[0].bitrate)

    def test_portrait_selection_uses_source_height(self) -> None:
        portrait = self.media(height=1920, width=1080)
        self.assertEqual(
            ["1080p", "720p", "480p", "360p"],
            [r.name for r in select_renditions(portrait, self.config)],
        )

    def test_video_command_aligns_gop_and_preserves_argument_boundaries(self) -> None:
        rendition = Rendition("720p", 720, "2800k", "2996k", "4200k")
        input_path = Path("media files") / "a & b.mp4"
        command = build_video_command(
            self.tools,
            input_path,
            Path("work") / "video.mp4",
            rendition,
            self.media(720),
            self.config,
        )
        self.assertIn(str(input_path), command)
        self.assertEqual("180", command[command.index("-g") + 1])
        self.assertEqual("180", command[command.index("-keyint_min") + 1])
        self.assertEqual(
            "expr:gte(t,n_forced*6)",
            command[command.index("-force_key_frames") + 1],
        )
        self.assertEqual("scale=-2:720", command[command.index("-vf") + 1])

    def test_audio_command_has_explicit_stream_and_format(self) -> None:
        command = build_audio_command(
            self.tools, Path("input.mp4"), Path("audio.mp4"), self.config
        )
        self.assertEqual("0:a:0", command[command.index("-map") + 1])
        self.assertEqual("128k", command[command.index("-b:a") + 1])
        self.assertIn("+frag_keyframe+empty_moov+default_base_moof", command)

    def test_packager_command_contains_dash_hls_and_shared_assets(self) -> None:
        root = Path("stage")
        layout = OutputLayout(
            Path("output-root"),
            Path("output"),
            "00000000-0000-0000-0000-000000000000",
            root,
            root / "work",
            root / "final",
        )
        rendition = Rendition("360p", 360, "800k", "856k", "1200k")
        command = build_packager_command(
            self.tools, layout, (rendition,), True, self.config
        )
        joined = "\n".join(command)
        self.assertIn("init_segment=final/video/360p/init.mp4", joined)
        self.assertIn("playlist_name=final/audio/playlist.m3u8", joined)
        self.assertIn("--mpd_output", command)
        self.assertIn("--hls_master_playlist_output", command)


if __name__ == "__main__":
    unittest.main()

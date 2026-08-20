import json
import subprocess
import unittest
from fractions import Fraction
from pathlib import Path

from vod_packager.errors import ValidationError
from vod_packager.probe import probe_media


class FakeRunner:
    def __init__(self, value: object) -> None:
        self.value = value

    def run(self, args: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess([], 0, json.dumps(self.value), "")


class ProbeTests(unittest.TestCase):
    def test_parses_video_audio_and_fractional_rate(self) -> None:
        runner = FakeRunner(
            {
                "streams": [
                    {
                        "codec_type": "video",
                        "width": 1280,
                        "height": 720,
                        "avg_frame_rate": "30000/1001",
                    },
                    {"codec_type": "audio"},
                ],
                "format": {"duration": "12.5"},
            }
        )
        info = probe_media(Path("ffprobe"), Path("input.mp4"), runner)  # type: ignore[arg-type]
        self.assertEqual(Fraction(30000, 1001), info.frame_rate)
        self.assertTrue(info.has_audio)
        self.assertEqual(12.5, info.duration)

    def test_parses_video_only_and_fallback_rate(self) -> None:
        runner = FakeRunner(
            {
                "streams": [
                    {
                        "codec_type": "video",
                        "width": 640,
                        "height": 360,
                        "avg_frame_rate": "0/0",
                        "r_frame_rate": "25/1",
                        "duration": "3",
                    }
                ],
                "format": {},
            }
        )
        info = probe_media(Path("ffprobe"), Path("input.mp4"), runner)  # type: ignore[arg-type]
        self.assertFalse(info.has_audio)
        self.assertEqual(Fraction(25), info.frame_rate)

    def test_rejects_missing_video_and_invalid_metadata(self) -> None:
        invalid = [
            {"streams": [{"codec_type": "audio"}], "format": {"duration": "1"}},
            {
                "streams": [
                    {
                        "codec_type": "video",
                        "width": 0,
                        "height": 360,
                        "avg_frame_rate": "25/1",
                    }
                ],
                "format": {"duration": "1"},
            },
            {
                "streams": [
                    {
                        "codec_type": "video",
                        "width": 640,
                        "height": 360,
                        "avg_frame_rate": "0/0",
                    }
                ],
                "format": {"duration": "1"},
            },
        ]
        for value in invalid:
            with self.subTest(value=value), self.assertRaises(ValidationError):
                probe_media(
                    Path("ffprobe"),
                    Path("input.mp4"),
                    FakeRunner(value),  # type: ignore[arg-type]
                )


if __name__ == "__main__":
    unittest.main()


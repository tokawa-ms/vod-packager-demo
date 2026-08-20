import json
import tempfile
import unittest
from pathlib import Path

from vod_packager.config import load_config
from vod_packager.errors import ValidationError


class ConfigTests(unittest.TestCase):
    def write_config(self, value: object) -> Path:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name) / "config.json"
        path.write_text(json.dumps(value), encoding="utf-8")
        return path

    def test_defaults(self) -> None:
        config = load_config(None)
        self.assertEqual(6.0, config.segment_duration)
        self.assertEqual(["1080p", "720p", "480p", "360p"], [r.name for r in config.renditions])

    def test_complete_config(self) -> None:
        path = self.write_config(
            {
                "segment_duration": 4,
                "video_codec": "libx264",
                "video_preset": "fast",
                "audio_bitrate": "96k",
                "renditions": [
                    {
                        "name": "540p",
                        "height": 540,
                        "bitrate": "1800k",
                        "maxrate": "1900k",
                        "bufsize": "2700k",
                    }
                ],
            }
        )
        config = load_config(path)
        self.assertEqual(4.0, config.segment_duration)
        self.assertEqual("540p", config.renditions[0].name)

    def test_rejects_unknown_root_field(self) -> None:
        with self.assertRaisesRegex(ValidationError, "unknown fields"):
            load_config(self.write_config({"unexpected": True}))

    def test_rejects_duplicate_and_unsafe_names(self) -> None:
        base = {
            "height": 360,
            "bitrate": "800k",
            "maxrate": "856k",
            "bufsize": "1200k",
        }
        for names in (("../bad",), ("same", "same")):
            with self.subTest(names=names), self.assertRaises(ValidationError):
                load_config(
                    self.write_config(
                        {
                            "renditions": [
                                {"name": name, **base} for name in names
                            ]
                        }
                    )
                )

    def test_rejects_invalid_values_and_json(self) -> None:
        invalid_values = [
            {"segment_duration": 0},
            {"audio_bitrate": "0k"},
            {"audio_bitrate": "128"},
            {"renditions": []},
        ]
        for value in invalid_values:
            with self.subTest(value=value), self.assertRaises(ValidationError):
                load_config(self.write_config(value))

        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name) / "bad.json"
        path.write_text("{", encoding="utf-8")
        with self.assertRaisesRegex(ValidationError, "invalid JSON"):
            load_config(path)


if __name__ == "__main__":
    unittest.main()


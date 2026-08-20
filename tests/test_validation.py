import tempfile
import unittest
from pathlib import Path

from vod_packager.errors import OutputValidationError
from vod_packager.models import OutputLayout, Rendition
from vod_packager.validation import validate_outputs


class ValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        self.layout = OutputLayout(
            root,
            root / "output",
            "00000000-0000-0000-0000-000000000000",
            root / "stage",
            root / "stage" / "work",
            root / "stage" / "final",
        )
        self.rendition = Rendition("360p", 360, "800k", "856k", "1200k")

    @staticmethod
    def write(path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"x")

    def create_valid_output(self, audio: bool) -> None:
        self.write(self.layout.final_dir / "manifest.mpd")
        self.write(self.layout.final_dir / "master.m3u8")
        video = self.layout.video_dir(self.rendition)
        for name in ("init.mp4", "playlist.m3u8", "segment_1.m4s"):
            self.write(video / name)
        if audio:
            for name in ("init.mp4", "playlist.m3u8", "segment_1.m4s"):
                self.write(self.layout.audio_dir / name)

    def test_accepts_complete_audio_video_output(self) -> None:
        self.create_valid_output(True)
        validate_outputs(self.layout, (self.rendition,), True)

    def test_accepts_complete_video_only_output(self) -> None:
        self.create_valid_output(False)
        validate_outputs(self.layout, (self.rendition,), False)

    def test_rejects_every_missing_artifact_class(self) -> None:
        required = [
            self.layout.final_dir / "manifest.mpd",
            self.layout.final_dir / "master.m3u8",
            self.layout.video_dir(self.rendition) / "init.mp4",
            self.layout.video_dir(self.rendition) / "playlist.m3u8",
            self.layout.video_dir(self.rendition) / "segment_1.m4s",
        ]
        for missing in required:
            with self.subTest(missing=missing):
                self.create_valid_output(False)
                missing.unlink()
                with self.assertRaises(OutputValidationError):
                    validate_outputs(self.layout, (self.rendition,), False)


if __name__ == "__main__":
    unittest.main()

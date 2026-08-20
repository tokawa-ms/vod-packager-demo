import os
import shutil
import subprocess
import tempfile
import unittest
import uuid
from pathlib import Path

from vod_packager.cli import main


RUN_INTEGRATION = os.environ.get("VOD_PACKAGER_RUN_INTEGRATION") == "1"


@unittest.skipUnless(RUN_INTEGRATION, "set VOD_PACKAGER_RUN_INTEGRATION=1")
class IntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.ffmpeg = shutil.which("ffmpeg")
        self.ffprobe = shutil.which("ffprobe")
        self.packager = shutil.which("packager")
        if not all((self.ffmpeg, self.ffprobe, self.packager)):
            self.skipTest("ffmpeg, ffprobe, and packager are required")
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)

    def create_input(self, audio: bool) -> Path:
        output = self.root / ("input-av.mp4" if audio else "input-video.mp4")
        command = [
            self.ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            "testsrc2=size=1280x720:rate=30:duration=12",
        ]
        if audio:
            command.extend(
                [
                    "-f",
                    "lavfi",
                    "-i",
                    "sine=frequency=1000:sample_rate=48000:duration=12",
                    "-shortest",
                    "-c:a",
                    "aac",
                ]
            )
        command.extend(["-c:v", "libx264", "-pix_fmt", "yuv420p", str(output)])
        subprocess.run(command, check=True)
        return output

    def run_package(self, input_path: Path, output: Path) -> int:
        return main(
            [
                str(input_path),
                "-o",
                str(output),
                "--ffmpeg-path",
                self.ffmpeg,
                "--ffprobe-path",
                self.ffprobe,
                "--packager-path",
                self.packager,
            ]
        )

    def assert_package(self, output: Path, audio: bool) -> None:
        self.assertGreater((output / "manifest.mpd").stat().st_size, 0)
        self.assertGreater((output / "master.m3u8").stat().st_size, 0)
        for name in ("720p", "480p", "360p"):
            directory = output / "video" / name
            self.assertTrue((directory / "init.mp4").is_file())
            self.assertTrue((directory / "playlist.m3u8").is_file())
            self.assertGreaterEqual(len(tuple(directory.glob("segment_*.m4s"))), 2)
        self.assertEqual(audio, (output / "audio").is_dir())

    @staticmethod
    def run_directories(output_root: Path) -> tuple[Path, ...]:
        return tuple(
            path
            for path in output_root.iterdir()
            if path.is_dir() and not path.name.startswith(".")
        )

    def test_audio_video_end_to_end(self) -> None:
        output_root = self.root / "output-av"
        self.assertEqual(0, self.run_package(self.create_input(True), output_root))
        runs = self.run_directories(output_root)
        self.assertEqual(1, len(runs))
        uuid.UUID(runs[0].name)
        self.assert_package(runs[0], True)
        self.assertFalse(tuple(output_root.glob(".*.staging-*")))

    def test_video_only_end_to_end(self) -> None:
        output_root = self.root / "output-video"
        self.assertEqual(0, self.run_package(self.create_input(False), output_root))
        runs = self.run_directories(output_root)
        self.assertEqual(1, len(runs))
        self.assert_package(runs[0], False)

    def test_repeated_runs_coexist_under_same_output_root(self) -> None:
        output_root = self.root / "output"
        output_root.mkdir()
        marker = output_root / "marker.txt"
        marker.write_text("preserved", encoding="utf-8")
        input_path = self.create_input(False)
        self.assertEqual(0, self.run_package(input_path, output_root))
        self.assertEqual(0, self.run_package(input_path, output_root))
        self.assertEqual("preserved", marker.read_text(encoding="utf-8"))
        runs = self.run_directories(output_root)
        self.assertEqual(2, len(runs))
        self.assertNotEqual(runs[0].name, runs[1].name)
        for run in runs:
            uuid.UUID(run.name)
            self.assert_package(run, False)


if __name__ == "__main__":
    unittest.main()

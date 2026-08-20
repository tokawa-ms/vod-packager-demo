import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from vod_packager.cli import main, parse_args
from vod_packager.errors import (
    ExternalCommandError,
    OutputValidationError,
    ValidationError,
)


class CliTests(unittest.TestCase):
    def test_parse_all_options(self) -> None:
        options = parse_args(
            [
                "input.mp4",
                "-o",
                "out",
                "--config",
                "config.json",
                "--ffmpeg-path",
                "ffmpeg-custom",
                "--ffprobe-path",
                "ffprobe-custom",
                "--packager-path",
                "packager-custom",
                "--keep-work-dir",
                "--verbose",
            ]
        )
        self.assertEqual(Path("input.mp4"), options.input_path)
        self.assertTrue(options.keep_work_dir)

    def test_output_defaults_to_output_directory(self) -> None:
        options = parse_args(["input.mp4"])
        self.assertEqual(Path("output"), options.output_dir)

    def test_maps_application_errors_to_exit_codes(self) -> None:
        errors = [
            (ValidationError("bad input"), 2),
            (ExternalCommandError("ffmpeg", 1, "failed"), 3),
            (OutputValidationError("missing"), 4),
        ]
        for error, expected in errors:
            with (
                self.subTest(error=error),
                patch("vod_packager.cli.package_vod", side_effect=error),
                patch("sys.stderr", new=io.StringIO()),
            ):
                self.assertEqual(expected, main(["input.mp4"]))

    def test_maps_keyboard_interrupt(self) -> None:
        with (
            patch("vod_packager.cli.package_vod", side_effect=KeyboardInterrupt),
            patch("sys.stderr", new=io.StringIO()),
        ):
            self.assertEqual(130, main(["input.mp4"]))

    def test_prints_completed_output_path(self) -> None:
        stdout = io.StringIO()
        with (
            patch(
                "vod_packager.cli.package_vod",
                return_value=Path("output") / "00000000-0000-0000-0000-000000000000",
            ),
            patch("sys.stdout", new=stdout),
        ):
            self.assertEqual(0, main(["input.mp4"]))
        self.assertIn(
            "Output: output\\00000000-0000-0000-0000-000000000000",
            stdout.getvalue(),
        )


if __name__ == "__main__":
    unittest.main()

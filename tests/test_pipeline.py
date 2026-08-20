import io
import tempfile
import unittest
from fractions import Fraction
from pathlib import Path
from unittest.mock import Mock, patch

from vod_packager.errors import ExternalCommandError
from vod_packager.models import MediaInfo, PackageOptions, ToolPaths
from vod_packager.pipeline import package_vod


class PipelineTests(unittest.TestCase):
    def options(
        self, input_path: Path, output: Path, keep_work_dir: bool
    ) -> PackageOptions:
        return PackageOptions(
            input_path=input_path,
            output_dir=output,
            config_path=None,
            ffmpeg_path=None,
            ffprobe_path=None,
            packager_path=None,
            keep_work_dir=keep_work_dir,
            verbose=False,
        )

    def test_packager_failure_preserves_output_root_and_cleans_stage(self) -> None:
        for keep_work_dir in (False, True):
            with self.subTest(keep_work_dir=keep_work_dir):
                temporary = tempfile.TemporaryDirectory()
                self.addCleanup(temporary.cleanup)
                root = Path(temporary.name)
                input_path = root / "input.mp4"
                input_path.write_bytes(b"input")
                output = root / "output"
                output.mkdir()
                marker = output / "marker"
                marker.write_bytes(b"preserved")

                runner = Mock()
                runner.run.side_effect = [
                    None,
                    ExternalCommandError("packager", 1, "simulated failure"),
                ]
                tools = ToolPaths(Path("ffmpeg"), Path("ffprobe"), Path("packager"))
                media = MediaInfo(640, 360, Fraction(30), 12.0, False)
                with (
                    patch("vod_packager.pipeline.resolve_tools", return_value=tools),
                    patch("vod_packager.pipeline.CommandRunner", return_value=runner),
                    patch("vod_packager.pipeline.check_tool_versions"),
                    patch("vod_packager.pipeline.probe_media", return_value=media),
                    patch("sys.stderr", new=io.StringIO()) as stderr,
                ):
                    with self.assertRaises(ExternalCommandError):
                        package_vod(self.options(input_path, output, keep_work_dir))

                self.assertEqual(b"preserved", marker.read_bytes())
                self.assertIn("[1/1] Encoding video: 360p", stderr.getvalue())
                self.assertIn("Packaging CMAF segments", stderr.getvalue())
                stages = tuple(output.glob(".*.staging-*"))
                self.assertEqual(1 if keep_work_dir else 0, len(stages))


if __name__ == "__main__":
    unittest.main()

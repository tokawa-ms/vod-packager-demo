import unittest
from pathlib import Path
from unittest.mock import patch

from vod_packager.errors import ToolNotFoundError
from vod_packager.process import CommandRunner


class ProcessTests(unittest.TestCase):
    def test_maps_process_start_failure_to_validation_error(self) -> None:
        with patch("vod_packager.process.subprocess.Popen", side_effect=OSError("bad executable")):
            with self.assertRaisesRegex(ToolNotFoundError, "could not start"):
                CommandRunner().run([Path("not-an-executable")])


if __name__ == "__main__":
    unittest.main()


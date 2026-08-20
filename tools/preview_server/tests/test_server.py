import io
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import urlopen

TOOL_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOL_DIR))

from server import PreviewHTTPServer, PreviewRequestHandler, PreviewServerError
from server import validate_package_dir


class ServerTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.package_dir = Path(temporary.name).resolve()
        (self.package_dir / "master.m3u8").write_bytes(b"#EXTM3U\n")

        handler = lambda *args, **kwargs: PreviewRequestHandler(
            *args, package_dir=self.package_dir, **kwargs
        )
        self.server = PreviewHTTPServer(("127.0.0.1", 0), handler)
        self.addCleanup(self.server.server_close)
        thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(self.server.shutdown)
        self.base_url = f"http://127.0.0.1:{self.server.server_port}"

    def test_serves_player_and_hls_manifest_with_correct_content_types(self) -> None:
        with urlopen(f"{self.base_url}/") as response:
            page = response.read().decode("utf-8")
            self.assertEqual("text/html; charset=utf-8", response.headers["Content-Type"])
        self.assertIn("plyr@3.8.4", page)
        self.assertIn("hls.js@1.7.0", page)
        self.assertIn("/media/master.m3u8", page)
        self.assertIn("'settings'", page)
        self.assertIn("qualityLabel: { 0: 'Auto' }", page)
        self.assertIn("plyr@3.8.4/dist/plyr.svg", page)
        self.assertIn('id="bitrate-chart"', page)
        self.assertIn("Hls.Events.LEVEL_SWITCHED", page)
        self.assertIn("samples.set(Math.floor(video.currentTime)", page)
        self.assertIn("maxBufferLength: 12", page)
        self.assertIn("maxMaxBufferLength: 12", page)
        self.assertIn("abrEwmaFastVoD: 1", page)
        self.assertIn('id="buffer-depth"', page)
        self.assertIn("truncateSamplesAtSeekPosition", page)
        self.assertIn("'seeking', truncateSamplesAtSeekPosition", page)
        self.assertIn("height: 100dvh", page)
        self.assertIn("overflow: hidden", page)
        self.assertIn("grid-template-rows: auto minmax(0, 1fr)", page)

        with urlopen(f"{self.base_url}/media/master.m3u8") as response:
            self.assertEqual(
                "application/vnd.apple.mpegurl",
                response.headers["Content-Type"],
            )
            self.assertEqual(b"#EXTM3U\n", response.read())

        with urlopen(f"{self.base_url}/") as response:
            self.assertIn(
                "connect-src 'self' blob: https://cdn.jsdelivr.net",
                response.headers["Content-Security-Policy"],
            )
            self.assertIn(
                "worker-src 'self' blob:",
                response.headers["Content-Security-Policy"],
            )

    def test_rejects_unmounted_and_parent_paths(self) -> None:
        for path in ("/master.m3u8", "/media/../master.m3u8"):
            with self.subTest(path=path), self.assertRaises(HTTPError) as context:
                urlopen(f"{self.base_url}{path}")
            self.assertEqual(404, context.exception.code)

    def test_validates_package_directory(self) -> None:
        self.assertEqual(self.package_dir, validate_package_dir(self.package_dir))
        (self.package_dir / "master.m3u8").unlink()
        with self.assertRaises(PreviewServerError):
            validate_package_dir(self.package_dir)

    def test_suppresses_expected_client_disconnect_tracebacks(self) -> None:
        stderr = io.StringIO()
        with patch("sys.stderr", stderr):
            for exception_type in (
                BrokenPipeError,
                ConnectionAbortedError,
                ConnectionResetError,
            ):
                with self.subTest(exception_type=exception_type):
                    try:
                        raise exception_type("client cancelled the request")
                    except exception_type:
                        self.server.handle_error(object(), ("127.0.0.1", 12345))
        self.assertEqual("", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()

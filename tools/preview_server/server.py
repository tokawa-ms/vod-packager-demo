"""Standalone localhost server for previewing generated HLS packages."""

import argparse
import sys
import webbrowser
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Sequence
from urllib.parse import unquote, urlsplit

PLAYER_FILE = Path(__file__).with_name("player.html")


class PreviewServerError(Exception):
    pass


class PreviewHTTPServer(ThreadingHTTPServer):
    daemon_threads = True

    def handle_error(
        self,
        request: object,
        client_address: tuple[str, int],
    ) -> None:
        exception = sys.exc_info()[1]
        if isinstance(
            exception,
            (BrokenPipeError, ConnectionAbortedError, ConnectionResetError),
        ):
            return
        super().handle_error(request, client_address)


class PreviewRequestHandler(SimpleHTTPRequestHandler):
    extensions_map = {
        **SimpleHTTPRequestHandler.extensions_map,
        ".m3u8": "application/vnd.apple.mpegurl",
        ".mpd": "application/dash+xml",
        ".m4s": "video/iso.segment",
        ".mp4": "video/mp4",
    }

    def __init__(
        self,
        *args: object,
        package_dir: Path,
        verbose: bool = False,
        **kwargs: object,
    ) -> None:
        self.package_dir = package_dir
        self.verbose = verbose
        super().__init__(*args, directory=str(package_dir), **kwargs)

    def do_GET(self) -> None:
        if urlsplit(self.path).path == "/":
            self._send_player(include_body=True)
            return
        if not urlsplit(self.path).path.startswith("/media/"):
            self.send_error(404)
            return
        super().do_GET()

    def do_HEAD(self) -> None:
        if urlsplit(self.path).path == "/":
            self._send_player(include_body=False)
            return
        if not urlsplit(self.path).path.startswith("/media/"):
            self.send_error(404)
            return
        super().do_HEAD()

    def translate_path(self, path: str) -> str:
        request_path = unquote(urlsplit(path).path)
        relative_parts = request_path.removeprefix("/media/").split("/")
        candidate = self.package_dir.joinpath(*relative_parts).resolve()
        try:
            candidate.relative_to(self.package_dir)
        except ValueError:
            return str(self.package_dir / ".invalid-path")
        return str(candidate)

    def end_headers(self) -> None:
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cache-Control", "no-cache")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; script-src 'self' https://cdn.jsdelivr.net "
            "'unsafe-inline'; style-src 'self' https://cdn.jsdelivr.net "
            "'unsafe-inline'; media-src 'self' blob:; connect-src 'self' blob: "
            "https://cdn.jsdelivr.net; worker-src 'self' blob:; "
            "img-src 'self' data:",
        )
        super().end_headers()

    def log_message(self, format: str, *args: object) -> None:
        if self.verbose:
            super().log_message(format, *args)

    def _send_player(self, *, include_body: bool) -> None:
        body = PLAYER_FILE.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if include_body:
            self.wfile.write(body)


def validate_package_dir(package_dir: Path) -> Path:
    resolved = package_dir.expanduser().resolve()
    if not resolved.is_dir():
        raise PreviewServerError(f"package directory does not exist: {package_dir}")
    if not (resolved / "master.m3u8").is_file():
        raise PreviewServerError(f"master.m3u8 was not found in: {package_dir}")
    return resolved


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Preview a generated HLS package with Plyr.",
    )
    parser.add_argument("package", type=Path, help="directory containing master.m3u8")
    parser.add_argument("--port", type=int, default=8000, help="port (default: 8000)")
    parser.add_argument(
        "--open-browser",
        action="store_true",
        help="open the preview page in the default browser",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    return parser


def serve_package(
    package_dir: Path,
    *,
    port: int = 8000,
    open_browser: bool = False,
    verbose: bool = False,
) -> None:
    if not 1 <= port <= 65535:
        raise PreviewServerError("port must be between 1 and 65535")

    resolved = validate_package_dir(package_dir)
    handler = partial(
        PreviewRequestHandler,
        package_dir=resolved,
        verbose=verbose,
    )
    with PreviewHTTPServer(("127.0.0.1", port), handler) as server:
        url = f"http://localhost:{port}/"
        print(f"Serving: {resolved}")
        print(f"Player:  {url}")
        print("Press Ctrl+C to stop.")
        if open_browser:
            webbrowser.open(url)
        server.serve_forever()


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        serve_package(
            args.package,
            port=args.port,
            open_browser=args.open_browser,
            verbose=args.verbose,
        )
    except KeyboardInterrupt:
        print("\nStopped.", file=sys.stderr)
        return 130
    except (PreviewServerError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""External executable discovery."""

import shutil
from pathlib import Path

from .errors import ToolNotFoundError
from .models import ToolPaths
from .process import CommandRunner


def _resolve(explicit: Path | None, name: str) -> Path:
    if explicit is not None:
        candidate = explicit.expanduser().resolve()
        if not candidate.is_file():
            raise ToolNotFoundError(f"{name} executable does not exist: {candidate}")
        return candidate
    discovered = shutil.which(name)
    if discovered is None:
        raise ToolNotFoundError(
            f"{name} executable was not found; add it to PATH or use --{name}-path"
        )
    return Path(discovered).resolve()


def resolve_tools(
    ffmpeg_path: Path | None,
    ffprobe_path: Path | None,
    packager_path: Path | None,
) -> ToolPaths:
    return ToolPaths(
        _resolve(ffmpeg_path, "ffmpeg"),
        _resolve(ffprobe_path, "ffprobe"),
        _resolve(packager_path, "packager"),
    )


def check_tool_versions(tools: ToolPaths, runner: CommandRunner) -> None:
    runner.run([tools.ffmpeg, "-version"])
    runner.run([tools.ffprobe, "-version"])
    runner.run([tools.packager, "--version"])


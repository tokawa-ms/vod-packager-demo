"""Safe external process execution."""

import os
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Sequence

from .errors import ExternalCommandError, ToolNotFoundError


class CommandRunner:
    def __init__(self, verbose: bool = False) -> None:
        self.verbose = verbose
        self._process: subprocess.Popen[str] | None = None

    def _display(self, args: Sequence[str]) -> str:
        return subprocess.list2cmdline(args) if os.name == "nt" else shlex.join(args)

    def run(
        self, args: Sequence[str | Path], cwd: Path | None = None
    ) -> subprocess.CompletedProcess[str]:
        command = [str(arg) for arg in args]
        if self.verbose:
            print(f"+ {self._display(command)}", file=sys.stderr)
        try:
            try:
                self._process = subprocess.Popen(
                    command,
                    cwd=cwd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    shell=False,
                )
            except OSError as exc:
                raise ToolNotFoundError(
                    f"could not start executable {command[0]}: {exc}"
                ) from exc
            stdout, stderr = self._process.communicate()
            returncode = self._process.returncode
        except KeyboardInterrupt:
            self.stop()
            raise
        finally:
            self._process = None
        if returncode:
            raise ExternalCommandError(Path(command[0]).name, returncode, stderr)
        if self.verbose and stderr.strip():
            print(stderr.rstrip(), file=sys.stderr)
        return subprocess.CompletedProcess(command, returncode, stdout, stderr)

    def stop(self) -> None:
        process = self._process
        if process is None or process.poll() is not None:
            return
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()

"""Application-specific errors and exit codes."""

VALIDATION_EXIT_CODE = 2
EXTERNAL_COMMAND_EXIT_CODE = 3
OUTPUT_VALIDATION_EXIT_CODE = 4
INTERRUPTED_EXIT_CODE = 130


class VodPackagerError(Exception):
    exit_code = VALIDATION_EXIT_CODE


class ValidationError(VodPackagerError):
    pass


class ToolNotFoundError(ValidationError):
    pass


class ExternalCommandError(VodPackagerError):
    exit_code = EXTERNAL_COMMAND_EXIT_CODE

    def __init__(self, command: str, returncode: int, stderr: str) -> None:
        self.command = command
        self.returncode = returncode
        self.stderr = stderr
        detail = stderr.strip()[-4000:] or "no error output"
        super().__init__(f"{command} failed with exit code {returncode}:\n{detail}")


class OutputValidationError(VodPackagerError):
    exit_code = OUTPUT_VALIDATION_EXIT_CODE


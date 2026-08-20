"""Output layout creation and path safety."""

import os
import uuid
from pathlib import Path

from .errors import ValidationError
from .models import OutputLayout, Rendition


def validate_output_path(input_path: Path, output_dir: Path) -> None:
    resolved = output_dir.expanduser().resolve()
    anchor = Path(resolved.anchor)
    if resolved == anchor:
        raise ValidationError("output directory cannot be a filesystem root")
    if resolved == Path.cwd().resolve():
        raise ValidationError("output directory cannot be the current directory")
    if resolved == input_path.resolve().parent:
        raise ValidationError("output directory cannot be the input file's parent")


def create_output_layout(
    input_path: Path,
    output_root: Path,
    renditions: tuple[Rendition, ...],
    has_audio: bool,
) -> OutputLayout:
    root = output_root.expanduser().resolve()
    validate_output_path(input_path, root)
    root.mkdir(parents=True, exist_ok=True)
    while True:
        run_id = str(uuid.uuid4())
        output = root / run_id
        staging = root / f".{run_id}.staging-work"
        if not output.exists() and not staging.exists():
            break
    layout = OutputLayout(
        root,
        output,
        run_id,
        staging,
        staging / "work",
        staging / "final",
    )
    layout.work_dir.mkdir(parents=True)
    layout.final_dir.mkdir()
    for rendition in renditions:
        layout.video_dir(rendition).mkdir(parents=True)
    if has_audio:
        layout.audio_dir.mkdir(parents=True)
    return layout


def promote_output(layout: OutputLayout) -> None:
    if layout.output_dir.exists():
        raise ValidationError(f"run output directory already exists: {layout.output_dir}")
    try:
        os.replace(layout.final_dir, layout.output_dir)
    except OSError as exc:
        raise ValidationError(f"could not promote staged output: {exc}") from exc

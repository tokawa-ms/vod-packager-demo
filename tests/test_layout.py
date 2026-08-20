import tempfile
import unittest
import uuid
from pathlib import Path

from vod_packager.errors import ValidationError
from vod_packager.layout import create_output_layout, promote_output, validate_output_path
from vod_packager.models import OutputLayout, Rendition


class LayoutTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.input_path = self.root / "input.mp4"
        self.input_path.write_bytes(b"x")
        self.rendition = Rendition("360p", 360, "800k", "856k", "1200k")

    def test_rejects_input_parent_as_output_root(self) -> None:
        with self.assertRaises(ValidationError):
            validate_output_path(self.input_path, self.root)

    def test_creates_unique_guid_run_directories(self) -> None:
        output_root = self.root / "output"
        first = create_output_layout(
            self.input_path, output_root, (self.rendition,), False
        )
        second = create_output_layout(
            self.input_path, output_root, (self.rendition,), False
        )
        self.assertNotEqual(first.run_id, second.run_id)
        self.assertEqual(first.run_id, str(uuid.UUID(first.run_id)))
        self.assertEqual(output_root.resolve(), first.output_dir.parent)
        self.assertEqual(output_root.resolve(), second.output_dir.parent)

    def test_promotes_run_without_replacing_siblings(self) -> None:
        output_root = self.root / "output"
        output_root.mkdir()
        sibling = output_root / str(uuid.uuid4())
        sibling.mkdir()
        (sibling / "marker").write_text("preserved", encoding="utf-8")
        stage = output_root / ".run.staging-work"
        final = stage / "final"
        final.mkdir(parents=True)
        (final / "new").write_text("new", encoding="utf-8")
        run_id = str(uuid.uuid4())
        layout = OutputLayout(
            output_root,
            output_root / run_id,
            run_id,
            stage,
            stage / "work",
            final,
        )
        promote_output(layout)
        self.assertEqual("new", (layout.output_dir / "new").read_text(encoding="utf-8"))
        self.assertEqual("preserved", (sibling / "marker").read_text(encoding="utf-8"))

    def test_refuses_to_replace_colliding_run_directory(self) -> None:
        output_root = self.root / "output"
        output_root.mkdir()
        run_id = str(uuid.uuid4())
        output = output_root / run_id
        output.mkdir()
        stage = output_root / ".run.staging-work"
        final = stage / "final"
        final.mkdir(parents=True)
        layout = OutputLayout(
            output_root,
            output,
            run_id,
            stage,
            stage / "work",
            final,
        )
        with self.assertRaisesRegex(ValidationError, "already exists"):
            promote_output(layout)


if __name__ == "__main__":
    unittest.main()

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location("sync_xcode_ai", Path(__file__).resolve().parents[1] / "scripts/sync_xcode_ai.py")
sync = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(sync)


class SyncSafetyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def write(self, name, content):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return path

    def apply(self, files):
        changes, conflicts = sync.plan(self.root, files)
        sync.apply_files(self.root, files, {"xcode_build": "fixture"}, changes, conflicts)

    def test_skills_mirror_overwrites_local_edits_and_removes_retired_skills(self):
        old = self.write("skills/retired/SKILL.md", b"old")
        current = self.write("skills/apple/SKILL.md", b"local customization")
        files = {"skills/apple/SKILL.md": b"Apple export\r\nexact bytes\n"}
        self.apply(files)
        self.assertEqual(current.read_bytes(), files["skills/apple/SKILL.md"])
        self.assertFalse(old.parent.exists())
        backups = list((self.root / ".xcode-ai/backups").glob("*/skills/apple/SKILL.md"))
        self.assertEqual(backups[0].read_bytes(), b"local customization")

    def test_second_sync_has_no_changes(self):
        files = {"skills/apple/SKILL.md": b"upstream", "xcode-ai/prompts/a": b"template"}
        self.apply(files)
        changes, conflicts = sync.plan(self.root, files)
        self.assertFalse(any(changes.values()))
        self.assertEqual(conflicts, [])

    def test_prompt_conflict_stops_entire_apply_before_touching_skills(self):
        files = {"skills/apple/SKILL.md": b"v1", "xcode-ai/prompts/a": b"original"}
        self.apply(files)
        self.write("xcode-ai/prompts/a", b"local prompt")
        incoming = {"skills/apple/SKILL.md": b"v2", "xcode-ai/prompts/a": b"new prompt"}
        with self.assertRaises(RuntimeError):
            self.apply(incoming)
        self.assertEqual((self.root / "skills/apple/SKILL.md").read_bytes(), b"v1")
        self.assertEqual((self.root / "xcode-ai/prompts/a").read_bytes(), b"local prompt")

    def test_adoption_does_not_override_tracked_prompt_conflict(self):
        self.apply({"xcode-ai/prompts/a": b"original"})
        self.write("xcode-ai/prompts/a", b"local")
        _, conflicts = sync.plan(self.root, {"xcode-ai/prompts/a": b"new"}, adopt=True)
        self.assertEqual(conflicts, ["xcode-ai/prompts/a"])

    def test_deletion_leaves_unmanaged_non_skill_files(self):
        self.apply({"xcode-ai/prompts/old": b"old"})
        self.write("xcode-ai/custom-note", b"mine")
        self.apply({})
        self.assertFalse((self.root / "xcode-ai/prompts/old").exists())
        self.assertEqual((self.root / "xcode-ai/custom-note").read_bytes(), b"mine")

    def test_path_traversal_and_symlink_are_rejected(self):
        for name in ("../outside", "/tmp/outside", "README.md", "skills/../outside"):
            with self.assertRaises(RuntimeError):
                sync.destination(self.root, name)
        with tempfile.TemporaryDirectory() as other:
            (self.root / "skills").symlink_to(other, target_is_directory=True)
            with self.assertRaises(RuntimeError):
                sync.destination(self.root, "skills/apple/SKILL.md")

    def test_write_failure_rolls_back_files_and_lock(self):
        self.apply({"skills/apple/SKILL.md": b"v1"})
        old_lock = (self.root / sync.LOCK).read_bytes()
        original_write = Path.write_bytes
        failed = False

        def fail_once(path, content):
            nonlocal failed
            if path == self.root / sync.LOCK and not failed:
                failed = True
                raise OSError("simulated disk failure")
            return original_write(path, content)

        with patch.object(Path, "write_bytes", fail_once):
            with self.assertRaises(OSError):
                self.apply({"skills/apple/SKILL.md": b"v2", "skills/new/SKILL.md": b"new"})
        self.assertEqual((self.root / "skills/apple/SKILL.md").read_bytes(), b"v1")
        self.assertFalse((self.root / "skills/new/SKILL.md").exists())
        self.assertEqual((self.root / sync.LOCK).read_bytes(), old_lock)


if __name__ == "__main__":
    unittest.main()

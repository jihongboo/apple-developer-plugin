import importlib.util
from pathlib import Path
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location("sync_prompt_test", Path(__file__).resolve().parents[1] / "scripts/sync_xcode_ai.py")
sync = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(sync)


class PromptReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "rules").mkdir()
        self.rules = self.root / "rules/apple.md"
        self.rules.write_text("Local note\n" + sync.SUMMARY_START +
                              "\n[Source](../xcode-ai/prompts/core.idechatprompttemplate)\n" + sync.SUMMARY_END)
        self.files = {"xcode-ai/prompts/core.idechatprompttemplate": b"upstream",
                      "xcode-ai/source.json": sync.json_bytes({"xcode_version": "27.1", "xcode_build": "fixture"})}

    def record(self):
        sync.mark_prompt_review(self.root, self.files, "Reviewed source; omitted host-specific output constraints")

    def test_source_edit_requires_review_without_rewriting_rules(self):
        self.record()
        before = self.rules.read_bytes()
        self.files["xcode-ai/prompts/core.idechatprompttemplate"] = b"updated"
        output = self.root / ".xcode-ai/review.md"
        status = sync.write_prompt_review(self.root, self.files, output)
        self.assertEqual(status["status"], "pending")
        self.assertEqual(status["changed"], ["xcode-ai/prompts/core.idechatprompttemplate"])
        self.assertEqual(self.rules.read_bytes(), before)

    def test_added_and_removed_sources_require_review(self):
        self.record()
        del self.files["xcode-ai/prompts/core.idechatprompttemplate"]
        self.files["xcode-ai/prompts/new.idechatprompttemplate"] = b"new"
        status = sync.prompt_review_status(self.root, self.files)
        self.assertEqual(len(status["added"]), 1)
        self.assertEqual(len(status["removed"]), 1)

    def test_summary_and_version_changes_require_review_but_manual_notes_do_not(self):
        self.record()
        self.rules.write_text(self.rules.read_text().replace("Local note", "Updated local note"))
        self.assertEqual(sync.prompt_review_status(self.root, self.files)["status"], "current")
        self.rules.write_text(self.rules.read_text().replace("[Source]", "Adapted guidance [Source]"))
        self.assertTrue(sync.prompt_review_status(self.root, self.files)["summary_changed"])
        self.record()
        self.files["xcode-ai/source.json"] = sync.json_bytes({"xcode_version": "27.2", "xcode_build": "new"})
        self.assertTrue(sync.prompt_review_status(self.root, self.files)["version_changed"])

    def test_missing_source_link_cannot_be_marked_reviewed(self):
        self.rules.write_text(self.rules.read_text().replace("core.idechatprompttemplate", "missing.idechatprompttemplate"))
        with self.assertRaises(RuntimeError):
            self.record()
        self.assertFalse((self.root / sync.PROMPT_REVIEW).exists())

    def test_apple_mirror_preserves_entry_skill_and_project_rules(self):
        entry = self.root / "plugin-skills/apple-development/SKILL.md"
        entry.parent.mkdir(parents=True)
        entry.write_bytes(b"entry")
        files = {"skills/apple/SKILL.md": b"Apple original"}
        changes, conflicts = sync.plan(self.root, files)
        original_rules = self.rules.read_bytes()
        sync.apply_files(self.root, files, {}, changes, conflicts)
        self.assertEqual(entry.read_bytes(), b"entry")
        self.assertEqual(self.rules.read_bytes(), original_rules)


if __name__ == "__main__":
    unittest.main()

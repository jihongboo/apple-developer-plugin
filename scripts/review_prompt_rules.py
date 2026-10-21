#!/usr/bin/env python3
"""Prepare prompt review evidence; record a completed semantic review explicitly."""
import argparse
import sys
from sync_xcode_ai import (ROOT, collect_files, mark_prompt_review,
                           prompt_review_status, write_prompt_review)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Check review freshness without modifying files")
    parser.add_argument("--mark-reviewed", action="store_true", help="Record a completed review; does not generate or validate the summary's meaning")
    parser.add_argument("--note", help="Record selected sources, exclusions and adaptation rationale")
    args = parser.parse_args()
    if args.check and args.mark_reviewed:
        parser.error("--check and --mark-reviewed are mutually exclusive")
    if args.mark_reviewed and not (args.note and args.note.strip()):
        parser.error("--mark-reviewed requires a nonempty --note describing the review")
    files = collect_files(ROOT / "xcode-ai/prompts", "xcode-ai/prompts")
    files["xcode-ai/source.json"] = (ROOT / "xcode-ai/source.json").read_bytes()
    if args.mark_reviewed:
        mark_prompt_review(ROOT, files, args.note.strip())
    status = prompt_review_status(ROOT, files)
    if not args.check:
        path = ROOT / ".xcode-ai/prompt-review.md"
        write_prompt_review(ROOT, files, path)
        print(f"Review packet: {path}")
    print(f"Prompt rules review: {status['status']}; added={len(status['added'])}, changed={len(status['changed'])}, removed={len(status['removed'])}")
    if args.check and status["status"] != "current":
        return 1
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (RuntimeError, OSError, ValueError, KeyError) as error:
        print(f"Review failed: {error}", file=sys.stderr)
        sys.exit(1)

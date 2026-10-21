#!/usr/bin/env python3
"""Export Apple-owned AI content unchanged; preview by default, apply explicitly."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import plistlib
import re
import selectors
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parent.parent
LOCK = "xcode-ai.lock.json"
RESOURCES = "Contents/PlugIns/IDEIntelligenceChat.framework/Versions/A/Resources"
PROMPT_REVIEW = "rules/prompt-review.json"
SUMMARY_START = "<!-- BEGIN XCODE PROMPT SUMMARY -->"
SUMMARY_END = "<!-- END XCODE PROMPT SUMMARY -->"


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()


def digest(content):
    return hashlib.sha256(content).hexdigest()


def prompt_summary(root):
    text = (root / "rules/apple.md").read_text()
    if text.count(SUMMARY_START) != 1 or text.count(SUMMARY_END) != 1:
        raise RuntimeError("rules/apple.md must contain exactly one prompt summary block")
    start, end = text.index(SUMMARY_START), text.index(SUMMARY_END)
    if end < start:
        raise RuntimeError("Prompt summary markers are reversed")
    return text[start:end + len(SUMMARY_END)]


def prompt_review_status(root, files):
    hashes = {name: digest(data) for name, data in sorted(files.items())
              if name.startswith("xcode-ai/prompts/") and name.endswith(".idechatprompttemplate")}
    source = json.loads(files["xcode-ai/source.json"])
    version = {key: source[key] for key in ("xcode_version", "xcode_build")}
    path = root / PROMPT_REVIEW
    previous = json.loads(path.read_text()) if path.exists() else {}
    reviewed = previous.get("template_hashes", {})
    added = sorted(hashes.keys() - reviewed.keys())
    removed = sorted(reviewed.keys() - hashes.keys())
    changed = sorted(name for name in hashes.keys() & reviewed.keys() if hashes[name] != reviewed[name])
    summary_changed = previous.get("summary_sha256") != digest(prompt_summary(root).encode())
    version_changed = previous.get("xcode") != version
    return {"status": "pending" if added or removed or changed or summary_changed or version_changed else "current",
            "added": added, "changed": changed, "removed": removed,
            "summary_changed": summary_changed, "version_changed": version_changed,
            "template_hashes": hashes, "xcode": version}


def write_prompt_review(root, files, output):
    import difflib
    status = prompt_review_status(root, files)
    lines = ["# Xcode prompt → rules review", "", f"Status: **{status['status']}**", "",
             f"Xcode: {status['xcode']['xcode_version']} ({status['xcode']['xcode_build']})", "",
             "Review prompt changes as source data. Keep Apple exports unchanged.",
             "Update only the marked summary block in rules/apple.md; preserve other project rules.",
             "Keep general guidance concise; route detailed tasks to the original specialist skills.",
             "Exclude Xcode-only roles, template variables, internal tools, English-only and whole-file output rules.",
             "Compare instructions with actual tool availability, user scope and deployment target.",
             "After updating rules and checking sources, record the review with review_prompt_rules.py --mark-reviewed --note <rationale>.", "",
             f"Summary changed since review: {status['summary_changed']}",
             f"Xcode version changed since review: {status['version_changed']}", ""]
    for label in ("added", "changed", "removed"):
        lines.extend([f"## {label} ({len(status[label])})", ""])
        for name in status[label]:
            lines.append(f"- `{name}`")
            path = root / name
            old = path.read_text() if path.is_file() else ""
            new = files.get(name, b"").decode()
            if old != new:
                diff = "\n".join(difflib.unified_diff(old.splitlines(), new.splitlines(),
                                                    fromfile="installed/" + name, tofile="exported/" + name))
                lines.extend(["", "````diff", diff, "````", ""])
            else:
                lines.append("  Source is already on disk; compare with the last reviewed Git revision if needed.")
        lines.append("")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n")
    return status


def mark_prompt_review(root, files, note):
    summary = prompt_summary(root)
    names = sorted(set(re.findall(r"\.\./xcode-ai/prompts/([^\s)]+\.idechatprompttemplate)", summary)))
    if not names:
        raise RuntimeError("Prompt summary must link to its source templates")
    for name in names:
        if "xcode-ai/prompts/" + name not in files:
            raise RuntimeError(f"Summary links to a missing source template: {name}")
    status = prompt_review_status(root, files)
    record = {"format": 1, "xcode": status["xcode"], "template_hashes": status["template_hashes"],
              "summary_sha256": digest(summary.encode()), "summary_sources": names, "review_note": note}
    (root / PROMPT_REVIEW).write_bytes(json_bytes(record))


def run(command, env):
    result = subprocess.run(command, env=env, capture_output=True, text=True, timeout=60)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or str(command))
    return result.stdout.strip()


def resolve_xcode(explicit):
    if explicit:
        app = Path(explicit).expanduser().resolve()
    elif os.environ.get("DEVELOPER_DIR"):
        selected = Path(os.environ["DEVELOPER_DIR"]).resolve()
        app = selected.parent.parent if selected.name == "Developer" else selected
    else:
        selected = Path(run(["/usr/bin/xcode-select", "-p"], os.environ))
        app = selected.parent.parent if selected.name == "Developer" else Path("/Applications/Xcode.app")
    if not (app / "Contents/Developer/usr/bin/mcpbridge").is_file():
        raise RuntimeError(f"Compatible Xcode not found at {app}; pass --xcode /path/to/Xcode.app")
    return app


def collect_files(directory, prefix):
    output = {}
    for path in sorted(directory.rglob("*")):
        if path.is_symlink():
            raise RuntimeError(f"Unexpected symlink in export: {path}")
        if path.is_file():
            output[f"{prefix}/{path.relative_to(directory).as_posix()}"] = path.read_bytes()
    return output


def probe_mcp(env, timeout=20):
    """Only initialize and list tools; no project-changing tool calls."""
    process = subprocess.Popen(["/usr/bin/xcrun", "mcpbridge"], env=env,
                               stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    selector = selectors.DefaultSelector()
    selector.register(process.stdout, selectors.EVENT_READ)
    pending = b""
    request_id = 0

    def send(message):
        process.stdin.write(json_bytes(message).replace(b"\n", b" ") + b"\n")
        process.stdin.flush()

    def request(method, params):
        nonlocal request_id, pending
        request_id += 1
        send({"jsonrpc": "2.0", "id": request_id, "method": method, "params": params})
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            while b"\n" in pending:
                line, pending = pending.split(b"\n", 1)
                if not line.strip():
                    continue
                response = json.loads(line)
                if response.get("id") == request_id:
                    if "error" in response:
                        raise RuntimeError(f"MCP {method}: {response['error']}")
                    return response["result"]
            if selector.select(max(0, deadline - time.monotonic())):
                chunk = os.read(process.stdout.fileno(), 65536)
                if not chunk:
                    raise RuntimeError("MCP bridge exited; open Xcode and enable external agent access")
                pending += chunk
        raise RuntimeError(f"MCP {method} timed out; check Xcode authorization and open project")

    try:
        initialized = request("initialize", {"protocolVersion": "2024-11-05", "capabilities": {},
                                             "clientInfo": {"name": "apple-plugin-sync", "version": "1.0.0"}})
        send({"jsonrpc": "2.0", "method": "notifications/initialized"})
        tools, cursor, seen = [], None, set()
        while True:
            result = request("tools/list", {"cursor": cursor} if cursor else {})
            tools.extend(result.get("tools", []))
            cursor = result.get("nextCursor")
            if not cursor:
                break
            if cursor in seen:
                raise RuntimeError("MCP tools/list repeated a pagination cursor")
            seen.add(cursor)
        return {"protocolVersion": initialized["protocolVersion"],
                "serverInfo": initialized.get("serverInfo", {}),
                "capabilities": initialized.get("capabilities", {}),
                "instructions": initialized.get("instructions"),
                "tools": sorted(tools, key=lambda item: item["name"])}
    finally:
        selector.close()
        process.terminate()
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


def capture(app, export_dir=None, probe=False):
    env = dict(os.environ, DEVELOPER_DIR=str(app / "Contents/Developer"))
    version = plistlib.loads((app / "Contents/version.plist").read_bytes())
    # Xcode creates its own build-specific export cache. No global configuration changes.
    exported = Path(export_dir).expanduser().resolve() if export_dir else Path(run(
        ["/usr/bin/xcrun", "agent", "plugin", "path", "--plugin-format", "codex"], env))
    skill_root = exported if export_dir else exported / "skills"
    skills = sorted(skill_root.glob("*/SKILL.md"))
    if not skills:
        raise RuntimeError(f"No exported skills found at {skill_root}; refusing an empty sync")
    files = collect_files(skill_root, "skills")
    resources = app / RESOURCES
    prompts = sorted(resources.glob("*.idechatprompttemplate"))
    if not prompts:
        raise RuntimeError(f"No prompt templates at {resources}; Xcode layout may have changed")
    for path in prompts + sorted(resources.glob("*.packaged")):
        files[f"xcode-ai/prompts/{path.name}"] = path.read_bytes()
    documentation = resources / "AdditionalDocumentation"
    if documentation.is_dir():
        files.update(collect_files(documentation, "xcode-ai/prompts/AdditionalDocumentation"))
    if not export_dir:
        for name in (".codex-plugin/plugin.json", ".mcp.json", "mcp.json"):
            path = exported / name
            if path.is_file():
                files[f"xcode-ai/upstream-plugin/{name}"] = path.read_bytes()
    files["xcode-ai/mcp/bridge-help.txt"] = (run(["/usr/bin/xcrun", "mcpbridge", "--help"], env) + "\n").encode()
    bridge = app / "Contents/Developer/usr/bin/mcpbridge"
    source = {"xcode_version": version["CFBundleShortVersionString"],
              "xcode_build": version["ProductBuildVersion"],
              "skills_export": "provided-skills-directory" if export_dir else "xcrun agent plugin path --plugin-format codex",
              "prompt_resources": RESOURCES,
              "skill_names": [p.parent.name for p in skills],
              "prompt_templates": len(prompts), "mcp_bridge_sha256": digest(bridge.read_bytes()),
              "mcp_runtime_verified": probe}
    if probe:
        inventory = probe_mcp(env)
        files["xcode-ai/mcp/tools.json"] = json_bytes(inventory)
        source["mcp_tool_count"] = len(inventory["tools"])
    files["xcode-ai/source.json"] = json_bytes(source)
    return files, source


def destination(root, name):
    # Treat lock-file paths as data. Never follow a local link outside the repository.
    path = root / name
    if Path(name).is_absolute() or ".." in Path(name).parts or not name.startswith(("skills/", "xcode-ai/")):
        raise RuntimeError(f"Invalid managed path: {name}")
    if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
        raise RuntimeError(f"Unsafe managed path: {name}")
    return path


def plan(root, files, adopt=False):
    lock_path = root / LOCK
    previous = json.loads(lock_path.read_text())["files"] if lock_path.exists() else {}
    changes, conflicts = {"added": [], "changed": [], "removed": []}, []
    existing_skills = set(collect_files(root / "skills", "skills")) if (root / "skills").exists() else set()
    for name in sorted(set(files) | set(previous) | existing_skills):
        path = destination(root, name)
        current = path.read_bytes() if path.is_file() else None
        incoming = files.get(name)
        current_hash = digest(current) if current is not None else None
        if current == incoming:
            continue
        if name.startswith("skills/"):
            pass  # The user explicitly requires an authoritative upstream skills mirror.
        elif name in previous and current_hash != previous[name]:
            conflicts.append(name)
        elif name not in previous and current is not None and not adopt:
            conflicts.append(name)
        key = "removed" if incoming is None else "added" if current is None else "changed"
        changes[key].append(name)
    return changes, conflicts


def apply_files(root, files, source, changes, conflicts):
    if conflicts:
        raise RuntimeError("Local changes or unowned files conflict; see report. No files were applied.")
    touched = changes["added"] + changes["changed"] + changes["removed"]
    paths = [destination(root, name) for name in touched] + [root / LOCK]
    originals = {path: path.read_bytes() if path.is_file() else None for path in paths}
    backup_root = root / ".xcode-ai/backups"
    backup_root.mkdir(parents=True, exist_ok=True)
    backup = Path(tempfile.mkdtemp(prefix="before-apply-", dir=backup_root))
    for path, content in originals.items():
        if content is not None:
            saved = backup / path.relative_to(root)
            saved.parent.mkdir(parents=True, exist_ok=True)
            saved.write_bytes(content)
    try:
        for name in changes["removed"]:
            destination(root, name).unlink()
        # Remove empty retired skill directories so they are not discovered as skills.
        for path in sorted((root / "skills").rglob("*"), key=lambda p: len(p.parts), reverse=True):
            if path.is_dir() and not any(path.iterdir()):
                path.rmdir()
        for name in changes["added"] + changes["changed"]:
            path = destination(root, name)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(files[name])
        (root / LOCK).write_bytes(json_bytes({"format": 1, "source": source,
                                             "files": {name: digest(data) for name, data in sorted(files.items())}}))
    except OSError:
        for path, content in originals.items():
            if content is None:
                if path.is_file():
                    path.unlink()
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(content)
        raise
    print(f"Backup: {backup}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--xcode", help="Xcode.app path; otherwise use DEVELOPER_DIR or xcode-select, then /Applications/Xcode.app")
    parser.add_argument("--skills-dir", help="Use a previously exported skills directory instead of plugin path")
    parser.add_argument("--apply", action="store_true", help="Apply the export after conflict checks")
    parser.add_argument("--adopt-existing", action="store_true", help="Explicitly replace conflicting, previously untracked upstream files on first adoption")
    parser.add_argument("--probe-mcp", action="store_true", help="Connect to Xcode and snapshot the live tools/list schema")
    args = parser.parse_args()
    staging_root = ROOT / ".xcode-ai"
    staging_root.mkdir(exist_ok=True)
    run_lock = (staging_root / "run.lock").open("w")
    try:
        fcntl.flock(run_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        raise RuntimeError("Another Xcode AI sync is running; retry after it finishes")
    # A failed export leaves the last successful preview intact.
    with tempfile.TemporaryDirectory(prefix="capture-", dir=staging_root) as temp:
        files, source = capture(resolve_xcode(args.xcode), args.skills_dir, args.probe_mcp)
        changes, conflicts = plan(ROOT, files, args.adopt_existing)
        stage = Path(temp) / "snapshot"
        for name, content in files.items():
            path = stage / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
        report = [f"# Xcode {source['xcode_version']} ({source['xcode_build']}) AI sync", "",
                  f"Skills: {len(source['skill_names'])}; prompt templates: {source['prompt_templates']}.",
                  f"MCP live connection verified: {source['mcp_runtime_verified']}.", "",
                  "Apple exports are preserved byte-for-byte. skills/ is an authoritative upstream mirror.", ""]
        if args.probe_mcp:
            report.extend(["## MCP capability changes", ""])
            prior_tools = ROOT / "xcode-ai/mcp/tools.json"
            old_tools = json.loads(prior_tools.read_text())["tools"] if prior_tools.exists() else []
            old_by_name = {tool["name"]: tool for tool in old_tools}
            new_by_name = {tool["name"]: tool for tool in inventory_from_files(files)}
            for label, names in (
                ("Added", sorted(new_by_name.keys() - old_by_name.keys())),
                ("Removed", sorted(old_by_name.keys() - new_by_name.keys())),
                ("Changed", sorted(name for name in old_by_name.keys() & new_by_name.keys()
                                   if old_by_name[name] != new_by_name[name])),
            ):
                report.extend([f"{label}: {', '.join(names) or 'none'}", ""])
            if "DeviceEventSynthesize" not in new_by_name and any(
                b"DeviceEventSynthesize" in data for name, data in files.items() if name.startswith("skills/")
            ):
                report.extend(["Compatibility: Apple skills reference `DeviceEventSynthesize`, but this tool name is absent from the live MCP inventory. Check the schema of `DeviceInteractionSynthesize` before adapting calls. Apple source remains unchanged.", ""])
        for label, names in [*changes.items(), ("conflicts", conflicts)]:
            report.extend([f"## {label} ({len(names)})", "", *[f"- `{n}`" for n in names], ""])
        review = write_prompt_review(ROOT, files, staging_root / "prompt-review.md")
        report.extend(["## Prompt-derived rules", "", f"Review status: **{review['status']}**.", "",
                       "See prompt-review.md for source changes and adaptation instructions. Raw exports are not active instructions."])
        snapshot = staging_root / "snapshot"
        if snapshot.exists():
            shutil.rmtree(snapshot)
        shutil.move(str(stage), snapshot)
        (staging_root / "report.md").write_text("\n".join(report) + "\n")
        if args.apply:
            apply_files(ROOT, files, source, changes, conflicts)
        print(f"Xcode {source['xcode_version']} ({source['xcode_build']}): {len(source['skill_names'])} skills, {source['prompt_templates']} prompts")
        print("; ".join(f"{key}: {len(value)}" for key, value in changes.items()) + f"; conflicts: {len(conflicts)}")
        print(f"Report: {staging_root / 'report.md'}")
        print(f"Prompt rules review: {review['status']} ({staging_root / 'prompt-review.md'})")
        print("Applied." if args.apply else "Preview only. Review report, then rerun with --apply.")


def inventory_from_files(files):
    return json.loads(files["xcode-ai/mcp/tools.json"])["tools"]


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, OSError, ValueError, KeyError, subprocess.TimeoutExpired) as error:
        print(f"Sync failed: {error}", file=sys.stderr)
        sys.exit(1)

"""Exercise Codex's actual package loader; optional live MCP test calls no model."""
import json
import os
from pathlib import Path
import selectors
import shutil
import subprocess
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]


class AppServer:
    def __init__(self, env):
        self.errors = tempfile.TemporaryFile()
        self.process = subprocess.Popen(
            ["codex", "app-server", "--stdio"], env=env, cwd="/private/tmp",
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self.errors,
        )
        self.selector = selectors.DefaultSelector()
        self.selector.register(self.process.stdout, selectors.EVENT_READ)
        self.pending = b""
        self.request_id = 0

    def send(self, message):
        self.process.stdin.write((json.dumps(message) + "\n").encode())
        self.process.stdin.flush()

    def call(self, method, params, timeout=30):
        self.request_id += 1
        self.send({"jsonrpc": "2.0", "id": self.request_id, "method": method, "params": params})
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            while b"\n" in self.pending:
                line, self.pending = self.pending.split(b"\n", 1)
                response = json.loads(line)
                if response.get("id") == self.request_id and "method" not in response:
                    if "error" in response:
                        self.errors.seek(0)
                        lines = self.errors.read().decode(errors="replace").splitlines()
                        diagnostics = [line for line in lines if "MCP server stderr" in line or "xcode_mcp.sh" in line]
                        raise RuntimeError(f"{method}: {response['error']}\n" + "\n".join(diagnostics[-5:]))
                    return response["result"]
            if self.selector.select(max(0, deadline - time.monotonic())):
                data = os.read(self.process.stdout.fileno(), 65536)
                if not data:
                    raise RuntimeError("Codex app server exited")
                self.pending += data
        raise RuntimeError(f"Codex app server timed out: {method}")

    def close(self):
        self.process.terminate()
        try:
            self.process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait()
        self.selector.close()
        self.process.stdin.close()
        self.process.stdout.close()
        self.errors.close()


@unittest.skipUnless(shutil.which("codex"), "Codex CLI is required for package integration tests")
class PluginPackagingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="apple-plugin-package-")
        self.addCleanup(self.temp.cleanup)
        self.env = dict(os.environ, CODEX_HOME=self.temp.name)
        for args in (
            ["plugin", "marketplace", "add", str(ROOT), "--json"],
            ["plugin", "add", "apple@apple-developer", "--json"],
        ):
            self.installed = self.cli(*args)

    def cli(self, *args):
        result = subprocess.run(["codex", *args], env=self.env, cwd="/private/tmp",
                                text=True, capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def server(self):
        server = AppServer(self.env)
        self.addCleanup(server.close)
        server.call("initialize", {"clientInfo": {"name": "apple-plugin-test", "version": "1"},
                                   "capabilities": {"experimentalApi": True}})
        server.send({"jsonrpc": "2.0", "method": "initialized"})
        return server

    def test_installed_plugin_registers_xcode_mcp(self):
        servers = self.cli("mcp", "list", "--json")
        xcode = next(server for server in servers if server["name"] == "xcode-tools")
        self.assertTrue(xcode["enabled"])
        transport = xcode["transport"]
        self.assertNotIn("${PLUGIN_ROOT}", " ".join(transport["args"]))
        self.assertTrue((Path(transport["cwd"]) / transport["args"][0]).is_file())
        detail = self.server().call("plugin/read", {
            "pluginName": "apple", "marketplacePath": str(ROOT / ".agents/plugins/marketplace.json"),
        })["plugin"]
        self.assertEqual(detail["mcpServers"], ["xcode-tools"])
        manifest = json.loads((ROOT / ".codex-plugin/plugin.json").read_text())
        expected = sum(len(list((ROOT / folder).glob("*/SKILL.md"))) for folder in manifest["skills"])
        self.assertEqual(len(detail["skills"]), expected)
        installed = Path(self.installed["installedPath"])
        entry = installed / "plugin-skills/apple-development/SKILL.md"
        self.assertTrue(entry.is_file())
        self.assertTrue((entry.parent / "../../rules/apple.md").resolve().is_file())

    @unittest.skipUnless(os.environ.get("APPLE_PLUGIN_TEST_LIVE_MCP") == "1", "Enable explicitly with a running Xcode")
    def test_codex_discovers_live_tools_and_checks_authorization(self):
        server = self.server()
        thread = server.call("thread/start", {"cwd": str(ROOT), "ephemeral": True,
                                               "approvalPolicy": "never", "sandbox": "read-only"})
        status = server.call("mcpServerStatus/list", {
            "threadId": thread["thread"]["id"], "serverName": "xcode-tools",
        })
        xcode = next(item for item in status["data"] if item["name"] == "xcode-tools")
        self.assertIsNone(xcode.get("toolsError"), xcode.get("toolsError"))
        self.assertIn("XcodeListWorkspaces", xcode["tools"])
        print(f"\nCodex discovered {len(xcode['tools'])} live Xcode tools.", flush=True)
        response = server.call("mcpServer/tool/call", {
            "threadId": thread["thread"]["id"], "server": "xcode-tools",
            "tool": "XcodeListWorkspaces", "arguments": {},
        })
        if response.get("isError"):
            text = "\n".join(item.get("text", "") for item in response.get("content", []))
            if "isn't approved to use Xcode's tools yet" in text:
                self.skipTest("MCP initialized and tools discovered; Xcode requires project authorization before workspace access")
            self.fail(response)
        self.assertTrue(response.get("content") or response.get("structuredContent"), response)


if __name__ == "__main__":
    unittest.main()

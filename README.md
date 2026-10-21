# Apple Platform Development Best Practices & AI Rules

A comprehensive knowledge base and assistant configuration for Apple platform development (covering iOS, macOS, watchOS, tvOS, and visionOS). 

This repository compiles Xcode 27 developer skills, modern Swift/SwiftUI practices, UIKit modernization steps, Swift Testing migration guides, and Xcode security configurations.

The knowledge resources can be reused across coding assistants; live Xcode tools require the local MCP integration:
- **For Developers**: Serves as an authoritative, offline-friendly handbook and cheat sheet for modern Apple development paradigms.
- **For AI Coding Assistants (Cursor, Copilot, Windsurf, Antigravity, etc.)**: The consolidated rules and skills can be copied directly into system prompts, project rules (e.g., `.cursorrules`, `.windsurfrules`), or integrated as AI agent plugins.

---

## Directory Structure

```
apple/
├── README.md           # This documentation
├── .codex-plugin/
│   └── plugin.json     # Codex compatibility manifest
├── .mcp.json           # Local Xcode MCP connection
├── .agents/plugins/
│   └── marketplace.json # Codex marketplace catalog
├── scripts/            # Xcode export/sync and MCP launcher
├── docs/               # Update workflow and reusable review prompt
├── xcode-ai/           # Original prompt templates and source metadata
├── xcode-ai.lock.json  # Managed export hashes and Xcode version
├── rules/
│   └── apple.md        # Unified ruleset (ideal for .cursorrules or system prompts)
└── skills/             # Exact mirror of Xcode's exported skills
```

---

## Features & Components

### 1. Unified Rules (`rules/apple.md`)
A consolidated, structured reference sheet containing strict coding boundaries and guidelines. This file is ideal to be used as a custom rule file (e.g., `.cursorrules` or `.github/copilot-instructions.md`) to guide AI-generated code.
- **SwiftUI Best Practices**: Optimizing view hierarchies, avoiding `@Entry` closure invalidation warnings, and standardizing data flow using the `@Observable` macro.
- **SwiftUI 2027 Compile Defense**: Crucial fixes for `@State` Macro compilation issues introduced in Xcode 27/iOS 27.
- **UIKit Modernization**: Guide to removing deprecated global interfaces like `UIScreen.main` or `interfaceOrientation` to support multi-window environments.
- **Swift Testing Modernization**: Best practices for migrating unit tests from `XCTest` to the modern `Testing` framework.
- **Xcode Security Settings**: Build setting configurations for Enhanced Security (`ENABLE_ENHANCED_SECURITY=YES`), compiler warning flags, and `arm64e` pointer authentication overrides.

### 2. Specialized Reference Skills (`skills/`)
Contains 15 skills exported from Xcode 27.1 (27A9275). See `xcode-ai/source.json` for the current generated inventory:
- **`accessibility-dynamic-type-specialist`**, **`accessibility-sufficient-contrast-specialist`**, **`accessibility-voiceover-specialist`**: Accessibility guidance.
- **`adopt-c-bounds-safety`**: Adopting C language pointer bounds annotations (`-fbounds-safety`).
- **`audit-xcode-security-settings`**: Progressively securing Xcode target build configurations.
- **`device-interaction`**: Automating simulator or hardware UI tests through precision touch-event synthesis.
- **`modernize-tests`**: Gradual test suite migration guide.
- **`swiftui-specialist`**: High-frequency environment variables and dynamic lists rendering optimization.
- **`swiftui-whats-new-27`**: Feature guide on Xcode 27 drag-to-reorder, `AsyncImage` caching, and toolbar adaptations.
- **`app-resizability`**: Scene lifecycle, orientation, safe areas, and adaptive app layouts.
- **`app-intents-specialist`**, **`app-intents-whats-new-27`**: App Intents integration and SDK updates.
- **`building-document-based-swiftui-applications`**: Document-based SwiftUI applications.
- **`translation`**, **`translation-coordinator`**: Translation workflows.

---

## How to Use

### Integrating with AI Assistants

#### 1. In Codex

Use a Codex CLI version that supports `codex plugin marketplace add` and `codex plugin add`. Install the plugin from this repository:

```bash
codex plugin marketplace add jihongboo/apple-developer-plugin &&
codex plugin add apple@apple-developer
```

The marketplace is named `apple-developer`; the plugin is named `apple`. This package includes skills and a local Xcode MCP bridge. It requires macOS and a compatible Xcode installation. Open a project in Xcode and enable external agent access in Intelligence settings before using MCP tools. The bridge connects to the installed Xcode; it does not bundle Xcode or its tools. No external service login is required.

Start a new chat after installation. In the desktop app, restart the app if the marketplace or skills do not appear. Try: "Use the modernize-tests skill to review which XCTest unit tests can migrate to Swift Testing."

Version 0.1.1 uses the Codex compatibility layout (`.codex-plugin/plugin.json` and `.mcp.json`). Codex CLI 0.163.0-alpha.10.2 discovers the skills in a portable package but does not register its root `mcp.json`; adding a compatibility overlay while retaining root `plugin.json` does not resolve that issue.

To update an existing Git-backed installation after the new release has been pushed:

```bash
codex plugin marketplace upgrade apple-developer &&
codex plugin add apple@apple-developer
```

Start a new chat after updating. Check that the plugin detail lists `xcode-tools` as well as the skills; a successful install alone does not verify MCP registration.

Xcode may require approval for each new external agent. If a tool reports that the agent is not approved yet, open your project using `XcodeOpenWorkspace` (or create one with `XcodeNewProject`) and complete the Xcode approval prompt. A successful MCP handshake and tool listing do not grant project access.

To verify the installation:

```bash
codex plugin list --marketplace apple-developer
```

For local development, run these commands from the cloned repository root instead of adding the GitHub source:

```bash
codex plugin marketplace add . &&
codex plugin add apple@apple-developer
```

Codex installs a cached copy of the plugin. After local edits, refresh that installed copy before testing. The standalone `rules/apple.md` file is a reference for manual integration; plugin installation does not automatically apply it as global instructions.

See the [official Codex plugin packaging and marketplace documentation](https://developers.openai.com/plugins/build/plugins) for distribution details.

#### 2. In Antigravity
Clone or copy this repository into your global Antigravity plugins directory:
```bash
mkdir -p ~/.gemini/config/plugins
git clone https://github.com/jihongboo/apple-developer-plugin.git ~/.gemini/config/plugins/apple
```

#### 3. In Cursor or Windsurf
Copy the contents of `rules/apple.md` into a `.cursorrules` or `.windsurfrules` file at the root of your project workspace. This instructs the AI assistant to adhere to modern SwiftUI APIs, avoid deprecated UIKit elements, and apply correct Swift Testing assertions.

#### 4. In GitHub Copilot / Custom System Prompts
Append the rules in `rules/apple.md` to your prompt guidelines or your repository-level Copilot instructions file (e.g., `.github/copilot-instructions.md`).

---

## Updating Xcode AI Content

Apple-exported skills are preserved unchanged, including their descriptions. After updating Xcode, preview changes with:

```bash
python3 scripts/sync_xcode_ai.py --xcode /Applications/Xcode.app
```

See [the update workflow](docs/update-xcode-ai.md) for applying skills and raw prompt templates, tracking versions and local conflicts, verifying MCP tools, and a reusable Codex prompt that runs the workflow.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

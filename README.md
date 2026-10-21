# Apple Platform Development Best Practices & AI Rules

A comprehensive knowledge base and assistant configuration for Apple platform development (covering iOS, macOS, watchOS, tvOS, and visionOS). 

This repository compiles Xcode 27 developer skills, modern Swift/SwiftUI practices, UIKit modernization steps, Swift Testing migration guides, and Xcode security configurations.

It is designed to be **fully tool-agnostic**:
- **For Developers**: Serves as an authoritative, offline-friendly handbook and cheat sheet for modern Apple development paradigms.
- **For AI Coding Assistants (Cursor, Copilot, Windsurf, Antigravity, etc.)**: The consolidated rules and skills can be copied directly into system prompts, project rules (e.g., `.cursorrules`, `.windsurfrules`), or integrated as AI agent plugins.

---

## Directory Structure

```
apple/
├── README.md           # This documentation
├── plugin.json         # Portable Agent Plugins manifest with Codex metadata
├── .agents/plugins/
│   └── marketplace.json # Codex marketplace catalog
├── rules/
│   └── apple.md        # Unified ruleset (ideal for .cursorrules or system prompts)
└── skills/             # Target-specific development skills & references
    ├── adopt-c-bounds-safety
    ├── audit-xcode-security-settings
    ├── device-interaction
    ├── modernize-tests
    ├── swiftui-specialist
    ├── swiftui-whats-new-27
    └── uikit-app-modernization
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
Contains 7 targeted skills with accompanying documentation references to assist with complex migration tasks:
- **`adopt-c-bounds-safety`**: Adopting C language pointer bounds annotations (`-fbounds-safety`).
- **`audit-xcode-security-settings`**: Progressively securing Xcode target build configurations.
- **`device-interaction`**: Automating simulator or hardware UI tests through precision touch-event synthesis.
- **`modernize-tests`**: Gradual test suite migration guide.
- **`swiftui-specialist`**: High-frequency environment variables and dynamic lists rendering optimization.
- **`swiftui-whats-new-27`**: Feature guide on Xcode 27 drag-to-reorder, `AsyncImage` caching, and toolbar adaptations.
- **`uikit-app-modernization`**: Migrating AppDelegate lifecycle to modern SceneDelegate lifecycle.

---

## How to Use

### Integrating with AI Assistants

#### 1. In Codex

Use a Codex CLI version that supports `codex plugin marketplace add` and `codex plugin add`. Install the plugin from this repository:

```bash
codex plugin marketplace add jihongboo/apple-developer-plugin &&
codex plugin add apple@apple-developer
```

The marketplace is named `apple-developer`; the plugin is named `apple`. This skills-only package does not require an external service login. Building or testing Apple apps requires macOS and a compatible Xcode installation. Device interaction and some security audit steps additionally require the Xcode tools named in those skills; installing this plugin does not provide those tools.

Start a new chat after installation. In the desktop app, restart the app if the marketplace or skills do not appear. Try: "Use the modernize-tests skill to review which XCTest unit tests can migrate to Swift Testing."

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

## License

This project is licensed under the MIT License - see the LICENSE file for details.

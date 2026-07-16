# Apple Platform Development Assistant Plugin

An AI-first assistant plugin for Google Antigravity, specifically designed to help developers with Apple platform development (iOS, macOS, watchOS, tvOS, visionOS). It bundles built-in skills extracted from Xcode 27 and a unified ruleset covering modern SwiftUI patterns, UIKit modernization, Swift Testing, and Xcode security configurations.

---

## Directory Structure

```
apple/
├── README.md           # This documentation
├── plugin.json         # Plugin metadata (offline-friendly)
├── rules/
│   └── apple.md        # Unified best practices and compile-time guardrails
└── skills/             # Xcode 27 built-in skills
    ├── adopt-c-bounds-safety
    ├── audit-xcode-security-settings
    ├── device-interaction
    ├── modernize-tests
    ├── swiftui-specialist
    ├── swiftui-whats-new-27
    └── uikit-app-modernization
```

---

## Features & Bundled Components

### 1. Unified Rules (`rules/apple.md`)
A consolidated, offline-friendly guardrail file loaded automatically by Antigravity to keep code generation aligned with the latest Apple APIs. Key coverages:
- **SwiftUI Best Practices**: Optimizing view hierarchies, avoiding `@Entry` closure invalidation warnings, and standardizing data flow using the `@Observable` macro.
- **SwiftUI 2027 Compile Defense**: Crucial fixes for `@State` Macro compilation issues introduced in Xcode 27/iOS 27.
- **UIKit Modernization**: Guide to removing deprecated global interfaces like `UIScreen.main` or `interfaceOrientation` to support multi-window environments.
- **Swift Testing Modernization**: Best practices for migrating unit tests from `XCTest` to the modern `Testing` framework.
- **Xcode Security Settings**: Build setting configurations for Enhanced Security (`ENABLE_ENHANCED_SECURITY=YES`), compiler warning flags, and `arm64e` pointer authentication overrides.

### 2. Specialized Skills (`skills/`)
Contains 7 targeted skills with accompanying documentation references to assist with complex tasks:
- **`adopt-c-bounds-safety`**: Adopting C language pointer bounds annotations (`-fbounds-safety`).
- **`audit-xcode-security-settings`**: Progressively securing Xcode target build configurations.
- **`device-interaction`**: Automating simulator or hardware UI tests through precision touch-event synthesis.
- **`modernize-tests`**: Gradual test suite migration guide.
- **`swiftui-specialist`**: High-frequency environment variables and dynamic lists rendering optimization.
- **`swiftui-whats-new-27`**: Feature guide on Xcode 27 drag-to-reorder, `AsyncImage` caching, and toolbar adaptations.
- **`uikit-app-modernization`**: Migrating AppDelegate lifecycle to modern SceneDelegate lifecycle.

---

## Installation & Setup

1. Clone or copy this repository into your global Antigravity plugins directory:
   ```bash
   # Create parent folder if not exists
   mkdir -p ~/.gemini/config/plugins
   
   # Clone the plugin
   git clone https://github.com/jihongboo/apple-developer-plugin.git ~/.gemini/config/plugins/apple
   ```

2. Restart your Antigravity agent. The plugin, its skills, and its unified ruleset will be automatically discovered and loaded for your workspace tasks.

---

## License

This project is licensed under the MIT License - see the LICENSE file for details.

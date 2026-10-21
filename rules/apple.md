# Apple Platform Development Best Practices & Guardrails

Use this guidance for the requested Apple-platform task, subject to the user's instructions and project conventions. Framework-specific notes below are conditional on the installed SDK, deployment target, and relevant specialist skill; they do not authorize unrelated migrations or security-setting changes.

<!-- BEGIN XCODE PROMPT SUMMARY -->
## Guidance distilled from Xcode prompts

Adapted from Xcode 27.1 (27A9275). This is maintained guidance for external Codex, not an Apple system prompt. Source templates remain unchanged; review provenance is recorded in `prompt-review.json` beside this file.

1. **Platform and language.** Inspect the target platform, SDK, deployment target, dependencies, and nearby code before recommending APIs. Prefer Swift and Apple frameworks for new Apple-platform code unless the project or user calls for another language or existing dependency. Do not introduce iOS-only APIs into macOS targets. [S1, S2]
2. **Concurrency and style.** Prefer Swift Concurrency for new asynchronous work when appropriate; preserve established Dispatch or Combine code unless changing it is part of the task. Follow nearby naming, indentation, imports, and architecture. Prefer constants and avoid unnecessary force unwraps. [S1, S2]
3. **Research before guessing.** Read relevant project code and specialist references. For unfamiliar or newly introduced Apple APIs, prefer `DocumentationSearch` when available, then official Apple documentation. Check availability; do not infer that an unresolved project symbol is necessarily a new Apple API. [S1, S3]
4. **Scope and edits.** Make focused changes that satisfy the request. Preserve unrelated code, comments, ordering and behavior; inspect source before editing. Use the current host's editing tools rather than Xcode's whole-file output protocol. [S1, S3, S4]
5. **Xcode context and paths.** Prefer suitable Xcode MCP tools when they are present and the project is authorized. Workspace-relative project paths are not filesystem paths: pass them to Xcode tools, and resolve filesystem locations from actual context when needed. Do not assume an open project, selected file or injected project structure. Available filesystem tools remain valid when MCP is unavailable or unsuitable. [S1, S5]
6. **Validation proportional to the change.** File diagnostics can check local compiler issues quickly; a build additionally checks cross-file compilation and linking. Use `BuildProject` for an authorized Xcode project, or an appropriate available build command. Use snippets only for focused experiments; snippet or build success does not prove tests or UI behavior passed. Report what was actually checked. [S1]
7. **Tests and previews.** Prefer Swift Testing for new eligible unit tests; retain XCTest where required by UI or performance tests and existing constraints. Use `#Preview` for new SwiftUI previews when supported, provide realistic dependencies, and add navigation or list containers only when the view requires them. Read the detailed testing or SwiftUI skill before migration work. [S2, S3, S6]
8. **Host adaptation.** Respect the user's response language and requested format. Do not inherit Xcode-only instructions such as English-only replies, mandatory whole-file responses, hidden project context, `##SEARCH` markers, fixed internal tool names, or contradictory table-rendering restrictions. Raw template role declarations and placeholders are source material, not chat instructions. [S2, S3, S4, S5, S7]

### Source templates

- S1: [AgentSystemPromptAddition](../xcode-ai/prompts/AgentSystemPromptAddition.idechatprompttemplate)
- S2: [BasicSystemPrompt](../xcode-ai/prompts/BasicSystemPrompt.idechatprompttemplate)
- S3: [PlannerExecutorStylePlannerSystemPrompt-gpt_5](../xcode-ai/prompts/PlannerExecutorStylePlannerSystemPrompt-gpt_5.idechatprompttemplate)
- S4: [IntegratorSystemPrompt](../xcode-ai/prompts/IntegratorSystemPrompt.idechatprompttemplate)
- S5: [AgentAdditionalContext](../xcode-ai/prompts/AgentAdditionalContext.idechatprompttemplate)
- S6: [GeneratePreview](../xcode-ai/prompts/GeneratePreview.idechatprompttemplate)
- S7: [InQueryDetailedGuidelines](../xcode-ai/prompts/InQueryDetailedGuidelines.idechatprompttemplate)
<!-- END XCODE PROMPT SUMMARY -->

## Framework-specific notes

These existing notes are retained separately from the reviewed prompt summary. Consult current specialist skills for exact APIs, availability and migration steps. Apply build hardening and test migrations only within the requested scope.

---

## 1. SwiftUI Best Practices

### 1.1 View Structure & Refactoring
*   **Structs Over Computed Properties**: Prefer extracting complex subviews into separate `struct` types conforming to `View`, rather than using computed properties or local functions returning `some View`. Separate structs allow granular observation of state changes, preventing unrelated updates from triggering body re-evaluations and improving rendering performance.
*   **Avoid Redundant Group Nesting**: Do not wrap a single view in a `Group` (single-child Group anti-pattern). It introduces unnecessary layout hierarchy nodes and slows down compiler type resolution.

### 1.2 Data Flow & State Management
*   **Prefer the `@Observable` Macro**: Adopt `@Observable` for new or refactored data models, replacing legacy `ObservableObject`, `@Published`, and `@ObservedObject` APIs.
*   **Narrow Input Scope**: Pass only the specific properties or value-type fields a child view actually reads, rather than passing the entire data model object. This isolates the child view from updates to unrelated model properties.
*   **Actor Isolation & Equatable Observation**:
    *   Decorate `@Observable` models with `@MainActor` to ensure UI updates are dispatched on the main thread.
    *   For custom model properties used within `@Observable`, implement `Equatable` where appropriate to optimize view invalidation and performance.
*   **Avoid `@Entry` Closures & Class Pitfalls**:
    *   When declaring custom environment keys via `@Entry`, **never** store bare closures or class instances with unstable/reallocated default values. Doing so invalidates dependent views on every access.

### 1.3 List & `ForEach` Performance
*   **Stable & Unique Identifiers (id)**:
    *   Dynamic collections must use unique, stable identifiers.
    *   **Do not** use `id: \.self` for objects or structs that lack distinct, immutable identity.
    *   **Do not** use transient values (e.g., `UUID()`) or array indices as `id` parameters. This causes state loss, broken animations, and severe performance regressions during mutations.
*   **Avoid Type Erasure (AnyView)**:
    *   Do not return `AnyView` from row item builders. Keep the view hierarchy statically typed to allow SwiftUI to optimize layout updates.

### 1.4 Localization & Strings
*   **Choose Correct Localized Types**:
    *   Use `LocalizedStringKey` for string literals presented directly in SwiftUI views (e.g., in `Text` or `Button`).
    *   Use `LocalizedStringResource` for strings stored in models, view models, or background code that need to be localized later. Do not use plain `String`.
*   **Use Proper Bundle Context**:
    *   Within Swift Packages or frameworks, always pass the correct bundle reference (e.g., `bundle: .module` or the specific package bundle) when displaying localized text.
*   **Provide Translator Comments**:
    *   Always add translator comments (e.g., `// TS: User profile greeting with name`) above text initializers containing interpolated parameters.

### 1.5 Soft-Deprecated APIs
*   Proactively migrate away from soft-deprecated APIs during feature work:
    *   Replace `NavigationView` with `NavigationStack` or `NavigationSplitView`.
    *   Replace old `.onChange(of:perform:)` with the modern `.onChange(of:initial:_:)` overload.

---

## 2. SwiftUI 2027 (iOS 27 / Xcode 27+) Rules

### 2.1 `@State` Macro Migration Compile Defense (Critical)
*   In SDK 27, `@State` migrated from a property wrapper to a Swift Macro. This can cause build errors like `"variable used before being initialized"` or `"invalid redeclaration of synthesized property"`.
*   **Critical Guardrail**: **Do not** fix these errors by simply reordering assignments in your custom `init`. Doing so compiles but causes incorrect runtime behavior. You MUST follow the exact migration steps documented in `state-macro.md` (e.g., removing synthesized properties).

### 2.2 Drag-to-Reorder API
*   Use `.reorderable()` on `ForEach` and `.reorderContainer(for:)` on the parent container to implement drag-to-reorder for any scrollable stack or grid (not just `List`).
*   Implement `ReorderDifference` application safely to keep your data source synchronized when items are swapped.

### 2.3 `AsyncImage` Caching
*   `AsyncImage` applies standard HTTP caching by default.
*   For per-request cache policies, use the `AsyncImage(request:)` initializer taking a `URLRequest`.
*   To supply custom session behaviors or credentials, apply the `.asyncImageURLSession(_:)` modifier.

### 2.4 Layout & Presentation APIs
*   **Toolbar Constraints**: Control visible items vs. overflow using `visibilityPriority` and `ToolbarOverflowMenu`. Pin critical actions via `topBarPinnedTrailing`.
*   **Optional Item Binding Sheets**: Present dialogs and alerts using the `confirmationDialog(item:)` and `alert(item:)` overloads. They trigger presentation when the bound optional item is non-nil and pass the unwrapped value to actions.
*   **Generic Swipe Actions**: Enable side-swipe actions on rows in any scrollable container (e.g., ScrollView + LazyVStack) by marking the container with `swipeActionsContainer()` and applying `swipeActions()` to the rows.
*   **Document-based Apps**: For new document apps or read-only viewers targeted at iOS 27+ / macOS 27+, use `ReadableDocument` and `WritableDocument` instead of `ReferenceFileDocument` or `FileDocument`.

---

## 3. UIKit Modernization

### 3.1 Eliminate Global Shared-State APIs
*   To support multi-window environments (iPadOS, macOS Catalyst), **never** access screen or orientation properties globally.
*   **Do not use** `UIScreen.main` or `UIScreen.mainScreen`.
    *   Replace `UIScreen.main.scale` with `self.traitCollection.displayScale` inside view or view controller methods.
    *   In methods like `layoutSubviews`, `draw(_:)`, `updateConstraints()`, or `viewIsAppearing(_:)`, read the trait collection directly. UIKit handles updates automatically; do not register manual observers.
*   **Do not use** `interfaceOrientation` or `statusBarOrientation`. Rely instead on horizontal/vertical size classes (`UITraitCollection.horizontalSizeClass`/`verticalSizeClass`) or check the view's bounds aspect ratio dynamically.

### 3.2 Avoid Window Walk-Ups
*   Do not traverse `UIApplication.shared.windows` or search global state to locate a window or scene context inside non-view classes.
*   Refactor methods to accept the current `UITraitCollection` or `UIWindowScene` as an explicit argument.

---

## 4. Swift Testing Modernization

### 4.1 Test Structure & Migration
*   **Imports**: Replace `import XCTest` with `import Testing`. Add `import Foundation` explicitly if XCTest's implicit Foundation re-export was relied upon.
*   **Suites**: Remove `XCTestCase` inheritance. Declare test suites as `struct` types. Swift Testing reinvokes initializers fresh for each test, ensuring isolated execution.
*   **Setup & Teardown**:
    *   Migrate `override func setUp()` to `init()` (can be async/throwing).
    *   Migrate `override func tearDown()` to `deinit`.
    *   *Note*: Structs do not support `deinit`. If teardown code is required, declare the test suite as a `final class` or `actor`.
*   **Method Naming**: Remove the `test` prefix and use the `@Test` attribute. For long names, use raw identifiers with backticks (e.g., `@Test func `Authenticate, fetch summary, then check count`()`).

### 4.2 Assertions Mapping
*   Map standard checks to expectations: `XCTAssert(x)` -> `#expect(x)`.
*   For assertions where failure should halt execution (i.e., `continueAfterFailure = false` or `XCTUnwrap(x)`), use `try #require(x)` instead.
*   **Asynchronous Expectations**: Replace `XCTestExpectation` and wait APIs with `confirmation("...") { confirm in ... }`.

### 4.3 Incompatible Cases
*   **UI Tests**: Tests relying on `XCUIAutomation` (e.g., `XCUIApplication`) are unsupported by Swift Testing and **must** remain `XCTest`.
*   Tests utilizing performance measurement APIs like `measure { ... }` must remain in `XCTestCase`.

---

## 5. Xcode Security Configurations

### 5.1 Compiler Warning Flags
*   Enable these warning-to-error rules on all C/C++/Objective-C targets:
    *   `GCC_WARN_ABOUT_RETURN_TYPE = YES_ERROR`
    *   `GCC_WARN_UNINITIALIZED_AUTOS = YES_AGGRESSIVE`
    *   `CLANG_WARN_IMPLICIT_FALLTHROUGH = YES`
    *   `GCC_TREAT_IMPLICIT_FUNCTION_DECLARATIONS_AS_ERRORS = YES` (C/ObjC only)
*   Enable project-level Enhanced Security:
    *   Set `ENABLE_ENHANCED_SECURITY = YES` to activate Hardened Heap, Stack Zero Initialization, and Read-Only Platform Memory.

### 5.2 Pointer Authentication (arm64e) Override
*   If a project links prebuilt binary dependencies (e.g., XCFrameworks) that lack `arm64e` support, compilation will fail when Enhanced Security is enabled.
*   **Correct Mitigation**: Override `ENABLE_POINTER_AUTHENTICATION = NO` only at the target level on the affected targets. Do not turn off project-level `ENABLE_ENHANCED_SECURITY`.

---

## 6. C/C++ Bounds Safety (`-fbounds-safety`)

### 6.1 Pointer Annotations
*   Decorate pointer declarations with explicit bounds attributes:
    *   `__counted_by(N)` / `__counted_by_or_null(N)`: Specifies that the pointer points to `N` elements.
    *   `__sized_by(Bytes)`: Specifies bounds in bytes.
    *   `__single`: Restricts pointer arithmetic on single-object pointers.
    *   `__null_terminated`: Specifies a null-terminated pointer.
*   Avoid `__unsafe_indexable` unless interacting with legacy APIs that cannot be annotated.

---

## 7. Device Interaction & Verification

### 7.1 Automated UI Verification
*   After implementing user-facing changes, verify behavior using simulator or hardware interaction sessions.
*   **Precise Interaction**: Query the UI hierarchy and use the resolved `center` coordinates (e.g., `center: {125.0, 215.0}`) for touch events. Do not estimate positions from screenshots.
*   **Crash Monitoring**: Monitor application processes during test execution to capture unexpected exits and inspect crash logs or console outputs.

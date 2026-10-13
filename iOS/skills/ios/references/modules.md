# iOS: dependency injection and modules

Follow what the project does. Facts checked 2026-10-13 against Apple's documentation and release notes and the libraries' repositories.

## Dependency injection

Default: pass dependencies through initialisers, typed as protocols where a test needs a fake, and build the graph in one place (the app or scene delegate, the `App` struct, or the root coordinator). A type that reaches for a global to find its collaborators hides them.

| The project uses | How to add a dependency | Trap |
|---|---|---|
| initialisers and one composition root | a new initialiser parameter, wired at the root | a default argument that creates the real service hides the dependency from tests |
| SwiftUI environment | `@Entry` in an `EnvironmentValues` extension (Xcode 16 and later; it back-deploys), or `.environment(object)` read with `@Environment(Type.self)` | `@Environment(Type.self)` crashes when nothing was injected; the environment does not cross a `UIHostingController` |
| Factory 3 (`import FactoryKit`) | an entry in an `extension Container`; read with `@Injected(\.service)` or `Container.shared.service()` | the import was `Factory` before 2.5; a `@MainActor` factory resolved off the main actor traps; test targets link `FactoryTesting`, never a second copy of FactoryKit |
| swift-dependencies (`@Dependency`) | a `DependencyKey` or `@DependencyEntry` with live and test values | values travel in task locals: an escaping closure (GCD, Combine) loses them without `withEscapedDependencies`. A test that reaches a live value fails on purpose. Never a `static @Dependency` |
| Swinject | `container.register` and `resolve` | a failed `resolve` returns `nil` at run time; no commits since September 2025; in Swift 6 mode an existential argument must be cast or `resolve` returns `nil` |
| Needle | a component, plus generated code | generated at build time; maintenance is sporadic |

- After changing a run-time container, launch the app or run a test that resolves the graph. A build proves nothing about it.
- Under Swift 6 a container is shared mutable state. Do not quiet its diagnostics with `nonisolated(unsafe)` or `@unchecked Sendable` in app code; use the pattern the library documents.
- Previews and tests need replacements. See how this project supplies them before adding a dependency that a preview cannot build.

## Modules

**When.** A module earns its cost when it shortens builds for a large app, keeps features from importing each other, or is shared with an extension or another app. Each one adds a manifest, resource handling and a linking decision.

**Local Swift packages.**

- Leave the library type unspecified (no `.static` or `.dynamic`) and let the consumer decide.
- **Resources.** `Bundle.module` exists only inside the package's own module and is internal: expose what others need through public API. It is a `fatalError` when the resource bundle is not where it is expected, which shows up in unusual hosts such as a test target that uses a dynamic library from another package.
- **Linked twice.** A package linked statically into two dynamic products (the app and a framework, or the app and an extension) gives Xcode's "linked as a static library by 'A' and 'B' ... duplication of library code" error, or at run time "Class X is implemented in both". Code shared by an app and its extension goes through one dynamic framework.
- **Access control is the module's contract.** `public` only for what other modules use, `package` for what the package's own targets share.
- A package using Swift 6.2's default main-actor isolation sets it per target (`.defaultIsolation(MainActor.self)`). It does not inherit the app's setting.
- Macro-heavy dependencies (TCA, swift-dependencies) bring in swift-syntax. Xcode 26 downloads prebuilt copies, and CI needs `-skipMacroValidation`.

**Generated projects.**

- XcodeGen (`project.yml`) and Tuist (`Project.swift`) generate the `.xcodeproj`. When the profile shows one, edit the manifest and regenerate; never edit the generated project.
- Tuist's module cache and selective testing work only with generated projects. Its command-line tool is MIT; its server parts carry other licences, and self-hosting the server needs a paid plan.
- Buildable folders (Xcode 16 and later) make the project follow the folder: a new file needs no project edit. The session profile says whether this project uses them.
- A JSON project format (`.xcproj`) works from Xcode 27, is the default from 27.2, and cannot be opened by Xcode 26. Do not convert a project unasked.

**Build time.**

- Xcode 26 builds Swift with explicit modules by default, and compilation caching depends on them. Targets with the same dependencies but different compiler flags or macros cannot share built modules: keep build settings uniform across modules.
- Mergeable libraries (Xcode 15 and later) give dynamic frameworks in debug and one merged binary in release, for framework targets of the project.
- Read the build timeline before splitting or merging modules.

## Mistakes to expect from yourself

1. A singleton reached from inside a type that could have taken it as a parameter.
2. Calling a container change done because it compiled.
3. `Bundle.main` for a resource that lives in a package, or `Bundle.module` used from another module.
4. Forcing `.dynamic` or `.static` on a package product to quiet a link error without finding who links it twice.
5. Everything `public` in a new module.
6. Editing a generated project, or adding a file reference by hand in a project with buildable folders.

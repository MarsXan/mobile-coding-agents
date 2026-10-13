# iOS: build, test, sign, resolve

## Know what you are building

- `xcodebuild -list -json` lists schemes, targets and configurations. A project with a `Podfile` builds through the **workspace**, never the `.xcodeproj`.
- `xcodebuild -showBuildSettings -scheme <S> -json` is the truth about a setting. Precedence, strongest first: command line, target settings, target `.xcconfig`, project settings, project `.xcconfig`, defaults. A value set on the target silently overrides the xcconfig; fix that by removing the target-level value. Use `$(inherited)` to append.
- If `project.yml` (XcodeGen) or `Project.swift` (Tuist) exists, the `.xcodeproj` is generated. Edit the manifest and regenerate.

## Commands

```sh
# Build for the simulator, no signing
xcodebuild build -workspace App.xcworkspace -scheme App \
  -destination 'generic/platform=iOS Simulator' -derivedDataPath <dir> -quiet CODE_SIGNING_ALLOWED=NO

# Test on a specific simulator, keep a result bundle
xcrun simctl list devices available
xcodebuild test -workspace App.xcworkspace -scheme App \
  -destination 'platform=iOS Simulator,id=<UDID>' -resultBundlePath out/Tests.xcresult -quiet
xcrun xcresulttool get test-results summary --path out/Tests.xcresult
```

- Narrow a run with `-only-testing:Target/Class/method` or `-testPlan <name>`. Split compile from run with `build-for-testing` and `test-without-building`.
- Flaky test: `-test-iterations 20 -run-tests-until-failure`, and `-parallel-testing-enabled NO` to expose order dependence.
- Use a separate `-derivedDataPath` for agent builds. Sharing Xcode's DerivedData while Xcode has the project open causes "database is locked" and index contention.
- Resolve packages with `xcodebuild -resolvePackageDependencies` or `swift package resolve`. `Package.resolved` is committed and never hand-edited.
- `-skipPackagePluginValidation` and `-skipMacroValidation` let build plugins and macros run without the trust prompt. They execute code at build time: CI only, vetted packages only.
- `mobile verify` wraps these and prints only the failures.

## What a failure means

| Message | Cause and next step |
|---|---|
| `No such module 'X'` | X was not built for this target and configuration. Check: building the workspace (CocoaPods), the package product is linked to this target, the scheme builds the dependency. Cleaning rarely fixes it. |
| `Cannot find 'X' in scope` for a file just created | The file is not a member of the target. See "Project file". |
| `Command PhaseScriptExecution failed` | A Run Script phase failed (SwiftLint, a code generator, a CocoaPods script). The script's own error is a few lines above. If it mentions `Sandbox: ... deny`, the script reads or writes a file it did not declare (`ENABLE_USER_SCRIPT_SANDBOXING`): declare the input and output files; do not turn the sandboxing off globally. |
| `Signing for "X" requires a development team`, `No profiles for ... were found`, `doesn't include signing certificate` | Signing. For simulator builds pass `CODE_SIGNING_ALLOWED=NO`. For device or archive builds do not change the team, bundle identifier or entitlements, and do not add `-allowProvisioningUpdates`, to make it pass: ask. |
| `Multiple commands produce ...` | The same file is in two targets or build phases, or two dependencies ship the same resource. Find and remove the duplicate. |
| `Undefined symbol(s) for architecture arm64` | Link time: a library missing from the target, a static/dynamic mismatch, a binary without the needed slice, or Objective-C categories needing `-ObjC`. |
| `building for 'iOS-simulator', but linking in object file built for 'iOS'` | A binary dependency has no simulator slice; it needs an XCFramework. Do not add `EXCLUDED_ARCHS = arm64` for the simulator unless the project already does. |
| `The compiler is unable to type-check this expression in reasonable time` | Split the expression, add explicit types, break a large SwiftUI `body` into smaller views. |
| `Module compiled with Swift X cannot be imported by the Swift Y compiler` | A prebuilt framework without library evolution; it needs a rebuild for this toolchain. |
| SwiftPM `dependencies could not be resolved` | Read the constraint chain and adjust the version requirement. Deleting `Package.resolved` upgrades everything silently. |
| CocoaPods `could not find compatible versions`, `sandbox is not in sync with the Podfile.lock` | `pod install`, not `pod update`. `pod update <Pod>` only when upgrading that pod is the task. |
| `Unable to find a destination matching ...` | That simulator name or OS does not exist here. List devices and use an `id`. |
| `Test runner exited before starting test execution` | The app crashed at launch in the test host. Read the crash log in the result bundle. |

## Project file

- **Synchronized folders** (Xcode 16+, the project profile does not say "explicit file references"): a file created under a synchronized folder belongs to the target automatically. Do not edit the project file to add it.
- **Explicit file references** (older projects): a new source file needs a file reference, a build file, a group entry and a build-phase entry. Make the smallest edit, keep order and identifiers, then confirm with `xcodebuild -list` and a build. If that is not clearly safe, create the file and ask the user to add it in Xcode.
- **JSON project file** (`.xcproj` inside the `.xcodeproj`, supported from Xcode 27 and the default for new projects from 27.2): edit it as structured JSON, and still confirm with `xcodebuild -list`.

## Simulator

```sh
xcrun simctl boot <UDID>
xcrun simctl install booted path/to/App.app
xcrun simctl launch --console-pty booted <bundle id>        # app stdout in the terminal
xcrun simctl openurl booted "myapp://path"                  # deep links
xcrun simctl push booted <bundle id> payload.apns           # push payloads
xcrun simctl privacy booted grant photos <bundle id>        # permission states
xcrun simctl io booted screenshot out.png
xcrun simctl get_app_container booted <bundle id> data      # inspect files and databases
xcrun simctl spawn booted log stream --predicate 'subsystem == "<subsystem>"'
```

`simctl erase` and `simctl delete` destroy simulator data: installed apps, their databases and keychains.

## CocoaPods status

CocoaPods is in maintenance mode and its registry becomes read-only on 2 December 2026: existing installs keep working, new pod versions stop arriving. A project still on CocoaPods should plan the move to SwiftPM; see `legacy.md`.

## Inside Claude Code's sandbox (tested with Xcode 26 and Claude Code 2.1.296)

- **`xcodebuild` and `simctl` do not work sandboxed.** They cannot reach the simulator service, and the build fails even with DerivedData inside the project. They must be listed in `sandbox.excludedCommands`, which runs them with full access through the normal permission flow.
- **SwiftPM works sandboxed** with two things: `--disable-sandbox` on `swift build` and `swift test` (SwiftPM starts its own sandbox, and sandboxes do not nest), and write access to the per-user compiler cache and temp directories (`getconf DARWIN_USER_CACHE_DIR`, `getconf DARWIN_USER_TEMP_DIR`).
- `mobile verify` detects the sandbox, adds `--disable-sandbox` itself, and says so plainly when it is asked to run `xcodebuild` inside one.

Settings are in the toolkit's `docs/03-setup-and-validation.md`.

# React Native: native modules, native views and config plugins

Facts checked 2026-10-13 against reactnative.dev, docs.expo.dev and the libraries' repositories.

## Before writing native code

1. Does a maintained library already do it? In an Expo project check the Expo SDK first, then React Native Directory. `npx expo-doctor` flags unmaintained or incompatible packages.
2. Is it only a native **setting** (a permission text, a build property, an entitlement, a manifest entry)? In a project with generated native folders that is an app-config key or a config plugin, not native code.
3. Only then write a module. Pick the kind the project already uses.

## The three ways to write a native module

| | Use when | Notes |
|---|---|---|
| Turbo Native Module / Fabric component (React Native core) | a bare project, or a library that must not depend on Expo; needed when C++ is shared | typed spec file, Codegen generates the glue |
| Expo Modules API (Swift and Kotlin DSL) | the project uses Expo; the least boilerplate | needs the `expo` package; supports the New Architecture |
| Nitro Modules | a library already built on it (MMKV 4 is) | still 0.x; do not introduce it for one small module |

Old-style bridge modules (`RCT_EXPORT_MODULE`, `ReactContextBaseJavaModule` with `@ReactMethod`) still load through the interop layer, which is being removed step by step. Do not write new ones.

## Turbo Native Module: the conventions Codegen depends on

- The spec is a TypeScript file in the directory that `codegenConfig.jsSrcsDir` names, and **its file name starts with `Native`** (`NativeLocalStorage.ts`). Codegen finds specs by that prefix.
- It exports `interface Spec extends TurboModule` and, as default, `TurboModuleRegistry.getEnforcing<Spec>('NativeLocalStorage')`. `getEnforcing` throws when the module is missing; `get` returns `null`.
- `package.json` carries `codegenConfig` with `name`, `type` (`modules`, `components` or `all`), `jsSrcsDir`, `android.javaPackageName`, and on iOS the mapping from the JavaScript name to the native class.
- Codegen runs on every Android build and during `pod install` on iOS. **Re-run `pod install` after changing the spec or `codegenConfig`.** Do not commit generated code: it is specific to the React Native version.
- Spec types are limited to what crosses the boundary: numbers, strings, booleans, arrays, plain objects, promises and callbacks. Nullable values must be typed nullable on both sides; a Kotlin `toString()` on a nullable silently turns "missing" into the text "null".

## Fabric native component

- The spec file name **ends in `NativeComponent`** (`MapViewNativeComponent.ts`) and its default export is `codegenNativeComponent<NativeProps>('MapView')`.
- Android: a view manager that extends `SimpleViewManager` and implements the generated interface. iOS: a view that extends `RCTViewComponentView`, in Objective-C++.
- Events are typed in the spec (`DirectEventHandler`, `BubblingEventHandler`); commands go through `codegenNativeCommands`.

## Linking

- Autolinking finds a library through its podspec at the package root (iOS) and its Gradle module (Android). A library in a monorepo, or one that was only added to `package.json` and not installed, will not link.
- After adding any package with native code: reinstall pods and rebuild the app. A JavaScript reload is not enough.

## Config plugins (Expo)

- A plugin is a function that changes the native projects during prebuild: `withInfoPlist`, `withAndroidManifest`, `withEntitlementsPlist`, `withAppBuildGradle`, `withDangerousMod` for anything else. It is listed under `plugins` in the app config, with options.
- Prefer, in this order: an app-config key (`ios.infoPlist`, `android.permissions`, `ios.entitlements`), the options of a plugin that already exists (`expo-build-properties` for SDK levels, deployment target and build flags), then your own plugin.
- A plugin must be **idempotent**: prebuild can run many times on existing folders (`--no-clean`). Check before inserting.
- `withDangerousMod` and string edits of Gradle files or the Podfile break on template changes. Use them last, and keep the edit small and anchored.
- Test a plugin by running `npx expo prebuild` and reading the generated files, then building.

## Threads and lifecycle

- A module method is not called on the main thread by default. Touch UIKit or Android views only after hopping to the main thread.
- Long work goes off the JavaScript thread: return a promise and do the work on a background queue or a coroutine scope that is cancelled in the module's invalidation hook.
- Emit events only while there are listeners, and remove native observers when the module is invalidated. A reload in development creates a new instance: leftover observers call into a dead one.
- Synchronous methods block the JavaScript thread. Keep them for cheap reads.

## Mistakes to expect from yourself

1. A new bridge-style module in a project on the New Architecture.
2. A spec file whose name does not match the `Native...` or `...NativeComponent` convention, so Codegen never sees it.
3. Editing generated native folders instead of writing or configuring a plugin.
4. Forgetting `pod install` and a rebuild after a spec or dependency change, then debugging "module not found".
5. A config plugin that appends the same line on every prebuild.
6. UI work from a module method without switching to the main thread.

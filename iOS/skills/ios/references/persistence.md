# iOS: stored data and migrations

Anything written to disk by a shipped build is a format. A later build must read it, migrate it, or deliberately discard it. "It works on a fresh install" proves nothing about an upgrade.

## Core Data

**Model versions.**

- A `.xcdatamodeld` holds versions. Never edit a version that has shipped. Add a version (Editor, Add Model Version), make it current, change the new one.
- **Lightweight migration** is automatic with `NSPersistentContainer` and covers: adding or removing an attribute or entity, a new required attribute with a default, renames given a Renaming ID, optional to required with a default, simple relationship changes.
- **Not lightweight**: changing an attribute's type with a transformation, splitting or merging entities, anything that depends on the data. Use staged migration (`NSStagedMigrationManager`, iOS 17+) to break the change into lightweight stages with custom steps between them, or a mapping model with an `NSEntityMigrationPolicy` on older targets.
- **Test it.** Keep a small SQLite store saved by each shipped model version as a test fixture. The test copies it, opens it with the current model and asserts on the migrated data.

**Threading.**

- Managed objects and contexts belong to one queue. Use `context.perform { }` (it is `async` from iOS 15). Pass `NSManagedObjectID` between contexts, never objects.
- `viewContext` is for the main queue only. Write on a background context and set `viewContext.automaticallyMergesChangesFromParent = true` with an explicit merge policy.
- The launch argument `-com.apple.CoreData.ConcurrencyDebug 1` turns threading violations into immediate crashes in debug runs.
- Batch update and delete requests bypass contexts and validation; merge their results into live contexts yourself.
- A store shared with an extension needs persistent history tracking, and writes must finish before suspension or the app is killed with `0xdead10cc`.

**CloudKit mirroring** constrains the model: no unique constraints, every attribute optional or defaulted, every relationship optional with an inverse, and the production schema only ever grows.

## SwiftData (iOS 17+)

- Version the schema from the first release: a `VersionedSchema` per shipped shape and a `SchemaMigrationPlan` passed to the `ModelContainer`.
- **Automatic**: adding an optional or defaulted property, removing a property, adding a model, a rename declared with `@Attribute(originalName:)`.
- **Needs a custom stage**: a type change, a new required property without a default, a new `.unique` attribute when duplicates may exist (deduplicate in `willMigrate`), splitting a model.
- **The trap**: an app that shipped without a versioned schema and now needs a custom migration must first declare a V1 that matches the shipped models exactly; otherwise the store is rejected as an unknown version.
- `ModelContext` and model objects are not `Sendable`. Background work goes in a `@ModelActor`; pass `PersistentIdentifier` values across.
- Autosave is not a durability guarantee. Call `save()` at the points where losing the change is unacceptable.

## Smaller stores are formats too

- **`UserDefaults`.** Keys and value types are a contract. To rename a key: read old, write new, remove old, idempotently, with a test. Not for secrets or large data. Reading it is a required-reason API: declare it in the privacy manifest.
- **Keychain.** Items outlive app deletion: clear stale items on first launch after install if that matters. Choose accessibility deliberately: `AfterFirstUnlock` for anything read in the background, `WhenUnlocked` otherwise, `ThisDeviceOnly` to keep it out of backups and transfers. Changing the access group or team identifier loses access to existing items.
- **`Codable` files and caches.** Decode tolerantly (`decodeIfPresent`, defaults) and carry a version field. A cache that fails to decode is discarded and refetched; it never crashes the app. User documents get a real migration.
- **`NSKeyedArchiver`.** The class name is in the archive. See "Archived classes" in `legacy.md`.
- **Locations.** `Documents` for user-visible data, `Application Support` for app data (both backed up), `Caches` for what can be regenerated (purged by the system), `tmp` for scratch. Files read in the background need a protection class that allows it.

## Before merging a storage change

1. Which shipped versions wrote the old format, and is the path from the oldest one tested?
2. What happens if the migration is interrupted (process killed, disk full)?
3. Is the change reversible if the release is rolled back, or does the old build now read data it cannot understand?
4. Does an extension, widget or watch app read the same store with its own copy of the model?
5. `mobile risk` reports an edited model version or a `@Model` change without a migration plan. Answer it in the summary.

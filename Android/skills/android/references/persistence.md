# Android: stored data and migrations

Anything a shipped build wrote is a format. The next build must read it, migrate it, or deliberately discard it. A fresh install passing proves nothing about an upgrade.

## Room

**Every entity change is a schema change.**

1. Raise `version` in `@Database`.
2. Provide the path: an `AutoMigration(from, to)` for added tables and columns; with a spec (`@RenameColumn`, `@DeleteColumn`, `@RenameTable`) for renames and deletions; a hand-written `Migration(from, to)` for anything else.
3. Export schemas (`exportSchema = true` with the schema location set through the Room Gradle plugin or a KSP argument) and commit `schemas/<database>/<version>.json`. Auto-migrations and migration tests need them.
4. Test with `MigrationTestHelper`: create the database at the old version, insert rows with SQL, run the migration with validation, and assert on the data. Also open the newest schema with **all** migrations from the oldest shipped version.

Details that fail in production:

- A new `NOT NULL` column needs a default, and the `@ColumnInfo(defaultValue = ...)` must match the migration SQL exactly, or validation fails with "Migration didn't properly handle".
- Indices and foreign keys in the migration must match the generated schema exactly.
- Old SQLite versions cannot drop or alter a column: create the new table, copy, drop, rename.
- `fallbackToDestructiveMigration` deletes the user's data on upgrade. It is a product decision, never a build fix.
- Never edit a `Migration` that has shipped.
- A type-converter change does not change the schema but does change the stored data. It needs a data migration too. Enums are stored by name; renaming a constant orphans existing rows. Never store ordinals.

Use: suspend DAO functions and `Flow` queries are main-safe; `allowMainThreadQueries` is not a fix. Multi-statement work goes in `@Transaction` or `withTransaction { }`. A `Flow` query re-emits on any change to its tables: add `distinctUntilChanged()`.

## DataStore

- Preferences DataStore keys and Proto DataStore schemas are formats. In a proto, never reuse or renumber a field.
- One DataStore instance per file in the process; a second one corrupts it or throws.
- Reading is asynchronous. `runBlocking { dataStore.data.first() }` on the main thread at startup is an ANR risk; load it before it is needed.
- Move from SharedPreferences with `SharedPreferencesMigration`, as its own change, with a test.

## SharedPreferences (legacy)

- Keys and value types are a format: reading an `Int` where an old build wrote a `String` throws `ClassCastException`. Migrate under a new key.
- `apply()` is asynchronous; `commit()` blocks. Neither belongs in a hot path.
- `EncryptedSharedPreferences` comes from a library that has been deprecated. Do not introduce it. Where it is in use, plan a migration that reads the old store and handles data that can no longer be decrypted.

## Files and scoped storage

- Internal storage (`filesDir`, `cacheDir`) needs no permission. The cache can be cleared by the system.
- Shared storage goes through MediaStore, the Storage Access Framework or the photo picker. Broad external-storage access is restricted by platform and by Play policy.
- Share files with a narrowly scoped `FileProvider`, never a `file://` URI.

## Backup and device transfer

Auto Backup copies preferences, files and databases to the user's next device unless excluded (`dataExtractionRules`, `fullBackupContent`).

- Exclude tokens, device-specific identifiers and anything encrypted with a Keystore key. Keystore keys do not transfer, so restored ciphertext cannot be decrypted.
- Code that decrypts stored data must survive failure: wipe that data and sign the user out, not crash on every launch.

## Serialised models

- A model written to disk or cached is a format, whichever library writes it. Pin names (`@SerialName`, `@SerializedName`, `@Json(name = ...)`), tolerate unknown and missing fields, and treat enum names as part of the format.
- R8 renames fields used by reflective serialisers; pinned names and keep rules prevent release-only data loss.
- A cache that fails to decode is discarded and refetched. It never crashes the app.

## Before merging a storage change

1. Which shipped versions wrote the old format, and is the path from the oldest tested?
2. What happens if the migration is interrupted?
3. If the release is rolled back, can the old build read what the new one wrote?
4. Does backup and restore to another device still work?
5. `mobile risk` reports an entity change without a version bump, a version bump without a migration, a destructive fallback, and a missing exported schema. Answer each in the summary.

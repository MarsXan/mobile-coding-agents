# Flutter: stored data and migrations

Anything a shipped build wrote is a format. The next build must read it, migrate it, or deliberately discard it. A fresh install passing proves nothing about an upgrade.

## drift

1. Any table change raises `schemaVersion`.
2. `MigrationStrategy.onUpgrade` gets a step for it. Use drift's schema tooling (`dart run drift_dev make-migrations`): it saves each version's schema, generates step-by-step migration helpers, and scaffolds tests.
3. Test with `SchemaVerifier`: migrate from each old version and validate against the expected schema, and assert on the data that was there.
4. Enable foreign keys in `beforeOpen` (`PRAGMA foreign_keys = ON`) if the app relies on them; SQLite has them off by default.
5. Never change a migration step that has shipped.

## sqflite

- `onCreate` builds the **latest** schema for fresh installs. `onUpgrade` takes old installs there. They must end in the same schema: updating one and not the other is the classic bug. Test both and compare.
- `onUpgrade` handles every starting version: loop from `oldVersion + 1` to `newVersion` and apply each step in order.
- There is no migration test helper. Keep a database file from each shipped version as a fixture and open it in a test.

## Hive (and hive_ce)

- `typeId` and each `@HiveField(n)` index are the on-disk format. Never change or reuse one. A removed field's index stays retired.
- New fields must be nullable or have a default, because old records do not have them.

## shared_preferences

- Keys and value types are a format. Reading a different type than an old build wrote throws.
- The newer asynchronous API can use a different native store than the legacy one. Switching without the package's migration helper makes existing values disappear.
- Not for secrets, and not for large or structured data.

## flutter_secure_storage

- Backed by the Keychain on iOS and the Keystore on Android.
- Android backup restores the encrypted data without the key. After a restore or reinstall, reads fail to decrypt: catch that, wipe the stored values, and send the user through sign-in again. Exclude the storage from backup where possible.
- iOS Keychain items survive app deletion. Clear stale ones on first launch after install if that matters.
- Choose iOS accessibility deliberately: values read in the background need "after first unlock".

## Files

- `getApplicationDocumentsDirectory` for user data, `getApplicationSupportDirectory` for app data, `getTemporaryDirectory` for what can be regenerated.
- **Store relative paths, never absolute ones.** On iOS the container path changes between installs and updates; an absolute path saved last week points nowhere today.

## Models

- A model that is persisted or cached is a format, whatever generates its `fromJson`. Pin names with `@JsonKey(name: ...)`, give missing fields defaults, and set `unknownEnumValue` for enums.
- One malformed item must not take the whole list down. Skip and log it.
- A cache that fails to decode is discarded and refetched. It never crashes the app.
- Dates are stored in UTC, ISO 8601. Money is stored as integer minor units or a decimal type, never `double`.

## Before merging a storage change

1. Which shipped versions wrote the old format, and is the path from the oldest tested?
2. What happens if the migration is interrupted?
3. If the release is rolled back, can the old build read what the new one wrote?
4. Does it survive backup and restore on Android and a reinstall on iOS?
5. `mobile risk` reports a drift table change without a `schemaVersion` bump, a bump without a migration step, and a changed `@HiveField`. Answer each in the summary.

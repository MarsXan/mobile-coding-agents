# React Native: stored data

Data on a user's device outlives the build that wrote it. Facts checked 2026-10-13 against each library's documentation and repository.

## What each store is, and its trap

| Store | What it is | Trap |
|---|---|---|
| AsyncStorage | asynchronous key-value strings, **not encrypted** | version 3 has a different API from 2 (instances from `createAsyncStorage(name)`; callbacks, `merge` and the hook removed) and Expo SDK 57 still pins 2.x. On Android the 2.x default total is about 6 MB and one entry about 2 MB |
| MMKV | synchronous key-value, fast | plain text unless an `encryptionKey` is set. Version 4 is a Nitro Module (`createMMKV()`, `.remove()`), needs a development build, and does not run in Expo Go |
| expo-sqlite | SQLite | you write the migrations: `PRAGMA user_version` in the provider's `onInit`. The libSQL option is removed in SDK 58 |
| op-sqlite | fast SQLite | no migration feature; no Expo Go |
| WatermelonDB | reactive database on SQLite | **raising the schema version without a migration resets the database**. The project has been quiet since 2025 |
| Realm | object database | MongoDB ended the Atlas Device SDKs and Sync in September 2025; the local database continues as a community project. Do not start new work on it |
| expo-secure-store, react-native-keychain | Keychain on iOS, Keystore-backed on Android | for small secrets only. **On iOS a value survives uninstalling the app**; on Android it does not |

## Rules

- **Tokens, keys and anything secret go in secure storage**, never in AsyncStorage or unencrypted MMKV. React Native's own security guide says so.
- **Every stored shape is a format.** Key names, the JSON inside a value, a persisted Redux or Zustand slice, a SQLite table: an installed app still holds what the previous version wrote.
- **Key-value stores have no schema, so you version the values yourself.** Store a version number with the data, or use the migration hook of the persistence layer:
  - `redux-persist`: `version` and `migrate` (`createMigrate`). Without them a changed state shape is rehydrated as it was written.
  - Zustand `persist`: `version` and `migrate`. If the stored version differs and there is no `migrate`, the stored state is dropped.
  - TanStack Query persister: a `buster` string invalidates the cached data.
- **SQL**: a table change needs a numbered migration and a test that opens a database created by the previous version. Run all pending steps in one transaction and write the new `user_version` last.
- **Renaming a key or a storage instance orphans what was stored under the old one.** Read the old key, write the new one, then delete the old one.
- **Do not store derived data or whole API responses "for later"** without an expiry and a version. Server data belongs to the query cache.
- **Sign-out and account deletion** must clear every store: key-value entries, the database, the query cache, secure-storage items, files. On iOS secure-storage items remain after an uninstall, so a reinstall can find an old session: decide what that should mean.

## Encryption

- Encrypting MMKV or SQLite (SQLCipher) needs a key, and the key lives in secure storage. A key written in the JavaScript source or an environment variable is readable from the app bundle.
- SQLCipher is not available in Expo Go.

## Files

- Use the app's document directory for data the user would miss and the cache directory for what can be rebuilt; the OS may empty the cache at any time.
- Several `expo-file-system` calls became async in SDK 56 and 58. Check the installed version before copying an example.
- A path is not stable across installs on iOS: store a path relative to the document directory, not the absolute one.

## Testing a storage change

- A unit test that feeds the **old** stored value into the new code: the migration function, the `persist` config, or the database opened from a fixture written by the previous schema.
- A test for the first launch with nothing stored, and for a value that is corrupt or half-written.
- On a device: install the previous release, create data, then install the new build on top. This is the only test that sees the real upgrade path.

## Mistakes to expect from yourself

1. A token in AsyncStorage.
2. A persisted store whose shape changed with no `version` and `migrate`.
3. A WatermelonDB or SQLite schema change with no migration.
4. Code written for AsyncStorage 3 or MMKV 4 in a project that has the older major installed, or the reverse.
5. A renamed key, with the old data silently left behind.
6. Assuming an uninstall cleared the iOS Keychain.

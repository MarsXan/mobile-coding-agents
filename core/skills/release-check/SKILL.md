---
name: release-check
description: Pre-release readiness check for a mobile build, comparing it with the previous release - contents, risk signals, verification, data migrations, compatibility, versioning, store requirements, rollout and rollback. Produces a go or no-go report and changes nothing.
disable-model-invocation: true
argument-hint: "[tag or branch of the previous release]"
allowed-tools: Bash(mobile risk *) Bash(mobile verify *) Bash(mobile detect *) Bash(git log *) Bash(git diff *) Bash(git tag *) Bash(git describe *)
---

# Release readiness

Produce a go or no-go report for the build about to ship, compared with the previous release: `$ARGUMENTS`, or the latest release tag from `git describe --tags --abbrev=0` if none was given. Check and report. Do not fix, upload, tag or publish anything.

1. **What is in it.** `git log <previous>..HEAD --oneline`, grouped into user-visible changes, internal changes, and dependency or toolchain changes. Flag any change with no linked ticket or description.
2. **Risk signals.** `mobile risk --base <previous> --fail-on never`. Every `block` and `warn` needs an owner's answer in the report.
3. **Verification.** `mobile verify --level full`. Report exactly what ran, and what could not run here.
4. **Data.** Every storage or schema change since the previous release has a migration and a test that starts from the **previous released** version, not just the previous commit. The upgrade path from the oldest version still in use is known.
5. **Compatibility.** The minimum OS is unchanged, or the drop is announced. Server contracts still serve the previous app versions. Deep links and push payloads are unchanged or versioned.
6. **Versioning.** Marketing version and build number are bumped and consistent across targets and flavors. Release notes exist.
7. **Build hygiene.** Release configuration. No debug flags, test endpoints, verbose logging or disabled certificate checks. Shrinking and obfuscation on where the project uses them. dSYMs, R8 mapping files and Flutter symbol files are archived for this build.
8. **Store and platform requirements.** Load the platform skill's `release.md` for the current checks: SDK and target-API deadlines, privacy manifest and data-safety declarations, permission purpose strings. Confirm dates on the official pages; these requirements change every year.
9. **Flags and rollout.** New risky paths are behind a flag that defaults to the safe side. The staged-rollout percentage, the metric thresholds that pause it, who watches, and the rollback plan are written down.
10. **Accessibility and localisation** of the changed screens: screen-reader labels, largest text size, right-to-left if supported, missing translations.

Report `GO`, `GO with conditions` or `NO-GO`; then the blockers or conditions with an owner each; then what was not verified.

---
name: release-b4a-plugin
description: Repackage the Adivery B4A plugin zip with the latest Adivery SDK .aar and publish it as a new GitHub release. Use when the user wants to cut/release a new version of the adivery-b4a-plugin after a newer Adivery Android SDK aar (sdk-X.Y.Z.aar) is available — it swaps the bundled aar inside adivery-b4a.zip, re-zips it, and creates a GitHub release on adivery/adivery-b4a-plugin with the zip attached.
---

# Release the Adivery B4A plugin

Cut a new release of the B4A plugin by swapping the bundled Adivery SDK
`.aar` inside the distributable `adivery-b4a.zip`, then publishing it as a
GitHub release. The companion script
[`package-and-release.sh`](package-and-release.sh) does the repackaging and
the GitHub API work; your job is to gather the inputs and confirm before the
(irreversible) publish.

## What the script does

The plugin zip has this internal layout — only the **aar** is replaced:

```
adivery-b4a/Adivery.aar   <- bundled SDK binary  (SWAPPED)
adivery-b4a/Adivery.jar   <- compiled B4A wrapper (untouched)
adivery-b4a/Adivery.xml   <- B4A library descriptor (untouched)
```

The release flow is failure-safe: **create draft → upload asset → publish**.
A partial failure leaves a private draft (never a broken public release).
It refuses to overwrite an existing tag.

> Note: this is a **binary-only swap** — it does not recompile `Adivery.jar`.
> If the new SDK added public APIs, the B4A wrapper won't expose them until
> someone rebuilds the jar with the B4A LibraryCompiler (Windows-only, out of
> scope). This matches existing practice for this repo.

## Steps

1. **Find the inputs.** Auto-detect what the script would pick (newest
   `sdk-*.aar` and `adivery-b4a.zip`, by default in `~/Downloads`):

   ```bash
   ls -t ~/Downloads/sdk-*.aar 2>/dev/null | head -1
   ls -l ~/Downloads/adivery-b4a.zip 2>/dev/null
   ```

   If either is missing or in another folder, ask the user for the path
   (`--aar PATH`, `--zip PATH`, or `--search-dir DIR`).

2. **Ask for the version.** Suggest the version derived from the aar filename
   (e.g. `sdk-4.9.0.aar` → `4.9.0`) and confirm with the user. A leading `v`
   is fine; the script normalizes to tag `v4.9.0`, name `Release v4.9.0`, body
   `Update plugin based on Adivery 4.9.0 version`. Cross-check against the
   latest existing tag so you don't go backwards:

   ```bash
   git ls-remote --tags origin | sed -E 's#.*refs/tags/##' | sort -V | tail -5
   ```

3. **Check the B4A docs dependency table for drift.** `Adivery.aar` is a raw
   local file with no Maven/Gradle resolution behind it, so
   `adivery-docs`' `b4a.md` documents the exact `kotlin-stdlib` / `okhttp` /
   `okio-jvm` / `sentry` jars a B4A developer must add by hand
   (`#AdditionalJar`). Whenever the SDK bumps one of these in
   `gradle/libs.versions.toml`, that doc silently goes stale. Run:

   ```bash
   bash .claude/skills/release-b4a-plugin/check-docs-deps.sh
   ```

   It reads the SDK's version catalog, resolves `okio`'s version from
   `okhttp`'s published POM (okio is transitive, not in our own catalog), and
   diffs both against the table in `b4a.md`. Override `--sdk-repo` /
   `--docs-file` if either repo isn't at the default `~/Workspace/...` path.

   > **Caveat**: this reads whatever commit the SDK repo is *currently*
   > checked out to — make sure that's the same commit/tag that produced the
   > `sdk-*.aar` you're packaging this release, or check out the right tag
   > first.

   If it reports a mismatch, update the version table and `#AdditionalJar`
   lines in `b4a.md` before continuing — or explicitly decide with the user
   to defer it and say why (e.g. docs repo needs its own PR/review cycle).

4. **Confirm the GitHub token.** Check whether it's already in the env:

   ```bash
   [ -n "$GITHUB_TOKEN" ] && echo present || echo MISSING
   ```

   - If **present**, just run the script normally (step 5).
   - If **MISSING**, ask the user for a token (needs `repo` / `contents:write`
     scope). Shell env does **not** persist across separate Bash calls, so pass
     it inline on the *same* command as the script:
     `GITHUB_TOKEN='ghp_xxx' bash .claude/skills/release-b4a-plugin/package-and-release.sh ...`
     Never write the token to a file, never echo it, never commit it.

5. **Confirm, then run.** Show the user the resolved aar, zip, version,
   target repo, and the docs-drift result, and get a go-ahead (publishing is
   public and hard to undo). Then run from the repo root:

   ```bash
   bash .claude/skills/release-b4a-plugin/package-and-release.sh --version <X.Y.Z>
   ```

   Add flags as needed: `--aar`, `--zip`, `--search-dir`, `--out`, `--notes`,
   `--repo`, or `--build-only` (repackage without releasing — good for a dry run).

6. **Report the result.** On success the script prints `RELEASE_URL=…`; share
   it. The repackaged zip is written under the skill's `build/` directory.
   If step 3 found drift and it wasn't fixed yet, remind the user it's still
   outstanding.

## Tips

- To preview without publishing, run with `--build-only` first and inspect the
  output zip (`unzip -l <out>`).
- `--repo` defaults to `adivery/adivery-b4a-plugin`; override only for a fork.
- `check-docs-deps.sh` is read-only — safe to run anytime, not just at
  release time.
- Requires `bash`, `unzip`, `zip`, `curl`, `jq`.

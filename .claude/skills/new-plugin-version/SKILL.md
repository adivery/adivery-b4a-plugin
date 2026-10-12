---
name: new-plugin-version
description: >-
  Bring the Adivery B4A plugin up to a new Adivery Android SDK release, so a
  new plugin version (vX.Y.Z, matching the SDK version) can be released. Use
  when the user asks for a "new plugin version", to "update the plugin to SDK
  X.Y.Z", "sync with the latest SDK release", "bump the SDK", or similar.
  Flow: preflight → pick the target SDK version (Maven Central) → diff the SDK
  API the Java wrapper uses between the published AARs → check the wrapper
  against the AAR, its own @Events, the sample, and the API customers have in
  the published adivery-b4a.zip → read the SDK's behaviour changes → port them
  to the Java wrapper, the sample and the docs → verify on Linux (bridge
  check, javac compile) → commit on a branch → hand the Windows-only
  LibraryCompiler rebuild and device run to the user → verify the rebuilt
  Adivery.jar/Adivery.xml → hand off to release-b4a-plugin to publish. This
  skill never publishes anything itself.
---

# Cut a new plugin version for a new SDK release

The plugin is a thin Java wrapper (`b4a-plugin/src/com/adivery/b4a/*.java`)
around the SDK's public API (`com.adivery.sdk.*`). B4A's LibraryCompiler, which
runs only on Windows (`build.bat`), compiles it into `Adivery.jar` and generates
the library descriptor `Adivery.xml` from its annotations. Both ship in
`adivery-b4a.zip` with the SDK's AAR, renamed to `Adivery.aar`. Customers
download the zip from the latest GitHub release (the docs link
`releases/latest/download/adivery-b4a.zip`). They don't use Maven or Gradle.
They add the SDK's own dependencies by hand as `#AdditionalJar` lines.

Nothing in this repo compiles the wrapper, and four bridges aren't checked by
any compiler:

- **Java → SDK.** A removed or renamed SDK method breaks only when someone
  runs LibraryCompiler. A **new callback** on a listener the wrapper
  subclasses compiles fine without an override, and the event is silently
  never raised to B4A:
  - `AdiveryListener`, in `Adivery.java`;
  - `AdiveryAdListener`, in `AdiveryBannerAd.java`.
- **Java → B4A.** The B4A IDE generates event Subs from the `@Events`
  annotation. At runtime, B4A calls the Sub named by the string passed to
  `raiseEvent`. The raised name must equal the `@Events` name lowercased, with
  the same number of values. Otherwise the customer's Sub never runs, or B4A
  throws on the signature mismatch.
- **B4A code.** `sample/*.b4a`/`*.bas` and the docs' code blocks call library
  members by name. They handle events as `Sub On_X(...)`, or `Sub
  <Prefix>_<Event>` for a banner whose prefix is `Initialize2`'s first
  argument.
- **Published API.** `Adivery.xml` in the latest release is what customers'
  code compiles against, and `Adivery.jar` is what runs. A member it has that
  the source lacks breaks customers once the jar is rebuilt from the source.

Plugin versions track SDK versions 1:1: SDK `X.Y.Z` → release tag `vX.Y.Z`.
Publishing is the **`release-b4a-plugin`** skill's job, not this one's. Its
`package-and-release.sh` swaps the aar, plus the wrapper when given `--jar` and
`--xml`.

Repo: `adivery/adivery-b4a-plugin` on GitHub. SDK sources (optional, used for
the changelog): `$ADIVERY_SDK_REPO`, default
`$HOME/Workspace/AndroidStudioProjects/mobile-android-sdk`. Docs:
`$HOME/Workspace/adivery-docs`, a separate GitLab repo. The Flutter, Unity and
React Native plugins have the same skill (`../adivery-*-plugin/.claude/skills/new-plugin-version`).
When porting a new format, their already-merged ports are a useful reference,
including for the sample's test placement IDs.

Helpers in this skill's `scripts/` (run Python with `python3 -I`; needs `javap`
and `javac`):
- `bridge.py api <aar> <repo>` prints the API of every SDK class the Java uses.
  Diff two of these.
- `bridge.py check <aar> <repo> [--baseline <old.aar>] [--shipped <zip>] [--docs <md>]...`
  checks Java vs AAR, `@Events` vs `raiseEvent`, the sample (and docs) vs the
  wrapper, and, with `--shipped`, that every published class, method, event and
  field is still in the source. It exits 1 on errors.
  - `NOT FORWARDED` lists SDK callbacks the Java doesn't override; with
    `--baseline`, only the ones new since that AAR.
  - `NEW` lists B4A members the published XML doesn't have yet.
- `bridge.py compile <aar> <repo> --android-jar <jar> [--core-jar <Core.jar>]`
  runs javac on the wrapper against the AAR. Without B4A's real `Core.jar`, it
  uses `scripts/b4a-stubs/`, which only proves the SDK side.
- `bridge.py jar <Adivery.jar|zip> <aar> [--repo .] [--baseline <old.aar>]` is a
  bytecode check of a compiled wrapper:
  - every SDK method and field it references exists in the AAR with that exact
    descriptor;
  - every listener method it overrides exists;
  - with `--repo`, its methods match the source, so it catches a stale or
    foreign jar.
- `bridge.py lib <zip|xml|repo>` prints the B4A-facing API, from an
  `Adivery.xml` or derived from the source. Diff two of these.
- The release skill's `check-docs-deps.sh --pom <sdk.pom> --sample <file>...`
  diffs the docs' dependency table and the `#AdditionalJar` lines of the sample
  and `README.md` against the published POM.

## Known state (2026-10-11): remove once a release ships a jar rebuilt from this repo

- **The published `Adivery.jar` was built from code that was never
  committed.** Its classes date from 2021-09; the `v4.9.0` zip still carries
  that jar, and its XML says version 4.8. Since then, releases have only
  swapped the aar.
- **The published API differs from the source.** It has these, and the source
  doesn't:
  - `AddListener(name)` / `RemoveListener(name)`, which raise
    `<name>_On_X` events to the current activity only, through an
    `ActivityChangeListener`;
  - `ShowAppOpen`;
  - banner events `Ad_Loaded`, `Ad_Clicked` and `Ad_Error(error)`.

  The docs document exactly these.
- **The 4.10.0-alpha.1 sync restored it** on the `feat/offerwall` branch (the
  "build: sync B4A wrapper with Adivery SDK 4.10.0-alpha.1" commit and the two
  `sample:` commits after it):
  - every published member is back, rebuilt from the published jar's
    bytecode;
  - OfferWall and `SetUserId` were added;
  - `check --shipped` reports 0 errors over 136 references, and the
    published `Adivery.xml` → source diff is additions only.

  Until that branch's jar is rebuilt and released, a run starting from
  `origin/master` still sees the drift: 111 references, 20 errors.
- **References checked against 4.10.0-alpha.1** (with `--baseline 4.9.0
  --shipped v4.9.0 --docs README.md`, as Phases 2b and 3 run it): 145 for the
  synced `feat/offerwall`, of which 136 are without the README. The
  count grows as the plugin grows. If it collapses, the parsing broke; don't
  read that as success.
- **kotlinx-coroutines.** 4.10.0-alpha.1 is the first SDK version that runs on
  it (63 classes, including `Dispatchers.Main`). It isn't bundled, so B4A apps
  need `kotlinx-coroutines-core-jvm` and `kotlinx-coroutines-android` as
  `#AdditionalJar`. The synced sample and `README.md` have them, and
  `check-docs-deps.sh` tracks them. The Persian docs on the docs repo's
  `offerwall` branch have them too (93e0c33, a local commit). The English
  copies don't.
- **`README.md`** was first written in that sync. Keep its API tables and
  `#AdditionalJar` block current (Phase 3).

## Hard rules

- **Only depend on a version that's on Maven Central**, and only prepare a
  version whose tag `vX.Y.Z` doesn't exist yet.
- **Diff the published artifacts, not sources.**
  - SDK side: the AARs from Maven Central. SDK sources may hold unreleased
    changes.
  - B4A side: `Adivery.xml` and `Adivery.jar` from the latest release's zip.
    The committed wrapper source has drifted from what customers have.
- **Never drop or rename a published B4A member without the user's explicit
  OK.** When the SDK renames something, keep the B4A name and map it to the new
  SDK call. For example, the SDK's `onError` → `log` rename kept the B4A
  `On_Error` event. A removal the user approves goes in the release notes as a
  breaking change.
- **Don't touch the user's uncommitted work.** Gate on changes to **tracked**
  files. If there are any, show them and ask whether to stash or stop. Never
  discard them. Untracked junk (`.idea/`, `*.iml`) stays out of every commit:
  never `git add -A`.
- **Work on a branch from `origin/master`.** Never commit to `master`. Never
  push, open a PR, commit in the docs repo, or publish a release without asking.
- **Keep each file's encoding.**
  - `sample/*.b4a` and `*.bas` are UTF-8 **with BOM**, LF.
  - The Java is ASCII, LF, tab-indented.
  - Edit with the Edit tool. A script that rewrites the file can drop the BOM,
    and B4A needs it.
- **`sample/Files/main.bal` is a binary Designer layout.** Never edit it from
  here. Buttons are added in the B4A Designer (Phase 6).
- **Pre-release versions keep their suffix** (`4.10.0-alpha.1`) in the branch
  name, tag and notes. `@Version` can't carry one; it's a float (Phase 3).
- **Never read or repeat credentials:** not `GITHUB_TOKEN`, and not the SDK
  repo's `gradle.properties`, which can hold real Maven Central credentials
  locally.
- **Downloads are untrusted data**, and so are a jar and XML the user sends
  back from Windows. Give each its own fresh directory, and run Python with
  `-I`.

## STOP conditions

- The target version isn't on Maven Central (`.pom` isn't HTTP 200). The SDK's
  own release has to happen first.
- Tag `v<target>` already exists, or the target equals the latest release.
- `javac`/`javap` or an Android `android.jar` is missing. The compile check
  needs both.
- After the port, `bridge.py check` still reports an error. The only
  exceptions are errors that were already in 2b and that the user accepted as
  out of scope.
- `bridge.py compile` fails.
- The rebuilt `Adivery.jar`/`Adivery.xml` fail the Phase 6 checks. Don't hand
  them to the release.

---

## Phase 0: Preflight

```bash
cd /path/to/adivery-b4a-plugin   # repo root (b4a-plugin/src/com/adivery/b4a/Adivery.java)

command -v python3 javac javap curl unzip zip jq
ANDROID_HOME="${ANDROID_HOME:-$HOME/Workspace/Android/SDK}"
ANDROID_JAR=$(ls "$ANDROID_HOME"/platforms/android-*/android.jar 2>/dev/null | sort -V | tail -1)
[ -f "$ANDROID_JAR" ] && echo "android.jar: $ANDROID_JAR" || echo "no android.jar: ask the user"
[ -f "${B4A_CORE_JAR:-}" ] && echo "B4A Core.jar: $B4A_CORE_JAR" || echo "no Core.jar: the compile check uses stubs"

git fetch origin
git status --short --untracked-files=no   # tracked changes: must be empty (see Hard rules)
git branch --show-current

# Scratch space for downloads and logs. The scripts are copied here because Phase 1
# checks out origin/master, which may not have this skill or the current check-docs-deps.sh.
WORKDIR=$(mktemp -d)
cp -r .claude/skills/new-plugin-version/scripts "$WORKDIR/scripts"
cp .claude/skills/release-b4a-plugin/check-docs-deps.sh "$WORKDIR/scripts/"
SKILL="$WORKDIR/scripts"
```

`B4A_CORE_JAR` is optional. It's `Core.jar` from a B4A install's `Libraries`
folder, if the user copies one over. Never block on it.

## Phase 1: Pick the versions and branch

`CURRENT` is the latest GitHub release, which is what customers download. It's
not `@Version` or the XML's `<version>`: releases that only swapped the aar
never updated those.

```bash
CURRENT_TAG=$(curl -fsS https://api.github.com/repos/adivery/adivery-b4a-plugin/releases/latest | jq -r .tag_name)
CURRENT=${CURRENT_TAG#v}

MAVEN=https://repo1.maven.org/maven2/com/adivery/sdk
LATEST=$(curl -fsS "$MAVEN/maven-metadata.xml" | grep -oP '<release>\K[^<]+')
TARGET="${TARGET:-$LATEST}"
curl -fsS -o /dev/null -w "%{http_code}\n" "$MAVEN/$TARGET/sdk-$TARGET.pom"   # must print 200
git ls-remote --tags origin "refs/tags/v$TARGET"                              # must print nothing

# The baseline for the B4A side: the zip customers have now.
mkdir "$WORKDIR/published"
curl -fsSL -o "$WORKDIR/published/adivery-b4a.zip" \
  "https://github.com/adivery/adivery-b4a-plugin/releases/download/$CURRENT_TAG/adivery-b4a.zip"
unzip -l "$WORKDIR/published/adivery-b4a.zip"   # adivery-b4a/{Adivery.aar,Adivery.jar,Adivery.xml}

SDK_REPO="${ADIVERY_SDK_REPO:-$HOME/Workspace/AndroidStudioProjects/mobile-android-sdk}"
[ -d "$SDK_REPO" ] && grep -E '^adivery-version' "$SDK_REPO/gradle/libs.versions.toml"

git branch -a --no-merged origin/master   # an unmerged branch may already port this SDK
```

- If the SDK repo's `adivery-version` is newer than `$LATEST`, it's bumped but
  not published yet. Say so, and stay on `$LATEST` unless the user wants to wait.
- Alpha and beta versions get a plugin version like any other.
  `package-and-release.sh` publishes them as normal releases, so they become
  the repo's Latest, which is what the docs' download link serves. Mention it.
- **If an unmerged branch already ports changes for `$TARGET`** (for example
  `feat/offerwall`, see Known state), ask whether to finish that branch
  instead of redoing the port. To finish it, rebase it onto `origin/master`,
  then do Phases 2–7 on it; Phase 3 then mostly reviews and fills gaps.

Report `CURRENT → TARGET`, then branch. Everything after this runs on the branch:

```bash
git checkout -b "chore/sdk-$TARGET" origin/master
```

## Phase 2: What changed

### 2a. SDK API diff, from the published AARs

```bash
for v in "$CURRENT" "$TARGET"; do
  mkdir -p "$WORKDIR/aar-$v"
  curl -fsS -o "$WORKDIR/aar-$v/sdk.aar" "$MAVEN/$v/sdk-$v.aar"
  curl -fsS -o "$WORKDIR/aar-$v/sdk.pom" "$MAVEN/$v/sdk-$v.pom"
  python3 -I "$SKILL/bridge.py" api "$WORKDIR/aar-$v/sdk.aar" . > "$WORKDIR/api-$v.txt"
done
diff "$WORKDIR/api-$CURRENT.txt" "$WORKDIR/api-$TARGET.txt"

# The published zip should bundle CURRENT's aar byte for byte. If not, say which one it has.
sha256sum "$WORKDIR/aar-$CURRENT/sdk.aar"
unzip -p "$WORKDIR/published/adivery-b4a.zip" adivery-b4a/Adivery.aar | sha256sum

# Dependencies the SDK pulls in. B4A apps add each by hand as #AdditionalJar.
for v in "$CURRENT" "$TARGET"; do
  sed -n '/<dependencies>/,/<\/dependencies>/p' "$WORKDIR/aar-$v/sdk.pom" > "$WORKDIR/deps-$v.txt"
done
diff "$WORKDIR/deps-$CURRENT.txt" "$WORKDIR/deps-$TARGET.txt" && echo "(no dependency changes)"
```

- `api` covers only the SDK classes the Java uses. For a **new ad format**
  that needs a class the wrapper doesn't use yet, look in the AAR directly:
  `unzip -p <aar> classes.jar > c.jar`, then `javap -public -cp c.jar <class>`.
- A new POM dependency means B4A apps need a new `#AdditionalJar` (and a docs
  table row), unless it isn't reached at runtime. okio comes through okhttp,
  so `check-docs-deps.sh` resolves it from okhttp's POM.
- **A POM dependency that didn't change can still become needed.** For
  example, the POM listed coroutines unused for releases, and then
  4.10.0-alpha.1 started calling it. For each runtime dependency the B4A
  table doesn't cover, count the AAR classes that reference it in both
  versions. Unzip each AAR's `classes.jar` into its own fresh directory, then
  `grep -rl --include='*.class' '<package/path>' <dir> | wc -l`. If the count
  went from 0 to more than 0, it's a new `#AdditionalJar` (sample and docs).

### 2b. The bridges and the published library, before any edit

```bash
python3 -I "$SKILL/bridge.py" check "$WORKDIR/aar-$TARGET/sdk.aar" . \
  --baseline "$WORKDIR/aar-$CURRENT/sdk.aar" --shipped "$WORKDIR/published/adivery-b4a.zip" \
  --docs README.md | tee "$WORKDIR/check-before.txt"

# Swap viability: would the PUBLISHED jar still work with the target aar (a binary-only swap)?
python3 -I "$SKILL/bridge.py" jar "$WORKDIR/published/adivery-b4a.zip" "$WORKDIR/aar-$TARGET/sdk.aar" \
  --baseline "$WORKDIR/aar-$CURRENT/sdk.aar" | tee "$WORKDIR/jar-swap.txt"

# Drift: was the published jar built from this source? (Separate run: its errors don't bear on the swap.)
python3 -I "$SKILL/bridge.py" jar "$WORKDIR/published/adivery-b4a.zip" "$WORKDIR/aar-$TARGET/sdk.aar" \
  --repo . | tee "$WORKDIR/jar-drift.txt"

# What the docs show customers, against the source. Reported, never a gate: the docs live in another repo.
python3 -I "$SKILL/bridge.py" check "$WORKDIR/aar-$TARGET/sdk.aar" . \
  --docs "$HOME/Workspace/adivery-docs/i18n/fa/docusaurus-plugin-content-docs/current/b4a.md" | grep 'b4a\.md'
```

Read the output by kind:

- **Java vs AAR errors** (an SDK method or `@Override` the new AAR lacks):
  the port has to fix them.
- **`@Events`/`raiseEvent` and sample errors:** on a branch fresh from
  `origin/master`, these are existing plugin bugs, not something the new SDK
  broke. Show them and ask whether to fix them on this branch or leave them out
  of scope. Keep `check-before.txt` for the report.
- **`published … is gone from the source`:** the source has drifted from what
  customers have (see Known state).
  - Show the user the list, with `bridge.py lib` of the published zip next to
    `bridge.py lib .`.
  - Recommend restoring those members in the source, because the docs and
    customers' code use them. `javap -c -p` on the published jar shows how
    they behave.
  - Ask for a decision before Phase 3: restore them, or accept a breaking
    change. A breaking change needs release notes and docs changes.
- **`NOT FORWARDED … [new since baseline]`:** new SDK callbacks to expose.
- **`jar-swap.txt`:**
  - errors: a binary-only swap would crash with `NoSuchMethodError`;
  - `NOT FORWARDED`: a binary-only swap would silently drop new events.
- **`jar-drift.txt`:** errors mean the published jar wasn't built from this
  source. They feed the drift decision above, not the choice of path.
- **A `--shipped` or `lib` difference made up only of ViewWrapper members**
  (`Left`, `Visible`, `SetLayoutAnimated`, …) means a newer B4A exposes more of
  them than `VIEW_WRAPPER` in `bridge.py` lists. That list comes from a
  2021-era `Core.jar`. Update it rather than "restoring" anything. If
  `B4A_CORE_JAR` is available, `javap` its `ViewWrapper` for the full list.

Then **choose the path with the user**:

- **A. Rebuild the wrapper.** This is the default whenever there are new APIs
  or callbacks to expose, or drift to fix: Phases 3–7.
- **B. Binary-only swap.** This is allowed only when `jar-swap.txt` reports 0
  errors and the user accepts that the new APIs and callbacks aren't exposed
  to B4A.
  - Skip the Java port and Phase 6.
  - Still do the dependency part of Phase 3 (sample `#AdditionalJar`, docs).
  - Then go to Phase 7 without `--jar`/`--xml`.

Where each SDK listener is forwarded:

| SDK class | Plugin file | B4A side |
|---|---|---|
| `AdiveryListener` | `Adivery.java` (the listener it registers with `com.adivery.sdk.Adivery.addListener`) | `Adivery` events: `raiseEvent(ba, "on_…", …)` → `Sub On_…` |
| `AdiveryAdListener` | `AdiveryBannerAd.java` (`setBannerAdListener`) | `AdiveryBannerAd` events: `raiseEvent(ba, "<event>")` in `AdiveryViewWrapper` → `Sub <Prefix>_<Event>` |

### 2c. Behaviour changes, from the SDK's history

A signature diff misses behaviour changes. For example, from 4.10.0-alpha.1 an
OfferWall isn't prefetched again after it closes, so the app has to prepare it
again before each show.

```bash
cd "$SDK_REPO"
FROM=$(git log --reverse --format=%H -S"adivery-version = \"$CURRENT\"" -- gradle/libs.versions.toml | head -1)
TO=$(git log --reverse --format=%H -S"adivery-version = \"$TARGET\"" -- gradle/libs.versions.toml | head -1)
git log --format='%h %s' "$FROM..$TO" -- \
  lib/src/main/java/com/adivery/sdk/Adivery.java \
  lib/src/main/java/com/adivery/sdk/AdiveryListener.java \
  lib/src/main/java/com/adivery/sdk/AdiveryListenerController.kt \
  lib/src/main/java/com/adivery/sdk/ParallelAdLoader.kt \
  lib/src/main/java/com/adivery/sdk/core
cd -
```

`-S` finds the commit that *introduced* each version line (`-G` would also
match the bump that removes it). If the SDK repo isn't present or the range is
empty, ask the user for the changelog instead of guessing. Read the relevant
commits (`git show <sha>`). For intended usage, read the SDK sample
(`app/src/main/java/com/adivery/sample/`) and the docs' Android page.

Summarise for the user, **before editing anything**:
- API additions, removals and signature changes;
- new callbacks to forward;
- behaviour changes that affect callers;
- dependency changes;
- the published-API drift and the decision taken on it;
- path A or B.

## Phase 3: Port

On `chore/sdk-$TARGET`:

1. **Java** (`b4a-plugin/src/com/adivery/b4a/`), following each file's
   existing pattern:
   - **A new SDK static** (e.g. `Adivery.prepareXAd(ctx, id)`) becomes a
     `public static <Ret> PascalCaseName(BA ba, …)` in `Adivery.java`.
     - Call the SDK fully qualified, `com.adivery.sdk.Adivery.x(…)`, since the
       wrapper class is also named `Adivery`.
     - Pass `ba.activity` for a `Context`/`Activity`, and
       `ba.activity.getApplication()` for an `Application`.
     - B4A has no overloading: names must be unique, ignoring case.
   - **A new `AdiveryListener` callback** needs three things:
     - an `@Override` in the registered listener that calls
       `raiseEvent(ba, "on_<snake_case>", args…)`;
     - an `@Events` entry `"On_<Snake_Case> (placement As String, …)"`;
     - the raised name equal to the entry's name lowercased, with one value
       per declared parameter. Types: `String`→`String`, `boolean`→`Boolean`,
       `int`→`Int`, `long`→`Long`, `float`→`Float`, `double`→`Double`.
   - **A banner (`AdiveryAdListener`) callback** becomes a
     `raiseEvent(ba, "<event>", …)` in `AdiveryBannerAd` plus an `@Events`
     entry. Customers handle it as `Sub <Prefix>_<Event>`.
   - **Removed or renamed SDK API:** keep the B4A member's name and signature,
     and map it to the new SDK call (Hard rules).
   - **Drift (2b):** apply what the user decided. If the members are being
     restored, match the published signatures exactly (`bridge.py lib` of the
     published zip).
   - **`@Version`** is B4A's library version, and it's a Java `float`.
     **Ask the user** what to set it to:
     - So far it has been the SDK's major.minor (`4.8f`, `4.9f`).
     - B4A shows it with two decimals.
     - `4.10f` is the float 4.1, which is lower than 4.9.
     - A pre-release suffix can't be expressed.
2. **Sample** (`sample/ui_example.b4a`):
   - A `Sub` for each new event, logging its arguments
     (`Log("Offer Wall Ad Loaded: " & placement)`), next to its siblings.
   - A `Sub ButtonX_Click` for each new format or user-facing API, next to the
     existing ones. Its button is added to `main.bal` in the Designer in
     Phase 6. Until then the Sub is inert; leave a comment saying so, like the
     existing OfferWall one.
   - App and placement IDs come from the SDK's own sample:
     `app/src/main/res/values/strings.xml` (`adivery_app_id`,
     `adivery_<format>_pl_id`) at the `$TARGET` commit. Placements belong to
     an app ID, so keep the whole set together. The sample's legacy
     `com.adivery.MainActivity` holds older IDs, but the manifest doesn't
     declare it, so don't use them. Ask the user if a format has no ID there.
   - Reflect behaviour changes in how the sample uses the API. For example,
     OfferWall prepares on tap and shows from `On_Offer_Wall_Ad_Loaded`.
   - If the POM dependencies changed, update the `#AdditionalJar` lines in
     **both** the Project Attributes and Activity Attributes regions.
3. **Docs** (`$HOME/Workspace/adivery-docs`):
   - Which copies: `i18n/fa/docusaurus-plugin-content-docs/current/b4a.md` is
     the maintained copy (dependency table, OfferWall section).
     `i18n/en/…/b4a.md` and `docs/b4a.md` lag behind it.
   - Check the docs repo's branch first: an unmerged branch (e.g. `offerwall`)
     may already document the feature.
   - Propose edits for new APIs, events and behaviour notes, and for the
     dependency table and `#AdditionalJar` lines.
   - Show the diff to the user. Never commit or push there without asking.
4. **README** (`README.md`):
   - add new formats, methods and events to its API tables;
   - update its `#AdditionalJar` block when the POM dependencies change;
   - note any API that needs SDK X or later, and any behaviour change
     integrators must handle (as the OfferWall notes do).

   It's in this repo, so its code blocks are checked with the wrapper, and
   their errors gate like the sample's.

Re-run until the only errors left are pre-existing ones the user chose to
leave out of scope (2b):

```bash
python3 -I "$SKILL/bridge.py" check "$WORKDIR/aar-$TARGET/sdk.aar" . \
  --baseline "$WORKDIR/aar-$CURRENT/sdk.aar" --shipped "$WORKDIR/published/adivery-b4a.zip" \
  --docs README.md
```

Run the 2b docs check again against the proposed docs edits. Report its errors,
but they don't gate this loop: the docs repo has its own review.

- **`NOT FORWARDED` lines:** forward each one, or list it in the report as
  skipped on purpose, with the reason.
- **`NEW` lines** are the B4A API this version adds. They go in the release
  notes.
- **Warnings** are not runtime failures, but mention any new ones:
  - a declared event that's never raised;
  - a sample with no Sub for an event;
  - a Sub that looks like an event but matches none, such as
    `FlexBanner_AdLoadFailed`, whose prefix nothing `Initialize`s.
- **Reference count:** see Known state for the expected numbers.

## Phase 4: Verify on Linux

```bash
python3 -I "$SKILL/bridge.py" compile "$WORKDIR/aar-$TARGET/sdk.aar" . \
  --android-jar "$ANDROID_JAR" ${B4A_CORE_JAR:+--core-jar "$B4A_CORE_JAR"}

bash "$SKILL/check-docs-deps.sh" --pom "$WORKDIR/aar-$TARGET/sdk.pom" --sample sample/ui_example.b4a --sample README.md
```

- **`compile`** type-checks the Java against the target SDK with javac,
  including every `@Override`. With stubs, the summary line says the B4A side
  wasn't really compiled. Report it that way.
- **If `compile` reports a missing B4A member**, add it to
  `scripts/b4a-stubs/` with the real signature. Never loosen a stub to make
  code compile.
- **`check-docs-deps.sh`** exits 1 on a version mismatch in the docs table, the
  sample or the README. It also lists POM dependencies the table doesn't cover.

## Phase 5: Commit and push

Two commits on `chore/sdk-$TARGET` (or on the feature branch Phase 1 chose to
finish), staged by explicit path:

1. `build: sync B4A wrapper with Adivery SDK <TARGET>`: `b4a-plugin/src`.
2. The sample (`sample/ui_example.b4a`) and `README.md`, with a message
   describing what changed for integrators.

Follow the session's commit-attribution rules. Then **ask** before pushing the
branch. The Windows machine pulls it from there, and opening the PR can wait
until `main.bal` is updated in Phase 6.

## Phase 6: Windows rebuild and device run (the user's step)

Path A only. LibraryCompiler, the B4A Designer and the B4A IDE run only on
Windows, so hand the user this checklist and wait for them:

1. Check out `chore/sdk-<TARGET>` on the Windows machine.
2. Put the target SDK's classes on LibraryCompiler's classpath. With B4A's
   Simple Library Compiler, that means extracting `classes.jar` from
   `sdk-<TARGET>.aar` into the project's `libs` folder (`b4a-plugin/libs/`;
   `*.jar` is gitignored). Ask how they built it last time; the 2021 jar was
   built against a `classes.jar` on a desktop.
3. Run `build.bat` (`LibraryCompiler Adivery <repo>\b4a-plugin`). It writes
   `Adivery.jar` and `Adivery.xml` to B4A's Additional Libraries folder.
4. Copy `sdk-<TARGET>.aar` there as `Adivery.aar`, plus any jar the POM diff
   added.
5. Open `sample/ui_example.b4a`. In the Designer, add a button to `main.bal`
   for each new `ButtonX_Click` Sub, with the same name. Commit
   `sample/Files/main.bal` on the branch.
6. Run the sample on a device and tap through each format. Check B4A's Logs
   tab for the sample's `Log` lines: loaded, shown, clicked, closed, rewarded,
   and `On_Error`.
7. Send back the `Adivery.jar` and `Adivery.xml` from step 3.

Then verify the rebuilt pair. Put the files in a fresh directory first:

```bash
NEW="$WORKDIR/rebuilt"          # holds the Adivery.jar and Adivery.xml the user sent
python3 -I "$SKILL/bridge.py" jar "$NEW/Adivery.jar" "$WORKDIR/aar-$TARGET/sdk.aar" \
  --repo . --baseline "$WORKDIR/aar-$CURRENT/sdk.aar"                              # 0 errors
diff <(python3 -I "$SKILL/bridge.py" lib "$NEW/Adivery.xml") <(python3 -I "$SKILL/bridge.py" lib .)   # no output
grep -o '<version>[^<]*</version>' "$NEW/Adivery.xml"                                # the @Version agreed in Phase 3
unzip -l "$NEW/Adivery.jar" | grep '\.class$' | grep -v ' com/adivery/b4a/'           # no output
```

- **If `jar --repo` fails**, the jar wasn't built from this branch's source.
- **If the `lib` diff isn't empty**, the XML wasn't generated from this
  source, unless it's only ViewWrapper members (2b).
- **If the last command prints anything**, the jar has bundled classes from
  outside the wrapper, most likely the SDK `classes.jar` from `libs/`. They'd
  clash with `Adivery.aar` as duplicate classes in customers' builds. Non-class
  junk, like the 2021 jar's `.project`, is harmless.
- In any of these cases, don't release. Find out why first.

Once `main.bal` is committed, **ask** before opening the PR against `master`.

## Phase 7: Hand off to the release

After the PR is merged, run **`release-b4a-plugin`** from an up-to-date
`master`. The release creates the tag at the default branch's HEAD, so
releasing before the merge would tag a commit without the changes. That skill
confirms before publishing.

`$WORKDIR` may not have survived the Windows round trip. If it hasn't, get the
published zip and the target AAR again with the Phase 1 and 2a commands. The
rebuilt `Adivery.jar`/`Adivery.xml` come from the user again. Re-verify them
as in Phase 6 before using them. Give it these inputs:

```bash
# Path A needs a package-and-release.sh that takes --jar/--xml. Master gained them with this skill.
grep -q -- '--jar)' .claude/skills/release-b4a-plugin/package-and-release.sh || echo "STOP: master's release script can't swap the wrapper"

bash .claude/skills/release-b4a-plugin/package-and-release.sh --version "$TARGET" \
  --aar "$WORKDIR/aar-$TARGET/sdk.aar" --zip "$WORKDIR/published/adivery-b4a.zip" \
  --jar "$NEW/Adivery.jar" --xml "$NEW/Adivery.xml" \
  --notes "<integrator-facing summary>" --build-only
```

- On path B, leave out `--jar`/`--xml`.
- `--build-only` is the dry run. That skill runs it again without
  `--build-only` after the user confirms.
- For `--notes`, write an integrator-facing summary rather than the default
  body ("Update plugin based on Adivery X version"):
  - the `NEW` B4A members;
  - behaviour changes;
  - new `#AdditionalJar` jars;
  - any approved breaking change.

---

## Final report

Summarize:
- `CURRENT → TARGET`, and whether it's a pre-release;
- the API diff and how each change was ported: new B4A methods, newly raised
  events with their B4A names and parameters, and callbacks skipped on
  purpose, with the reason;
- the published-API drift found in 2b, and what was decided;
- behaviour changes, and how the sample and docs reflect them;
- POM dependency changes, and the `check-docs-deps.sh` result;
- verification:
  - `bridge.py check`: references checked, and errors before (2b) vs after
    the port, with any pre-existing ones left out of scope;
  - `bridge.py compile`, saying whether it used stubs or `Core.jar`;
  - the `jar` check of the published jar against the target AAR;
  - after Phase 6: the rebuilt pair's `jar --repo` and `lib` diff, and the
    device run (or that they're still pending);
- path A or B;
- the branch, its commits, and what's left: the Windows rebuild, the PR, the
  docs repo edits, `release-b4a-plugin`;
- `$WORKDIR`, which is safe to delete once the release is out. Phase 7 reads
  its AAR, published zip and rebuilt files.

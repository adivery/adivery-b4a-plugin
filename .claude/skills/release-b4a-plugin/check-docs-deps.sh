#!/usr/bin/env bash
#
# check-docs-deps.sh
#
# Diff the external-dependency version table in the B4A docs (b4a.md)
# against the versions actually pinned by the Adivery Android SDK.
#
# Why this exists: the B4A plugin bundles a raw local Adivery.aar with
# no Maven/Gradle dependency resolution behind it, so b4a.md documents
# the exact kotlin-stdlib/okhttp/okio-jvm/sentry jars a B4A developer
# must add by hand (#AdditionalJar). Whenever the SDK bumps one of
# these in gradle/libs.versions.toml, the docs silently go stale.
#
# kotlin/okhttp/sentry are read straight from the SDK's own version
# catalog, or with --pom from the SDK's published POM (what customers
# actually get; the catalog can be ahead of the last release). okio is
# NOT in either -- it's a transitive dependency of okhttp -- so it's
# resolved from okhttp's published POM on Maven Central instead (the
# same source used when this doc section was first written).
#
# --sample (repeatable) also diffs the #AdditionalJar lines of files that
# pin the same jars: the sample project (sample/ui_example.b4a) and the
# repo's README.md.
#
# This is a read-only check: it never edits either repo. Exit code is
# 1 on drift (or on a missing docs row) so callers can treat it as a
# gate if they want to; the release flow itself treats it as a
# heads-up, not a hard block.
#
# Requires: bash, curl, grep, sed, awk.

set -euo pipefail

SDK_REPO="${HOME}/Workspace/AndroidStudioProjects/mobile-android-sdk"
DOCS_FILE="${HOME}/Workspace/adivery-docs/i18n/fa/docusaurus-plugin-content-docs/current/b4a.md"
POM=""
SAMPLES=()

usage() {
  cat <<'USAGE'
Usage: check-docs-deps.sh [options]

Options:
  --sdk-repo PATH    Path to the mobile-android-sdk checkout.
                     Default: ~/Workspace/AndroidStudioProjects/mobile-android-sdk
  --docs-file PATH   Path to the B4A docs page (b4a.md).
                     Default: ~/Workspace/adivery-docs/i18n/fa/docusaurus-plugin-content-docs/current/b4a.md
  --pom PATH         The SDK's published POM (sdk-X.Y.Z.pom from Maven Central).
                     When given, versions come from it and --sdk-repo is not used.
  --sample PATH      Also check the #AdditionalJar lines in this file
                     (e.g. sample/ui_example.b4a, README.md). Repeatable.
  -h, --help         Show this help.

Note: without --pom, this reads gradle/libs.versions.toml from whatever
commit the SDK repo is CURRENTLY checked out to. Make sure that matches
the tag/commit that produced the sdk-*.aar you're packaging in this
release -- or pass --pom, which can't drift.
USAGE
}

while [ $# -gt 0 ]; do
  case "$1" in
    --sdk-repo)  SDK_REPO="${2:-}"; shift 2 ;;
    --docs-file) DOCS_FILE="${2:-}"; shift 2 ;;
    --pom)       POM="${2:-}"; shift 2 ;;
    --sample)    SAMPLES+=("${2:-}"); shift 2 ;;
    -h|--help)   usage; exit 0 ;;
    *)           echo "unknown argument: $1 (try --help)" >&2; exit 1 ;;
  esac
done

err() { printf 'error: %s\n' "$*" >&2; exit 1; }

CATALOG="${SDK_REPO}/gradle/libs.versions.toml"
if [ -n "$POM" ]; then
  [ -f "$POM" ] || err "POM not found: $POM"
else
  [ -f "$CATALOG" ] || err "version catalog not found: $CATALOG (pass --sdk-repo or --pom)"
fi
[ -f "$DOCS_FILE" ] || err "docs file not found: $DOCS_FILE (pass --docs-file)"
for f in ${SAMPLES[@]+"${SAMPLES[@]}"}; do [ -f "$f" ] || err "file not found: $f"; done

for bin in curl grep sed awk; do
  command -v "$bin" >/dev/null 2>&1 || err "required tool not found: $bin"
done

# ---------------------------------------------------- versions the SDK pins --
# NOTE: this catalog reuses bare keys like "okhttp"/"sentry" as BOTH a
# [versions] entry ('okhttp = "4.12.0"') AND a [libraries] alias
# ('okhttp = { module = "...", version.ref = "okhttp" }'). The anchored
# '= "..."$' pattern below matches only the plain [versions] form.
version_entry() {
  grep -E "^${1}[[:space:]]*=[[:space:]]*\"[^\"]+\"[[:space:]]*\$" "$CATALOG" \
    | head -1 | sed -E 's/.*"([^"]+)".*/\1/'
}

# One "groupId:artifactId:version" line per <dependency> in a POM.
pom_deps() {
  tr -d '\r\n' < "$1" | sed -E 's#</dependency>#\n#g' \
    | sed -nE 's#.*<dependency>.*<groupId>([^<]+)</groupId>.*<artifactId>([^<]+)</artifactId>.*<version>([^<]+)</version>.*#\1:\2:\3#p'
}
pom_version() { pom_deps "$POM" | grep -E "^${1}:" | head -1 | cut -d: -f3; }

# The libraries the B4A table covers (okio is reached through okhttp, and
# kotlinx-coroutines-core-jvm through kotlinx-coroutines-android).
TRACKED='^(org\.jetbrains\.kotlin:kotlin-stdlib|com\.squareup\.okhttp3:okhttp|io\.sentry:sentry|org\.jetbrains\.kotlinx:kotlinx-coroutines-android):'

if [ -n "$POM" ]; then
  SOURCE="$POM"
  sdk_kotlin="$(pom_version 'org\.jetbrains\.kotlin:kotlin-stdlib')"
  sdk_okhttp="$(pom_version 'com\.squareup\.okhttp3:okhttp')"
  sdk_sentry="$(pom_version 'io\.sentry:sentry')"
  sdk_coroutines="$(pom_version 'org\.jetbrains\.kotlinx:kotlinx-coroutines-android')"
else
  SOURCE="$CATALOG"
  sdk_kotlin="$(version_entry kotlin)"
  sdk_okhttp="$(version_entry okhttp)"
  sdk_sentry="$(version_entry sentry)"
  sdk_coroutines="$(version_entry kotlinx-coroutines-android)"
fi

[ -n "$sdk_kotlin" ] || err "could not find kotlin-stdlib's version in $SOURCE"
[ -n "$sdk_okhttp" ] || err "could not find okhttp's version in $SOURCE"
[ -n "$sdk_sentry" ] || err "could not find sentry's version in $SOURCE"

# okio is transitive (via okhttp), not in our own catalog -- resolve it
# from okhttp's published POM, same version okhttp itself was built against.
pom_url="https://repo1.maven.org/maven2/com/squareup/okhttp3/okhttp/${sdk_okhttp}/okhttp-${sdk_okhttp}.pom"
sdk_okio="$(curl -s --max-time 30 "$pom_url" \
  | grep -A3 '<artifactId>okio</artifactId>' \
  | grep -oE '<version>[^<]+</version>' \
  | head -1 \
  | sed -E 's#<version>([^<]+)</version>#\1#')"
[ -n "$sdk_okio" ] || err "could not resolve okio's version from $pom_url (network issue, or okhttp changed its dependency layout -- check manually)"

# The SDK runs on kotlinx-coroutines since 4.10.0-alpha.1 (Dispatchers.Main, so
# the -android jar too) without bundling it. Its core is transitive, so it's
# resolved from kotlinx-coroutines-android's published POM, like okio.
LIBS="kotlin-stdlib okhttp okio-jvm sentry"
if [ -n "$sdk_coroutines" ]; then
  pom_url="https://repo1.maven.org/maven2/org/jetbrains/kotlinx/kotlinx-coroutines-android/${sdk_coroutines}/kotlinx-coroutines-android-${sdk_coroutines}.pom"
  sdk_coroutines_core="$(curl -s --max-time 30 "$pom_url" \
    | grep -A2 '<artifactId>kotlinx-coroutines-core-jvm</artifactId>' \
    | grep -oE '<version>[^<]+</version>' \
    | head -1 \
    | sed -E 's#<version>([^<]+)</version>#\1#')"
  [ -n "$sdk_coroutines_core" ] || err "could not resolve kotlinx-coroutines-core-jvm's version from $pom_url -- check manually"
  LIBS="$LIBS kotlinx-coroutines-core-jvm kotlinx-coroutines-android"
fi
sdk_version() {
  case "$1" in
    kotlin-stdlib) echo "$sdk_kotlin" ;;
    okhttp) echo "$sdk_okhttp" ;;
    okio-jvm) echo "$sdk_okio" ;;
    sentry) echo "$sdk_sentry" ;;
    kotlinx-coroutines-core-jvm) echo "$sdk_coroutines_core" ;;
    kotlinx-coroutines-android) echo "$sdk_coroutines" ;;
  esac
}

# --------------------------------------------- versions currently in the docs -
doc_version() {
  local name="$1"
  grep -E "^\| ${name} \|" "$DOCS_FILE" | head -1 | awk -F'|' '{gsub(/ /,"",$3); print $3}'
}

# --------------------------------------------------------------------- report -
mismatch=0
report() {
  local label="$1" sdk="$2" doc="$3"
  if [ -z "$doc" ]; then
    printf '  %-27s sdk=%-10s docs=<no row found>  -- add a row for this library\n' "$label" "$sdk"
    mismatch=1
  elif [ "$sdk" != "$doc" ]; then
    printf '  %-27s sdk=%-10s docs=%-10s  -- MISMATCH\n' "$label" "$sdk" "$doc"
    mismatch=1
  else
    printf '  %-27s sdk=%-10s docs=%-10s  -- ok\n' "$label" "$sdk" "$doc"
  fi
}

echo "==> SDK versions: $SOURCE"
echo "==> docs file   : $DOCS_FILE"
echo "==> comparing:"
for name in $LIBS; do
  report "$name" "$(sdk_version "$name")" "$(doc_version "$name")"
done

# ------------------------------------------------- files' #AdditionalJar -----
stale_samples=""
for SAMPLE in ${SAMPLES[@]+"${SAMPLES[@]}"}; do
  echo "==> sample      : $SAMPLE"
  file_stale=0
  for name in $LIBS; do
    want="$(sdk_version "$name")"
    # The sample project repeats each line in its Project and Activity attribute regions.
    have="$(grep -oE "#AdditionalJar:[[:space:]]*${name}-[0-9][^[:space:]]*" "$SAMPLE" \
      | sed -E "s/.*${name}-//" | sort -u | tr '\n' ' ' | sed 's/ $//')"
    if [ -z "$have" ]; then
      printf '  %-27s sdk=%-10s sample=<no #AdditionalJar line>  -- MISMATCH\n' "$name" "$want"; file_stale=1
    elif [ "$have" != "$want" ]; then
      printf '  %-27s sdk=%-10s sample=%-10s  -- MISMATCH\n' "$name" "$want" "$have"; file_stale=1
    else
      printf '  %-27s sdk=%-10s sample=%-10s  -- ok\n' "$name" "$want" "$have"
    fi
  done
  [ "$file_stale" -eq 0 ] || stale_samples="${stale_samples} ${SAMPLE}"
done

# --------------------------------- POM dependencies the B4A table doesn't list -
# Not a mismatch: some may not be needed at runtime by the B4A wrapper's code
# paths. But a dependency that's NEW in this SDK version needs a decision.
if [ -n "$POM" ]; then
  untracked="$(pom_deps "$POM" | grep -vE "$TRACKED" || true)"
  if [ -n "$untracked" ]; then
    echo "==> POM dependencies the B4A table doesn't cover (decide whether B4A apps need them as #AdditionalJar):"
    printf '  %s\n' $untracked
  fi
fi

if [ "$mismatch" -eq 1 ]; then
  echo "==> docs are OUT OF DATE -- update the dependency table and #AdditionalJar lines in $DOCS_FILE"
fi
if [ -n "$stale_samples" ]; then
  echo "==> OUT OF DATE #AdditionalJar lines (in the sample project, update both blocks) in:${stale_samples}"
fi
if [ "$mismatch" -eq 1 ] || [ -n "$stale_samples" ]; then
  exit 1
fi
echo "==> up to date, nothing to change"
exit 0

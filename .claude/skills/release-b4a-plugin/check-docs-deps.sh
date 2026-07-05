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
# catalog. okio is NOT in that catalog -- it's a transitive dependency
# of okhttp -- so it's resolved from okhttp's published POM on Maven
# Central instead (the same source used when this doc section was
# first written).
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

usage() {
  cat <<'USAGE'
Usage: check-docs-deps.sh [options]

Options:
  --sdk-repo PATH    Path to the mobile-android-sdk checkout.
                     Default: ~/Workspace/AndroidStudioProjects/mobile-android-sdk
  --docs-file PATH   Path to the B4A docs page (b4a.md).
                     Default: ~/Workspace/adivery-docs/i18n/fa/docusaurus-plugin-content-docs/current/b4a.md
  -h, --help         Show this help.

Note: this reads gradle/libs.versions.toml from whatever commit the SDK
repo is CURRENTLY checked out to. Make sure that matches the tag/commit
that produced the sdk-*.aar you're packaging in this release.
USAGE
}

while [ $# -gt 0 ]; do
  case "$1" in
    --sdk-repo)  SDK_REPO="${2:-}"; shift 2 ;;
    --docs-file) DOCS_FILE="${2:-}"; shift 2 ;;
    -h|--help)   usage; exit 0 ;;
    *)           echo "unknown argument: $1 (try --help)" >&2; exit 1 ;;
  esac
done

err() { printf 'error: %s\n' "$*" >&2; exit 1; }

CATALOG="${SDK_REPO}/gradle/libs.versions.toml"
[ -f "$CATALOG" ] || err "version catalog not found: $CATALOG (pass --sdk-repo)"
[ -f "$DOCS_FILE" ] || err "docs file not found: $DOCS_FILE (pass --docs-file)"

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

sdk_kotlin="$(version_entry kotlin)"
sdk_okhttp="$(version_entry okhttp)"
sdk_sentry="$(version_entry sentry)"

[ -n "$sdk_kotlin" ] || err "could not find a top-level 'kotlin = \"...\"' entry in $CATALOG"
[ -n "$sdk_okhttp" ] || err "could not find a top-level 'okhttp = \"...\"' entry in $CATALOG"
[ -n "$sdk_sentry" ] || err "could not find a top-level 'sentry = \"...\"' entry in $CATALOG"

# okio is transitive (via okhttp), not in our own catalog -- resolve it
# from okhttp's published POM, same version okhttp itself was built against.
pom_url="https://repo1.maven.org/maven2/com/squareup/okhttp3/okhttp/${sdk_okhttp}/okhttp-${sdk_okhttp}.pom"
sdk_okio="$(curl -s --max-time 30 "$pom_url" \
  | grep -A3 '<artifactId>okio</artifactId>' \
  | grep -oE '<version>[^<]+</version>' \
  | head -1 \
  | sed -E 's#<version>([^<]+)</version>#\1#')"
[ -n "$sdk_okio" ] || err "could not resolve okio's version from $pom_url (network issue, or okhttp changed its dependency layout -- check manually)"

# --------------------------------------------- versions currently in the docs -
doc_version() {
  local name="$1"
  grep -E "^\| ${name} \|" "$DOCS_FILE" | head -1 | awk -F'|' '{gsub(/ /,"",$3); print $3}'
}

doc_kotlin="$(doc_version 'kotlin-stdlib')"
doc_okhttp="$(doc_version 'okhttp')"
doc_okio="$(doc_version 'okio-jvm')"
doc_sentry="$(doc_version 'sentry')"

# --------------------------------------------------------------------- report -
mismatch=0
report() {
  local label="$1" sdk="$2" doc="$3"
  if [ -z "$doc" ]; then
    printf '  %-14s sdk=%-10s docs=<no row found>  -- add a row for this library\n' "$label" "$sdk"
    mismatch=1
  elif [ "$sdk" != "$doc" ]; then
    printf '  %-14s sdk=%-10s docs=%-10s  -- MISMATCH\n' "$label" "$sdk" "$doc"
    mismatch=1
  else
    printf '  %-14s sdk=%-10s docs=%-10s  -- ok\n' "$label" "$sdk" "$doc"
  fi
}

echo "==> SDK catalog : $CATALOG"
echo "==> docs file   : $DOCS_FILE"
echo "==> comparing:"
report "kotlin-stdlib" "$sdk_kotlin" "$doc_kotlin"
report "okhttp"        "$sdk_okhttp" "$doc_okhttp"
report "okio-jvm"      "$sdk_okio"   "$doc_okio"
report "sentry"        "$sdk_sentry" "$doc_sentry"

if [ "$mismatch" -eq 1 ]; then
  echo "==> docs are OUT OF DATE -- update the dependency table and #AdditionalJar lines in $DOCS_FILE"
  exit 1
else
  echo "==> docs are up to date, nothing to change"
  exit 0
fi

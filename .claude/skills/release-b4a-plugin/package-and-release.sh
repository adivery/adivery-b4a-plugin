#!/usr/bin/env bash
#
# package-and-release.sh
#
# Repackage the Adivery B4A plugin zip with a newer Adivery SDK .aar and
# (optionally) publish it as a GitHub release.
#
# The plugin zip has this internal layout:
#   adivery-b4a/Adivery.aar   <- the bundled SDK binary (this is what we swap)
#   adivery-b4a/Adivery.jar   <- the compiled B4A wrapper (untouched)
#   adivery-b4a/Adivery.xml   <- the B4A library descriptor (untouched)
#
# The release flow is failure-safe: create as draft -> upload asset ->
# publish. Any partial failure leaves a private draft to delete/retry,
# never a broken public release.
#
# Requires: bash, unzip, zip, curl, jq.  Auth via $GITHUB_TOKEN.

set -euo pipefail

# ---------------------------------------------------------------- defaults ----
REPO="adivery/adivery-b4a-plugin"
SEARCH_DIR="${HOME}/Downloads"
ASSET_NAME="adivery-b4a.zip"   # release asset name (unversioned, per convention)
INNER_DIR="adivery-b4a"        # top-level folder inside the zip
INNER_AAR="Adivery.aar"        # the aar entry to replace, inside INNER_DIR/
AAR=""
ZIP=""
VERSION=""
OUT=""
NOTES=""
BUILD_ONLY=0

usage() {
  cat <<'USAGE'
Usage: package-and-release.sh --version X.Y.Z [options]

Options:
  --version X.Y.Z   Release version (a leading "v" is accepted/normalized).
  --aar PATH        New Adivery SDK aar. Default: newest sdk-*.aar in --search-dir.
  --zip PATH        Base plugin zip to repackage. Default: <search-dir>/adivery-b4a.zip.
  --search-dir DIR  Where to auto-detect aar/zip. Default: ~/Downloads.
  --out PATH        Output zip path. Default: <scratch>/adivery-b4a.zip next to script.
  --notes TEXT      Release body. Default: "Update plugin based on Adivery X.Y.Z version".
  --repo OWNER/NAME Target repo. Default: adivery/adivery-b4a-plugin.
  --build-only      Repackage only; skip the GitHub release.
  -h, --help        Show this help.

Environment:
  GITHUB_TOKEN      Required for releasing (not for --build-only).
USAGE
}

err() { printf 'error: %s\n' "$*" >&2; exit 1; }

# ---------------------------------------------------------------- parse args --
while [ $# -gt 0 ]; do
  case "$1" in
    --version)    VERSION="${2:-}"; shift 2 ;;
    --aar)        AAR="${2:-}"; shift 2 ;;
    --zip)        ZIP="${2:-}"; shift 2 ;;
    --search-dir) SEARCH_DIR="${2:-}"; shift 2 ;;
    --out)        OUT="${2:-}"; shift 2 ;;
    --notes)      NOTES="${2:-}"; shift 2 ;;
    --repo)       REPO="${2:-}"; shift 2 ;;
    --build-only) BUILD_ONLY=1; shift ;;
    -h|--help)    usage; exit 0 ;;
    *)            err "unknown argument: $1 (try --help)" ;;
  esac
done

for bin in unzip zip curl jq; do
  command -v "$bin" >/dev/null 2>&1 || err "required tool not found: $bin"
done

# ---------------------------------------------------------------- normalize ---
[ -n "$VERSION" ] || err "--version is required"
VERSION="${VERSION#[vV]}"
echo "$VERSION" | grep -Eq '^[0-9]+\.[0-9]+\.[0-9]+([.-][0-9A-Za-z.]+)?$' \
  || err "version '$VERSION' does not look like X.Y.Z"
TAG="v${VERSION}"
NAME="Release v${VERSION}"
[ -n "$NOTES" ] || NOTES="Update plugin based on Adivery ${VERSION} version"

# ---------------------------------------------------------------- locate aar --
if [ -z "$AAR" ]; then
  [ -d "$SEARCH_DIR" ] || err "search dir not found: $SEARCH_DIR (pass --aar)"
  # Strictly match sdk-X.Y.Z.aar; ignore dependency aars (e.g. lifecycle-*).
  latest="$(find "$SEARCH_DIR" -maxdepth 1 -type f -name 'sdk-*.aar' -printf '%f\n' 2>/dev/null \
    | grep -E '^sdk-[0-9]+\.[0-9]+\.[0-9]+\.aar$' \
    | sed -E 's/^sdk-(.*)\.aar$/\1/' \
    | sort -V | tail -1)"
  [ -n "$latest" ] || err "no sdk-*.aar found in $SEARCH_DIR (pass --aar explicitly)"
  AAR="${SEARCH_DIR}/sdk-${latest}.aar"
fi
[ -f "$AAR" ] || err "aar not found: $AAR"
unzip -tqq "$AAR" >/dev/null 2>&1 || err "aar is not a valid archive: $AAR"

# ---------------------------------------------------------------- locate zip --
if [ -z "$ZIP" ]; then
  ZIP="${SEARCH_DIR}/adivery-b4a.zip"
fi
[ -f "$ZIP" ] || err "plugin zip not found: $ZIP (pass --zip)"

# ---------------------------------------------------------------- output path -
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -z "$OUT" ]; then
  OUT="${SCRIPT_DIR}/build/${ASSET_NAME}"
fi
mkdir -p "$(dirname "$OUT")"

echo "==> aar     : $AAR"
echo "==> base zip: $ZIP"
echo "==> output  : $OUT"
echo "==> version : $VERSION (tag $TAG)"

# ---------------------------------------------------------------- repackage ---
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

unzip -q "$ZIP" -d "$WORK"
target="${WORK}/${INNER_DIR}/${INNER_AAR}"
[ -f "$target" ] || err "expected '$INNER_DIR/$INNER_AAR' inside $ZIP but it was not found"

old_size="$(wc -c < "$target")"
cp -f "$AAR" "$target"
new_size="$(wc -c < "$target")"
echo "==> swapped ${INNER_DIR}/${INNER_AAR}: ${old_size} bytes -> ${new_size} bytes"

rm -f "$OUT"
( cd "$WORK" && zip -q -r -X "$OUT" "$INNER_DIR" )
echo "==> repackaged: $OUT ($(wc -c < "$OUT") bytes)"

if [ "$BUILD_ONLY" -eq 1 ]; then
  echo "==> build-only: skipping GitHub release."
  echo "OUTPUT_ZIP=$OUT"
  exit 0
fi

# ---------------------------------------------------------------- release -----
[ -n "${GITHUB_TOKEN:-}" ] || err "GITHUB_TOKEN is not set; export it or rerun with --build-only"

API="https://api.github.com/repos/${REPO}"
UPLOADS="https://uploads.github.com/repos/${REPO}"
AUTH=(-H "Authorization: Bearer ${GITHUB_TOKEN}" -H "Accept: application/vnd.github+json")

# Pre-check: refuse to clobber an existing tag/release.
code="$(curl -s -o "${WORK}/precheck.json" -w '%{http_code}' "${AUTH[@]}" "${API}/releases/tags/${TAG}")"
if [ "$code" = "200" ]; then
  err "a release for tag ${TAG} already exists: $(jq -r '.html_url' "${WORK}/precheck.json")"
elif [ "$code" = "401" ] || [ "$code" = "403" ]; then
  err "GitHub auth failed (HTTP ${code}); check GITHUB_TOKEN scopes (needs 'repo'/'contents:write')"
elif [ "$code" != "404" ]; then
  err "unexpected HTTP ${code} while checking for existing tag ${TAG}: $(cat "${WORK}/precheck.json")"
fi

# 1) Create as DRAFT.
body_json="$(jq -n --arg t "$TAG" --arg n "$NAME" --arg b "$NOTES" \
  '{tag_name:$t, name:$n, body:$b, draft:true, prerelease:false}')"
code="$(curl -s -o "${WORK}/create.json" -w '%{http_code}' -X POST "${AUTH[@]}" \
  -H 'Content-Type: application/json' -d "$body_json" "${API}/releases")"
[ "$code" = "201" ] || err "failed to create draft release (HTTP ${code}): $(cat "${WORK}/create.json")"
release_id="$(jq -r '.id' "${WORK}/create.json")"
echo "==> created draft release id=${release_id}"

# 2) Upload the asset. On failure leave the draft for retry/inspection.
code="$(curl -s -o "${WORK}/upload.json" -w '%{http_code}' -X POST "${AUTH[@]}" \
  -H 'Content-Type: application/zip' --data-binary @"$OUT" \
  "${UPLOADS}/releases/${release_id}/assets?name=${ASSET_NAME}")"
if [ "$code" != "201" ]; then
  echo "draft release ${release_id} kept for inspection: ${API}/releases/${release_id}" >&2
  err "asset upload failed (HTTP ${code}): $(cat "${WORK}/upload.json")"
fi
echo "==> uploaded asset: $(jq -r '.name' "${WORK}/upload.json") ($(jq -r '.state' "${WORK}/upload.json"))"

# 3) Publish (flip draft -> false).
code="$(curl -s -o "${WORK}/publish.json" -w '%{http_code}' -X PATCH "${AUTH[@]}" \
  -H 'Content-Type: application/json' -d '{"draft":false}' \
  "${API}/releases/${release_id}")"
[ "$code" = "200" ] || err "failed to publish release ${release_id} (HTTP ${code}): $(cat "${WORK}/publish.json")"

html_url="$(jq -r '.html_url' "${WORK}/publish.json")"
echo "==> published: ${html_url}"
echo "RELEASE_URL=${html_url}"

#!/usr/bin/env bash
# Shared release helper for every platform's CI workflow.
#
#   release.sh check
#       Writes kind=release or kind=snapshot to $GITHUB_OUTPUT (and stdout), plus
#       version=<VERSION>. It is a release when the tag v<VERSION> doesn't exist
#       yet, or already points at this commit (another platform's workflow
#       created it for the same push). Otherwise it is a snapshot build of a
#       version that has already been released.
#
#   release.sh publish FILE...
#       For a release, creates the GitHub release v<VERSION> on this commit if
#       it doesn't exist (marked pre-release for -alpha/-beta/-rc versions, with
#       notes from that version's CHANGELOG.md section) and uploads FILE... to it.
#       For a snapshot it does nothing, so released builds are never replaced.
#
# Needs GH_TOKEN, GITHUB_SHA and GITHUB_REPOSITORY (all set in GitHub Actions).
set -euo pipefail

root="$(cd "$(dirname "$0")/../.." && pwd)"
version="$(tr -d '[:space:]' < "$root/VERSION")"
tag="v$version"

# Prints the commit the tag points at, or nothing if the tag doesn't exist.
tag_commit() {
  local sha
  sha="$(gh api "repos/$GITHUB_REPOSITORY/commits/$tag" --jq .sha 2>/dev/null || true)"
  if [[ "$sha" =~ ^[0-9a-f]{40}$ ]]; then echo "$sha"; fi
}

kind() {
  local sha
  sha="$(tag_commit)"
  if [ -z "$sha" ] || [ "$sha" = "$GITHUB_SHA" ]; then echo release; else echo snapshot; fi
}

notes() {
  local section
  section="$(awk -v head="## [$version]" '
    index($0, head) == 1 { found = 1; next }
    found && /^## / { exit }
    found { print }
  ' "$root/CHANGELOG.md")"
  if [ -n "$(echo "$section" | tr -d '[:space:]')" ]; then
    echo "$section"
  else
    echo "Bing Wallpaper $version."
  fi
}

case "${1:-}" in
  check)
    k="$(kind)"
    echo "version=$version"
    echo "kind=$k"
    if [ -n "${GITHUB_OUTPUT:-}" ]; then
      { echo "version=$version"; echo "kind=$k"; } >> "$GITHUB_OUTPUT"
    fi
    ;;
  publish)
    shift
    [ "$#" -gt 0 ] || { echo "usage: release.sh publish FILE..." >&2; exit 2; }
    if [ "$(kind)" != release ]; then
      echo "$tag was already released from another commit; not touching it."
      exit 0
    fi
    if ! gh release view "$tag" >/dev/null 2>&1; then
      prerelease=()
      case "$version" in *-*) prerelease=(--prerelease) ;; esac
      # Another platform's workflow may create it at the same moment; that's fine.
      gh release create "$tag" --target "$GITHUB_SHA" --title "Bing Wallpaper $version" \
        --notes "$(notes)" "${prerelease[@]}" \
        || gh release view "$tag" >/dev/null
    fi
    if [ "$(tag_commit)" != "$GITHUB_SHA" ]; then
      echo "$tag points at another commit; not uploading." >&2
      exit 1
    fi
    gh release upload "$tag" "$@" --clobber
    ;;
  *)
    echo "usage: release.sh check | publish FILE..." >&2
    exit 2
    ;;
esac

#!/usr/bin/env bash
# Build FLIMPA release artifacts (macOS .app + .dmg, or Windows folder for .exe packaging).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
VERSION="${1:-2.0.0}"
VENV_PY="${ROOT}/.venv/bin/python"

if [[ ! -x "$VENV_PY" ]]; then
  echo "Missing .venv — run: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt"
  exit 1
fi

echo "==> PyInstaller build"
"$VENV_PY" -m PyInstaller --clean --noconfirm FLIMPA.spec

RELEASE_DIR="${ROOT}/release"
mkdir -p "$RELEASE_DIR"

if [[ "$(uname -s)" == "Darwin" ]]; then
  APP="${ROOT}/dist/FLIMPA.app"
  DMG="${RELEASE_DIR}/FLIMPA.v${VERSION}.dmg"
  if [[ ! -d "$APP" ]]; then
    echo "Expected ${APP} — build failed?"
    exit 1
  fi

  # iCloud paths add Finder metadata that breaks codesign ("app is damaged").
  # Copy to /tmp, strip xattrs, ad-hoc sign, then pack the .dmg.
  STAGE=$(mktemp -d /tmp/flimpa_release_stage.XXXXXX)
  cleanup() { rm -rf "$STAGE"; }
  trap cleanup EXIT

  echo "==> Staging and signing .app"
  ditto --norsrc "$APP" "$STAGE/FLIMPA.app"
  xattr -cr "$STAGE/FLIMPA.app"
  dot_clean -m "$STAGE/FLIMPA.app" 2>/dev/null || true
  find "$STAGE/FLIMPA.app" -name '._*' -delete 2>/dev/null || true
  codesign --force --deep -s - --timestamp=none "$STAGE/FLIMPA.app"
  codesign --verify --deep --strict "$STAGE/FLIMPA.app"
  ln -s /Applications "$STAGE/Applications"

  echo "==> Creating DMG: ${DMG}"
  rm -f "$DMG"
  hdiutil create -volname "FLIMPA ${VERSION}" -srcfolder "$STAGE" -ov -format UDZO "$DMG"
  echo "Done: $DMG"
  ls -lh "$DMG"
  echo ""
  echo "To install: open the .dmg, drag FLIMPA.app to Applications, then open FLIMPA from Applications."
else
  echo "==> Windows/Linux: built folder at dist/FLIMPA/"
  echo "Zip dist/FLIMPA as FLIMPA.v${VERSION}.zip or use Inno Setup for an installer."
fi

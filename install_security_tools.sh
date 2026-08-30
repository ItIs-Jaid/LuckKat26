#!/usr/bin/env bash
# Install Security Tools reference toolset — Black Arch or Kali.
#
# Pulls native package names (those marked ✅ in security-tools-reference.md) for the
# chosen distro, dedupes, and installs. Tools not yet packaged in the distro (marked
# pip/git) are skipped — install those separately as noted in the reference doc.
#
# Usage:
#   ./install_security_tools.sh blackarch          # dry-run: print the pacman command
#   ./install_security_tools.sh blackarch --apply  # actually install
#   ./install_security_tools.sh kali               # dry-run: print the apt command
#   ./install_security_tools.sh kali --apply
#   ./install_security_tools.sh kali --cat cloud --apply   # only the cloud category
#
# Defaults to dry-run so nothing installs by accident. Requires root/sudo to apply.
set -euo pipefail

DISTRO="blackarch"
APPLY=0
CAT=""
REF="$(cd "$(dirname "$0")" && pwd)/security-tools-reference.md"

# Parse args: <distro> [--apply] [--cat <category>]
while [ $# -gt 0 ]; do
  case "$1" in
    blackarch|kali) DISTRO="$1" ;;
    --apply) APPLY=1 ;;
    --cat) CAT="${2:-}"; shift ;;
    *) echo "unknown arg: $1" >&2; exit 1 ;;
  esac
  shift
done

if [ ! -f "$REF" ]; then
  echo "reference doc not found: $REF" >&2; exit 1
fi

if [ "$DISTRO" = "blackarch" ]; then
  PKG_COL=3   # blackarch_pkg is column 3 in the tables
  INSTALLER="sudo pacman -S --needed"
elif [ "$DISTRO" = "kali" ]; then
  PKG_COL=2   # kali_pkg is column 2
  INSTALLER="sudo apt-get install -y"
else
  echo "unknown distro: $DISTRO (use blackarch|kali)" >&2; exit 1
fi

# Extract native (✅) package names from the chosen column.
# A data row looks like: | Name | kali | blackarch | niche | url |
# Track the current `## N.` section so --cat filters by category.
# Category mapping mirrors kb/seed_security_tools.py CATEGORY_BY_SECTION.
pkgs=$(awk -F'|' -v col="$PKG_COL" -v cat="$CAT" '
  /^## [0-9]+\./ {
    n = $0; sub(/^## /, "", n); sub(/\..*/, "", n)
    if (n == 1) curcat = "red_team"
    else if (n == 2) curcat = "recon"
    else if (n == 3) curcat = "cloud"
    else if (n == 4) curcat = "osint"
    next
  }
  /^[|]/ && $0 ~ /https?:\/\// {
    if (cat != "" && curcat != cat) next
    name = $2
    gsub(/^[ \t]+|[ \t]+$/, "", name)
    if (name == "" || name == "Tool") next
    cell = (col == 2) ? $3 : $4
    if (cell ~ /⚠️/) next           # skip external (pip/git) tools
    gsub(/[`✅⚠️* \t]/, "", cell)
    if (cell == "") next
    print cell
  }
' "$REF" | sort -u)

if [ -z "$pkgs" ]; then
  echo "no native $DISTRO packages found (check reference doc)."
  exit 0
fi

echo "# ${DISTRO} — ${CAT:-all categories} — $(echo "$pkgs" | wc -l) native packages"
if [ "$APPLY" -eq 1 ]; then
  echo "# applying..."
  # shellcheck disable=SC2086
  $INSTALLER $pkgs
else
  echo "# dry-run (add --apply to install):"
  echo "$INSTALLER $pkgs" | fold -s -w 100
fi

#!/usr/bin/env bash
# Installs only Dotprofile. Never applies profiles or rewrites desktop settings.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
mode="${1:-interactive}"
case "$mode" in
  interactive|--upgrade|--check) ;;
  *) echo 'Usage: ./install.sh [--upgrade | --check]' >&2; exit 2 ;;
esac
if (( $# > 1 )); then echo 'Unexpected installer arguments.' >&2; exit 2; fi
if (( EUID == 0 )); then echo 'Run as your normal user, not root.' >&2; exit 1; fi
install_home="${DOTPROFILE_INSTALL_HOME:-$HOME}"
root="$install_home/.local/share/dotprofile"
bin="$install_home/.local/bin"
missing=()
command -v python3 >/dev/null 2>&1 || missing+=(python)
command -v gum >/dev/null 2>&1 || missing+=(gum)
if command -v python3 >/dev/null 2>&1 && ! python3 -c 'import tomlkit' >/dev/null 2>&1; then
  missing+=(python-tomlkit)
fi
if [[ "$mode" == --check ]]; then
  if ((${#missing[@]})); then printf 'Missing dependency: %s\n' "${missing[@]}" >&2; exit 1; fi
  python3 engine/profilectl.py --version
  if [[ -f "$root/engine/profilectl.py" ]]; then
    if installed_version="$(python3 "$root/engine/profilectl.py" --version 2>/dev/null)"; then
      printf 'Installed: %s\n' "$installed_version"
    else
      echo 'Installed manager predates --version; v0.6.2-beta upgrade available.'
    fi
  fi
  echo 'Dependencies available; check made no changes.'
  exit 0
fi
if ((${#missing[@]})); then
  if [[ "$mode" == --upgrade ]]; then
    printf 'Missing dependency: %s\n' "${missing[@]}" >&2
    echo 'Install missing dependencies with: sudo pacman -S --needed python python-tomlkit gum' >&2
    exit 1
  fi
  command -v pacman >/dev/null 2>&1 || { echo 'Install Python 3.11+, tomlkit, and Gum first.' >&2; exit 1; }
  printf 'Required dependency: %s\n' "${missing[@]}"
  read -r -p 'Install these dependencies via Pacman? [y/N] ' answer
  [[ "$answer" =~ ^[yY]$ ]] || exit 0
  sudo pacman -S --needed "${missing[@]}"
fi
selected='Desktop Profile Manager (TUI + engine)'
if [[ "$mode" == interactive ]]; then
  selected="$(printf '%s\n' 'Desktop Profile Manager (TUI + engine)' 'Install local appearance profiles (choose separately)' |
    gum choose --no-limit --height 8 --header 'Select appearance-profile components')" || exit 0
  [[ -n "$selected" ]] || exit 0
  echo 'WARNING: applying profiles later can restyle indicators and rename workspaces 1–5.'
  gum confirm 'Install selected components? Installation preserves desktop settings and existing profiles.' || exit 0
fi
want() { grep -Fqx "$1" <<< "$selected"; }
if want 'Desktop Profile Manager (TUI + engine)'; then
  for path in "$root" "$root/engine" "$bin" "$root/engine/profilectl.py" "$bin/dotprofile" "$root/upgrade-backups"; do
    [[ ! -L "$path" ]] || { echo "Symlinked installation path refused: $path" >&2; exit 1; }
  done
  python3 engine/profilectl.py --version
  bash -n tui/dotprofile
  mkdir -p "$root/engine" "$bin" "$root/upgrade-backups"
  snapshot="$(mktemp -d "$root/upgrade-backups/v0.6.2-beta-$(date +%Y%m%d-%H%M%S)-XXXXXX")"
  for file in engine tui; do
    if [[ "$file" == engine ]]; then target="$root/engine/profilectl.py"; else target="$bin/dotprofile"; fi
    if [[ -e "$target" ]]; then cp -p "$target" "$snapshot/$file"; else touch "$snapshot/$file.absent"; fi
  done
  engine_stage="$(mktemp "$root/engine/.upgrade-XXXXXX")"
  tui_stage="$(mktemp "$bin/.dotprofile-upgrade-XXXXXX")"
  changed=false
  cleanup() {
    result=$?
    if (( result != 0 )) && [[ "$changed" == true ]]; then
      if [[ -f "$snapshot/engine" ]]; then cp -p "$snapshot/engine" "$root/engine/profilectl.py"; else rm -f "$root/engine/profilectl.py"; fi
      if [[ -f "$snapshot/tui" ]]; then cp -p "$snapshot/tui" "$bin/dotprofile"; else rm -f "$bin/dotprofile"; fi
      echo 'Upgrade failed; previous manager restored.' >&2
    fi
    rm -f "$engine_stage" "$tui_stage"
    return "$result"
  }
  trap cleanup EXIT
  install -m 755 engine/profilectl.py "$engine_stage"
  install -m 755 tui/dotprofile "$tui_stage"
  python3 "$engine_stage" --version
  changed=true
  mv -f "$engine_stage" "$root/engine/profilectl.py"
  mv -f "$tui_stage" "$bin/dotprofile"
  python3 "$root/engine/profilectl.py" --version
  NDP_DEFAULT_ROOT="$root/defaults" NDP_STATE_ROOT="$install_home/.local/state/dotprofile" python3 engine/profilectl.py install-defaults defaults
  changed=false
  echo "Installed Dotprofile v0.6.2-beta. Manager backup: $snapshot"
fi
if want 'Install local appearance profiles (choose separately)'; then
  mapfile -t dirs < <(find profiles -mindepth 2 -maxdepth 2 -name profile.toml -printf '%h\n' | sort)
  if ((${#dirs[@]})); then
    chosen="$(printf '%s\n' "${dirs[@]}" | gum choose --no-limit --height 12 --header 'Choose profiles to copy; none will apply')" || chosen=''
    while IFS= read -r dir; do
      if [[ -n "$dir" ]]; then NDP_PROFILE_ROOT="$root/profiles" NDP_STATE_ROOT="$install_home/.local/state/dotprofile" python3 engine/profilectl.py install-profile "$dir"; fi
    done <<< "$chosen"
  fi
fi
printf '\nFinished. Existing profiles and running desktop settings were preserved.\n'

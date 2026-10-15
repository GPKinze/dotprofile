# Dotprofile v0.6.3-beta — Noctalia + Umbriel appearance profiles

A TUI appearance profile manager for CachyOS / Arch. Save approved desktop appearance fields as portable TOML, then merge them into an existing desktop. Requires Python 3.11+, `tomlkit`, and Gum; importing requires Noctalia and Umbriel with their configuration validators.

> **Warning: importing a profile can restyle workspace indicators and rename workspaces 1–5.** Synthetic examples use **一 二 三 四 五** and decorative **【 】**. Names apply only to existing outputs with five distinct static workspace names and `min_workspaces <= 5`. Dynamic or incompatible outputs are skipped with a warning. Keybindings, workspace counts, monitor settings, and workspace behavior are preserved.

This **v0.6.3-beta development update** includes the native capsule radius fix and the wallpaper-free RDR Personal example. Schema checks use Noctalia **5.2.1** and Umbriel **0.1.0**; runtime IPC is simulated in automated tests. Review dry-run warnings before applying profiles. No wallpapers, preview images, or private configurations are distributed. RDR is an explicitly sanitized Personal appearance package.

Run the following commands from the repository root, not from `docs/`. For first-time installation and prerequisites, see the [project README](../README.md#installation-v063-beta).

## Upgrade (Fish compatible)

```fish
cd dotprofile  # or the extracted source directory
./install.sh --check
python3 -m unittest discover -s tests -v
bash -n install.sh tui/dotprofile
./install.sh --upgrade
fish_add_path ~/.local/bin
dotprofile --version
```

`--upgrade` updates only the engine and TUI, backs up both previous manager files under `~/.local/share/dotprofile/upgrade-backups/`, stages their replacements, and restores them if an upgrade fails. It preserves Personal profiles, desktop configs, and application configs, and installs curated immutable Default packages separately. It does not install packages or apply a profile. Missing dependencies are reported with installation instructions.

For an initial interactive installation, run `./install.sh`. It can offer **only missing** Python, tomlkit, and Gum dependencies through Pacman, then lets you choose the manager and optional local profiles independently. Copying a profile never applies it. Existing Personal IDs cannot be overwritten without explicit confirmation and a package backup.

Installed paths:

```text
~/.local/bin/dotprofile
~/.local/share/dotprofile/engine/profilectl.py
~/.local/share/dotprofile/defaults/       # official Default originals
~/.local/share/dotprofile/profiles/       # existing and new Personal profiles
~/.local/state/dotprofile/backups/
```

## Verify the real export without touching existing profiles

These commands work in Fish. They save `review-copy` into a new temporary profile library, bundle the current wallpaper, validate the exported Noctalia TOML, and show a dry run. They do not apply it or replace the existing `review-copy` profile.

```fish
set -l check_root (mktemp -d)
set -l engine ~/.local/share/dotprofile/engine/profilectl.py
env NDP_PROFILE_ROOT="$check_root" python3 "$engine" save review-copy --include-wallpaper
noctalia config validate "$check_root/review-copy/noctalia.toml"
rg '^\[(bar|widget)\.' "$check_root/review-copy/noctalia.toml"
cat "$check_root/review-copy/workspace.toml"
env NDP_PROFILE_ROOT="$check_root" python3 "$engine" apply review-copy --dry-run
```

Keep `check_root` for inspection; it is printed in the save result. `save` refuses existing Personal IDs unless `--overwrite --confirm` is explicitly provided; Default originals always remain immutable. To keep a corrected export in your usual library while preserving your old profile, choose a new ID such as `my-appearance-copy`. Include wallpaper images only when you have permission to redistribute them.

## What is portable

| Included | Protected / excluded |
| --- | --- |
| Case-sensitive named bars discovered from `bar.order`, with unlisted legacy bars appended | `bar.order`, output/monitor overrides, dead-zone actions |
| Approved bar geometry, opacity, fonts, borders, and capsules | Plugin-owned tables, plugin widget definitions, plugin placements |
| Approved native widget appearance, resolved through named aliases | Commands, scripts, action bindings, custom executable widgets, device selectors |
| Workspace indicator styling and bracket-only text, including repeated references | Arbitrary private text or unsupported text decorations |
| Native capsule groups as `[[bar.NAME.capsule_group]]` with `group:ID` lane tokens | Capsules containing any plugin or unknown member; their entire membership and token are excluded |
| Five static names in `workspace.toml` | Keybindings, other workspace behavior, inventory/count changes |
| Wallpaper or solid color, fill and transitions; shell fonts/animations/shadows/panel appearance | Wallpaper directories, automation, per-monitor paths, services |
| Lockscreen wallpaper, transitions, tint, and blur | Authentication, passwords, fingerprint, grace periods, enablement |
| Umbriel gaps, borders, blur, shadows, approved colors and animations | Hardware, outputs, input, rules, autostart, effect files/shaders |

All fields use explicit allowlists. Unsupported fields are omitted on export and rejected in imported profiles. The engine does not install plugins, services, applications, themes, app templates, or personal dotfiles. No profile-provided hooks are executed.

Noctalia's merged export supplies user overrides, including wallpaper paths. Its `full` export supplies current defaults, including animations; v0.6 combines them before filtering. Older versions without `full` export retain the merged-export path. Lowercase `main`/`default` fixtures and v0.4 profiles remain supported.

## Plugin and layout protection

A widget ID is resolved through `[widget.ID].type`, falling back to the native ID. An ID such as `clock` or `launcher` that resolves to an unknown or plugin type is protected. This covers arbitrary plugins, including public plugin types such as `icefish/phone-operate:status`, `icefish/phone-connect:bar`, and `noctalia/screen_recorder:recorder` aliases.

Exports omit all plugin settings and plugin placements. A capsule containing a plugin or unknown member is omitted entirely, even when it also contains native widgets.

On import, switching, and restoration, protected widgets retain their **bar, lane, relative order, reference count, and capsule membership**. Built-in widget placements may be added, removed, duplicated, or moved between lanes and native capsules. Decorative bracket instances can be created from approved definitions. Existing resolved types cannot be retargeted. Plugin indices are retained when enough native placements remain; removing native neighbors can change numeric indices, while plugin lane/order stays fixed.

For a safely accepted complete native group snapshot, omitting the optional `radius` removes a previous explicit native radius so Noctalia chooses automatic rounding. The snapshot must contain `id`, `members`, `enabled`, `fill`, `border`, `border_width`, `opacity`, `padding`, `accordion`, and `accordion_direction`, and be part of a validated three-lane layout. Sparse legacy groups retain omitted fields. No other omitted appearance fields are reset, and protected groups remain untouched.

A complete native layout supplies all three lanes. Its lanes and dependent capsule changes are planned together, checked for protected-placement preservation, then committed together. Native `group:g1` may safely change membership between the synthetic A and B layouts. A group ID that belongs to a plugin/mixed/unknown capsule or an unresolved existing token cannot be claimed by a profile. Native members shared with any protected capsule are frozen too, including their widget settings. Unknown group fields, inactive group rows, and removed native instance definitions remain stored so unrelated settings survive.

Profiles support **top, bottom, left, and right** bar positions, dimensions, margins, and approved visual styling. Noctalia derives horizontal/vertical orientation from `position`; `thickness` controls the cross-axis size and `margin_ends`/`padding` follow the main axis. Moving a containing bar naturally moves its plugins on screen without independently rearranging them. Native clock `format`, `vertical_format`, and `tooltip_format` support line breaks; the exception applies only to these display fields. See the [Noctalia bar schema](https://docs.noctalia.dev/noctalia/bar/).

Incomplete or conflicting layouts are skipped for the affected bar with a specific warning; safe bar position/style changes can still apply. Case-sensitive bar names match exactly; a single source bar may map to a single differently named target bar. Multi-bar mismatches are skipped, never guessed. Existing `bar.order` is preserved. Older profiles with no layout data keep the current layout; missing layout data cannot be reconstructed. Capture the desired desktop with **Save As** under a new Personal name; upgrades never rewrite existing profiles.

Per-monitor layouts are skipped conservatively. An import cannot create a GUI override list that relocates protected layout data from lower configuration layers, or relocate a lower-layer capsule array. Such layout/group changes are skipped. Recipient monitor geometry overrides remain unchanged, with a warning when they prevent requested profile fields from taking effect. Profiles also cannot disable or enable a bar containing protected widgets.

## Templates, app themes, and hooks stay recipient-owned

**Appearance packages never include `[theme.templates]`, built-in/community selections, custom template declarations, template paths/actions, application-theme configs, or user-defined hooks.** Exports use explicit field allowlists and strip source comments so private template details cannot leak through comments. Imports reject template/hook settings and extra sidecar files/directories, even when propagation is allowed. Dotprofile never installs, configures, enables, disables, overwrites, or deletes those settings or application themes. Configure them independently through Noctalia.

Noctalia can render enabled app templates when palette colors change, and can execute existing hooks on color, mode, or wallpaper events. Dotprofile reads the recipient's effective configuration—including lower config layers—without changing it. **The default is to skip differing theme/wallpaper fields with an informative warning when active templates or relevant hooks are detected.** Unknown template configuration and nonempty unknown hook events also cause a conservative skip. Disabled catalogues/user templates and empty hook entries are preserved and do not by themselves require an opt-in.

To allow Noctalia's normal propagation, explicitly opt in for **one operation**. First review the recipient's templates and hooks, then compare the dry run:

```fish
python3 engine/profilectl.py apply personal:MY_PROFILE --dry-run
python3 engine/profilectl.py apply personal:MY_PROFILE --dry-run --allow-noctalia-propagation
```

Only after accepting the consequences, omit `--dry-run` to apply that selected plan. `restore` supports the same flag and requires a fresh opt-in; consent is never stored in a profile, manifest, backup, or global preference. The TUI shows the safe preview and offers a **default-off** informed confirmation before re-previewing an opted-in plan. Declining keeps the safe plan.

**Opt-in permits Noctalia to rewrite external app configs and execute the recipient's existing hook commands. Those external effects are outside Dotprofile's backups and cannot be rolled back by it.** The opt-in does not allow a profile to edit template/hook configuration, install application themes, change plugins, or bypass any other field/layout protection. Dotprofile itself never runs template/hook commands. The recipient's template/hook settings, flags, custom paths, and command strings remain exactly as configured.

Wallpaper and palette selection remain supported when propagation is safe or explicitly accepted. Other approved appearance changes still apply when theme/wallpaper fields are skipped. Accepted explicit wallpaper images/colors are applied live through Noctalia IPC as described below. Details and primary Noctalia references are in [the safety policy](SAFETY.md).

## Live wallpaper switching

After profile/native validation, a recovery backup, staged configuration writes, post-write validation, and configuration reload, Dotprofile sends `noctalia msg wallpaper-set <resolved-path>`. Noctalia's supported all-monitor form applies the bundled image (or supported solid color) to **every connected monitor** and persists its default/current monitor wallpaper paths. No connector names are hardcoded or imported from the profile. Noctalia retains control of wallpaper surfaces, transitions, fill behavior, per-monitor options, directories, and automation; Dotprofile does not disable them to force an image. Normal automation may subsequently select another wallpaper. See [Noctalia wallpaper IPC](https://docs.noctalia.dev/noctalia/ipc/media-and-ui/).

Reapplying the same profile still sends wallpaper IPC, even if `wallpaper.default.path` already matches: live monitor choices can be stale. Existing template/hook guards apply again, including this same-default case. With active or unrecognized propagation sources, wallpaper changes and wallpaper IPC are skipped unless **this operation** explicitly uses `--allow-noctalia-propagation`. No profile stores consent. Profiles without an explicit nonempty wallpaper path send no wallpaper IPC; an empty path produces a warning because the IPC has no supported empty target. Dry runs show the planned IPC but make no runtime calls, reloads, backups, or desktop writes.

A missing bundled asset is rejected before writes. IPC launch failures, nonzero replies, timeouts, or failed post-IPC validation fail the operation and attempt configuration recovery. Noctalia normally persists `wallpaper.default.path`, `wallpaper.last.path`, and connected `wallpaper.monitors.*.path` during this IPC. Dotprofile recognizes only those expected path changes, retains the observed bytes for rollback, and checks every other configuration value for unexpected/concurrent changes. It never treats arbitrary IPC-time edits as its own writes. Unexpected plugin/template/hardware edits are retained, with an explicit rollback warning and recovery snapshot. Noctalia may normalize serialization of its own managed TOML; configuration values outside the permitted paths must remain identical.

**Configuration rollback does not guarantee that displayed monitor images are restored after partial IPC or a timeout. External template/hook effects cannot be rolled back.** Error output states these limits and identifies the recovery snapshot. Appearance restoration uses the same validation/backup/IPC flow and requires fresh propagation consent; it applies the snapshot's approved common wallpaper, not historical per-monitor configurations. The active-profile marker commits only after successful reload, wallpaper IPC, and final validation.

## Immutable Defaults and Personal profiles

Official **Default** profiles and user-created **Personal** profiles have separate storage:

```text
~/.local/share/dotprofile/defaults/PROFILE_ID/   # release-owned, immutable through Dotprofile
~/.local/share/dotprofile/profiles/PROFILE_ID/   # Personal; existing v0.4/v0.5 data stays here
~/.local/state/dotprofile/profile-backups/      # recovery copies before Personal edits
```

The shipped default is `example-minimal`. Existing user-created profiles remain Personal. Default status is determined by a release-owned catalogue of names/file hashes and the separate Default namespace; arbitrary imported metadata cannot grant it. Official files are installed read-only and checked against the catalogue before use. Externally edited/mismatched defaults are refused. Future reviewed releases update the catalogue with their official packages.

You may **apply or export** a Default, customize your running desktop freely, and save those changes using **Save As with a new Personal name**. The stored Default is never overwritten, renamed, deleted, or modified through the engine or TUI. Return to its original appearance at any time using **Switch Profile → Default: example-minimal**, subject to the same plugin/layout/template safety checks.

Personal profiles may be renamed, deleted, or overwritten only with confirmation and a full package backup. The TUI displays **Default** and **Personal** labels, blocks Default management, and asks before Personal changes. CLI protection is independent of the TUI:

```fish
python3 engine/profilectl.py list --labels
python3 engine/profilectl.py apply default:example-minimal --dry-run
python3 engine/profilectl.py save my-custom-appearance
python3 engine/profilectl.py export default:example-minimal ~/Exports
python3 engine/profilectl.py save personal:MY_PROFILE --overwrite --confirm
python3 engine/profilectl.py rename personal:MY_PROFILE personal:NEW_NAME --confirm
python3 engine/profilectl.py delete personal:MY_PROFILE --confirm
python3 engine/profilectl.py profile-backups
```

Personal edits do not change your running desktop. `--confirm` explicitly acknowledges the specified library operation; a package backup is saved first. Backups keep an ID-named folder that can be recovered using `install-profile PATH_TO_BACKUP/PROFILE_ID`. Without `--overwrite --confirm`, imports and saves refuse an existing Personal ID. Defaults always reject those mutation flags.

`default:NAME` and `personal:NAME` unambiguously identify sources. They can coexist with the same ID. For compatibility, an unqualified ID selects a Personal profile first, otherwise a known installed Default. Updating official defaults **never overwrites a Personal profile with the same name**. Importing a default export through `install-profile` creates a Personal copy; it does not grant official status.

The manager upgrade installs only the curated files from the release's `defaults/` directory through hash validation. `install-defaults DIRECTORY` accepts only exact catalogue packages, not self-declared official metadata or unknown packages. It never applies a profile or migrates, renames, replaces, or deletes existing Personal profiles.

## Profiles and use

```text
profiles/PROFILE_ID/
  profile.toml       # id, display name, optional description
  noctalia.toml      # approved shell appearance, bars, widgets, capsule groups
  umbriel.toml       # approved compositor appearance and animations
  workspace.toml    # optional: [workspace_indicator] labels = ["一","二","三","四","五"]
  wallpaper.png      # optional bundled asset; supported image suffixes also accepted
  lockscreen.png     # optional bundled asset
```

The official `defaults/example-minimal` is an appearance-only Default without workspace names. The legacy source example under `profiles/example-minimal` is available for explicit Personal import; official status comes only from the separate Default namespace and release catalogue. The `profiles/rdr` folder is an installable, wallpaper-free Personal example. Gruvbox Kanji remains documentation-only. `review-copy` below is a temporary profile ID, not a shipped folder.

Launch `dotprofile` to save, install a local profile, review/apply a profile, inspect the active profile, or restore a backup. Equivalent engine commands:

```fish
python3 engine/profilectl.py --version
python3 engine/profilectl.py list
python3 engine/profilectl.py save my-appearance-copy --include-wallpaper
python3 engine/profilectl.py install-profile ./defaults/example-minimal
python3 engine/profilectl.py apply example-minimal --dry-run
python3 engine/profilectl.py backups
python3 engine/profilectl.py restore BACKUP_ID --dry-run
```

Applying or restoring is a separate explicit action. Review and approve it in the TUI. `restore` merges approved appearance from a snapshot into the **current** desktop. It never restores historical plugin settings, installation state, placements, capsule membership, keybindings, or unrelated fields. Plugins installed, removed, moved, or edited since a backup remain as they are now. Unsafe layout restoration is skipped with a warning. v0.6 snapshots include permitted effective Noctalia defaults; for older snapshots, absent appearance overrides are retained and reported.

## Install the wallpaper-free RDR Personal example

From the repository root, with the manager installed:

```fish
python3 engine/profilectl.py install-profile ./profiles/rdr
python3 engine/profilectl.py apply personal:rdr --dry-run
```

Import copies the package into the Personal library and **does not apply it**. Use **Switch Profile → Personal: rdr** to preview and confirm separately. An existing Personal `rdr` is refused by default; retain it unless you deliberately choose confirmed replacement with a backup. No replacement is part of an upgrade.

RDR's center `group:g1` contains exactly `launcher` and `workspaces`. Its complete native group omits `radius` to use Noctalia's automatic pill rounding, including after a boxy native layout. RDR is not in the immutable Default catalogue. It supplies Roman labels **Ⅰ Ⅱ Ⅲ Ⅳ Ⅴ** for compatible five-workspace outputs; keybindings and workspace behavior remain protected.

The published package has no wallpaper section, lockscreen wallpaper override, asset reference, or image. Importing/applying it makes no wallpaper IPC request and leaves wallpaper paths/options untouched. Its `theme.source = "wallpaper"` uses the recipient's current wallpaper for colors, so appearance can differ from the author's desktop. Existing templates/hooks can react to palette selection; the ordinary default-safe propagation guard still applies. It uses `Geist Mono` if installed; font availability and schema differences can affect the result. See [RDR documentation](../profiles/rdr/README.md) for the wallpaper source link and redistribution status.

## Import safeguards and limits

- Profile manifests and TOML are validated before writes. Symlinked profile sources/config files, executable settings, plugin definitions or sidecar files, output changes, and unapproved sections are refused. Profile directories accept only the defined TOML files, approved bundled images, README.md, and preview.png; arbitrary extra files/directories are rejected.
- Noctalia effective export must succeed before importing its appearance; otherwise aliases cannot be resolved safely and import is refused.
- Both installed native validators check offline candidates before any live writes. Umbriel includes are resolved relative to the original config in the validation copy. Dry runs report target files and every skipped operation, without touching live configs or creating recovery state.
- Engine operations are serialized. If a live file changes during preparation, import aborts instead of overwriting that edit. This is not a lock on Noctalia's GUI; avoid simultaneous edits during application.
- Snapshots include both configs and the previous active-profile marker. Writes use temporary files, fsync, and atomic replacement per file. Post-write validation or explicit reload failures roll back our writes and attempt to reload the previous configuration. If a file changed externally beyond the recognized wallpaper IPC persistence, rollback leaves that file intact and raises a clear recovery warning instead of overwriting a new plugin edit. There is no single atomic transaction spanning both live files, and a running desktop may observe a brief intermediate state. Abrupt process termination or failed recovery writes require manual recovery from the retained snapshot.
- TOML comments and unapproved fields are preserved wherever tomlkit can keep them. Equal widget lists are not rewritten. Missing bars are not created. Missing approved native instances/groups may be created only as part of an accepted complete layout; unresolved recipient-owned instances remain protected.
- Only explicit workspace labels in the main Umbriel output tables are captured; included output declarations are not relocated. Multiple eligible outputs with conflicting names omit label export rather than selecting arbitrary names.
- Custom animation effects/shaders and arbitrary text are deliberately outside the portable schema. Validation warnings for pre-existing unavailable plugins may remain, while their configuration is preserved.

## Developer checks

```fish
python3 -m unittest discover -s tests -v
bash -n install.sh tui/dotprofile
python3 tests/verify_rdr_package.py
# Optional: installed Noctalia/Umbriel validators, synthetic temporary configs only
python3 tests/native_layout_roundtrip.py
```

Tests cover universal plugin preservation during import/export/switching/restoration, the synthetic case-sensitive `Main` bar, capsule AoT, duplicate decorations, plugin aliases and collisions, protected group membership, workspace names, old formats, field validation, backups, rollback, concurrent edits, and isolated installer upgrades. The synthetic layout A → B → A → B and backup-restoration regression and all twelve position transitions (including bottom → left → bottom) check native layouts, groups, geometry, and plugin invariants. Native integration validation is described in [the archive review](RELEASE-REVIEW.md); the exclusion, propagation, and immutable-default policies are documented in [the safety policy](SAFETY.md). Wallpaper regressions use simulated IPC only, including an isolated command-line test with real installed validators; see [the archive review](RELEASE-REVIEW.md). Tests never apply profiles or send wallpaper/reload IPC to a running desktop. Test hardware names, paths, plugin settings, and images are synthetic.

MIT licensed.

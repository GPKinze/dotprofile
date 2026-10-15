# Dotprofile v0.6.2-beta safety policy

## Ownership boundaries

A desktop appearance profile owns only explicitly allowed palette/wallpaper, shell/bar/native-widget/capsule appearance, compositor appearance, and five compatible workspace labels. It never owns plugin configuration/installation/placement, theme templates, app-theme configuration, user hooks, keybindings, authentication, services, hardware, monitor settings, applications, or unrelated dotfiles.

Every public profile source—including official defaults—passes the same field/file checks. Profile manifests accept only ID/name/description. They cannot grant official status or encode propagation consent. Profile packages reject unknown sidecars, executable hooks, template directories, app configs, and plugin data. Saved TOML is serialized without private source comments.

## Templates and hooks

`[theme.templates]` and all child tables/selections/flags/custom paths/pre/post hooks/actions are omitted from exports and rejected in imported profiles. `[hooks]` and application-theme settings are likewise excluded. Applying, switching, restoring, saving, exporting, importing, upgrading, or managing a profile never enables/disables/modifies/deletes the recipient's template or hook configuration. Lower configuration layers and existing app-theme files remain untouched by Dotprofile.

Read-only effective-config inspection detects enabled catalogues with selected IDs, enabled user templates, and relevant color/mode/wallpaper hooks. Unknown template fields and nonempty unknown hook events default to a conservative guard. Differing theme/wallpaper sections and explicit live wallpaper requests (even with an already matching default path) are skipped with an informative warning; other approved appearance fields can proceed. Known disabled templates and empty hooks remain unchanged.

The user can explicitly authorize **Noctalia's normal propagation** with `--allow-noctalia-propagation` for one apply/restore operation. The TUI's equivalent confirmation is default-off and states the consequences before showing the selected dry run. This never authorizes profile-provided automation or direct edits to any protected settings. It never installs/configures an app theme.

Under that opt-in, Noctalia may render the recipient's existing templates into external application config files and execute their existing hook commands. Such commands can have arbitrary effects. Dotprofile's backups cover its own config/library changes, not those external effects; it cannot undo them or guarantee what third-party commands do. No opt-in is persisted, inherited by restoration, or embedded in an export. Do not use the opt-in without reviewing existing recipient automation.

Primary runtime references: [Noctalia app theming](https://docs.noctalia.dev/noctalia/theming/app-theming/) and [Noctalia event hooks](https://docs.noctalia.dev/noctalia/automation/hooks/). Users independently manage those features through Noctalia; Dotprofile does not toggle them to work around propagation.

Private recovery snapshots may retain byte-for-byte source configs, including protected settings, so failed engine writes can be recovered. These snapshots are not public appearance packages. User-facing restoration filters historical configs through appearance allowlists and retains **current** templates/hooks/plugins/keybindings. Failure rollback replaces a config only if it still matches the engine's write or the precisely recognized Noctalia wallpaper IPC persistence; concurrent external edits are preserved with a recovery warning.

## Immutable Default profiles

Official originals live in the Default namespace, separate from existing/new Personal profiles. Release-owned names/file hashes in the engine, not arbitrary metadata, authenticate each official package. Qualified references distinguish `default:NAME` from `personal:NAME`; identical IDs across these separate namespaces are safe. Unqualified references select Personal first for compatibility.

Defaults can be applied/exported but not overwritten, renamed, deleted, or modified through Dotprofile. A tampered stored default fails its digest check. The only Default write path installs the exact current release catalogue after validating every package; it never changes any Personal package or running desktop. Stored files are read-only. As with any user-owned file, an owner can change permissions or bytes outside Dotprofile; that is outside the manager's boundary and invalidates authentication until a trusted package is reinstalled.

Desktop customization after applying a Default is unrestricted by library immutability. Save those appearance changes with **Save As and a new Personal name**. Switch Profile can select the Default again, subject to all ordinary appearance/layout/template compatibility protections.

Personal overwrite/import replacement/rename/delete requires explicit confirmation and a package backup before changing the stored copy. Package backup folders retain their profile ID for recovery using the normal Personal import path. A normal import—even of an exported official profile—always creates a Personal profile. Export cannot write into any managed library/state directory. Namespace overlap and symlinked packages are refused.

## Universal plugin protection

Widget IDs resolve through their configured types. Unknown/plugin types are protected, including aliases that imitate native names. No plugin-owned field/config/table/file enters a profile. Protected widgets retain their bar, lane, reference count, relative order, and capsule membership. Their original numeric indices are retained where possible; adding/removing native neighbors may shift indices without independently rearranging plugins. Mixed/plugin capsules are omitted from exports and kept intact on import/restoration. Incompatible transformations are skipped with warnings.

Complete native layout changes are staged per bar across all three lanes and capsule definitions. Approved built-in instances (including bracket-only text) can be created, placed, removed from lanes, or moved into/out of native groups. Definitions for removed native placements and inactive group rows are retained; unknown fields and existing types are preserved. Type conflicts, unresolved instance ownership, reused protected group IDs, incomplete lanes, and per-monitor/lower-layer conflicts skip the affected layout transaction with a warning. Mixed capsules and native members shared with protected capsules remain frozen globally, including their settings. Capsule updates patch only approved native source rows; protected rows retain their exact source text rather than acquiring normalized effective-export defaults. No profile can claim an unresolved current group token or widget alias.

Supported containing-bar position/geometry/style changes may apply independently of a skipped widget layout. Top/bottom are horizontal and left/right vertical under Noctalia's schema; moving the bar naturally moves all its contents on screen. Plugins retain lane/order/membership, and their configuration is never rewritten for orientation. Hardware and recipient monitor overrides remain protected; conflicting monitor geometry produces an explicit warning. Newline support is limited to the three approved display-format fields of resolved native clocks. All private-path/interpolation checks and all other scalar-field restrictions remain enforced.

The same policy applies to Default and Personal operations. Library edits never apply desktop settings. Defaults do not bypass plugin restrictions; a native widget that has become a plugin on the recipient is protected. An explicit propagation opt-in does not bypass these direct merge protections, though recipient hook commands operate outside Dotprofile's control.

## Wallpaper IPC ownership and recovery

An accepted explicit bundled image or solid color is applied with Noctalia's supported `wallpaper-set <path>` form after validation, backup, staged writes, post-write validation, and config reload. The shell handles all connected monitors; Dotprofile never derives a monitor list from hardware settings, hardcodes a connector, or imports per-monitor configuration. Existing fill/transition/directory/automation/surface behavior remains Noctalia-owned. This normal IPC intentionally updates the chosen image for connected outputs and the default; it is distinct from importing hardware or per-monitor options. Profiles still cannot contain `wallpaper.monitors`, `wallpaper.last`, directories, or automation.

The same-default case is guarded because IPC can trigger existing templates/hooks even when the saved default already matches. Enabled/unknown propagation sources require explicit consent for this operation; without it no wallpaper IPC is sent. Dry runs never send runtime IPC or create recovery state. No explicit nonempty image/color means no wallpaper IPC. Asset validation precedes any backup/write/runtime call.

The transaction checks the staged files again immediately before IPC. Successful/partial shell persistence is recognized only when the changed leaf values are the requested `wallpaper.default.path`, `wallpaper.last.path`, or `wallpaper.monitors.*.path`; all other configuration values must be identical. Noctalia can normalize the managed file's formatting/comments through its own serializer. Dotprofile does not overwrite unexpected concurrent settings to work around that boundary. Recognized persisted bytes become the expected transaction write, including when no engine config write was originally needed.

IPC failures and timeouts attempt rollback of the engine's and recognized shell configuration writes, recover the previous active marker, and retain backups. Subsequent unrelated edits still block that file's recovery and produce a warning. A partial reply/timeout may already have changed displayed wallpapers. Reloading recovered configuration does not guarantee restoration of those images; Dotprofile does not issue speculative recovery IPC or replay historical per-monitor choices. External application-template writes, hook commands, and other recipient automation effects cannot be rolled back. These limits are stated in errors; user-requested appearance restoration uses the ordinary fresh-consent flow.

## Validation and recovery limits

Dry runs validate offline candidates and make no desktop writes or reloads. Imports/restoration require effective type resolution and both native validators. Profile-library changes are staged or backed up and serialized. Desktop writes are atomic per file with backups, candidate/post-write validation, reload checks, and rollback. Engine locks do not lock the desktop GUI; changed files are not overwritten during preparation/recovery.

There is no atomic transaction across both desktop files and no automatic undo for abrupt termination, failed recovery writes, or external propagation effects. Keep independent backups. Runtime hot reload and opted-in propagation are not tested against a live desktop during release preparation.

# Changelog

## 0.6.2-beta — first public source preview

- Package the tested v0.6.2 behavior for review; engine changes are limited to its beta version label.
- Use synthetic regression fixtures, a synthetic-only optional native runner, and public release documentation. Exclude local history, personal configurations, wallpapers, backups, caches, and logs.
- No repository publication or live-desktop application is part of this source package.

## 0.6.2 — 2026-10-15

- Fix live wallpaper switching: use Noctalia's supported all-connected-monitor `wallpaper-set` IPC after profile/native validation, recovery backup, staged config writes, post-write validation, and reload. Pass the resolved bundled image as one argument without a shell.
- Reapply explicit wallpapers even when the stored default already matches, while enforcing the template/hook propagation guard for that case too. Keep dry runs free of IPC/reload/write/recovery-state side effects; empty targets warn and missing assets fail safely.
- Track only expected default/last/per-monitor wallpaper path persistence from Noctalia. Preserve wallpaper options, directories, automation, plugin/template settings, hardware, and keybindings. Concurrent/unexpected edits prevent that file's rollback instead of being overwritten.
- Handle unavailable IPC, error replies, timeouts, partial persistence, and post-IPC validation failures with configuration/marker recovery where safe. Warn that displayed monitor images may remain changed and external template/hook effects cannot be rolled back. Use the same flow for appearance restoration.
- Add wallpaper regression coverage and an isolated CLI integration with real native validators and simulated IPC. Retain all v0.6.1 layout and v0.6 protection tests; leave the TUI and existing profiles unchanged.

## 0.6.1 — 2026-10-15

- Replace fixed native-slot/count matching with a checked complete layout transition. Add/remove/relocate approved built-in placements and create missing native aliases/bracket decorations without retargeting existing types. Preserve duplicate references.
- Permit native capsule membership changes and new capsule IDs, including layout A → B → A with reused native `group:g1`. Keep unknown settings and inactive definitions.
- Preserve every plugin/unknown instance, lane, relative ordering, reference count, capsule membership, and configuration. Freeze mixed capsules and shared native members globally; refuse protected ID collisions, unresolved ownership, and unsafe lower-layer/per-monitor transitions with specific warnings. Plugin indices may shift as native neighbors are added/removed.
- Verify saving/applying all four supported bar positions, horizontal/vertical orientation, dimensions, margins, and styling. Support multiline native clock display formats without relaxing other field or interpolation checks. Warn when recipient monitor geometry overrides prevent profile fields from taking effect. Keep plugins in their containing bar while it changes screen edge.
- Share the planner between switching and appearance restoration. Add layout-only real profile fixtures, round-trip/position regressions, and reproducible offline native-validator integration. Preserve all v0.6 template/hook, immutable-default, keybinding, hardware, backup, and validation protections.
- No new TUI features, no existing profile migration, and no profile application or reload on a running live desktop during development.

## 0.6.0 — 2026-10-15

### Recipient-owned templates and hooks

- Exclude every theme-template declaration, selection, path/action, application-theme config, and hook from public appearance packages; reject them on import even with propagation opt-in. Strip source comments from saved appearance TOML to prevent private template detail leakage.
- Preserve recipient template/hook configuration exactly, including enable flags, custom template fields, command strings, unknown future settings, and settings changed since a backup.
- Keep the safe default: skip differing theme/wallpaper changes when enabled templates or relevant hooks may propagate. Respect disabled catalogues and user templates; conservatively guard unknown template settings/events.
- Add `--allow-noctalia-propagation` to apply and restore, with explicit consequences in help/output. The TUI offers a default-off informed choice and previews the selected plan. Consent is per operation, never part of a profile or remembered preference.
- Keep palette/wallpaper features supported without installing/configuring app themes. External Noctalia template/hook effects under opt-in are outside Dotprofile rollback.

### Immutable Default profiles

- Separate release-owned `defaults/` from existing/new Personal `profiles/` storage. Keep all existing Personal profiles in place during upgrade.
- Bind official status to an engine-owned release catalogue of names and file digests; imported metadata never grants it. Install official files read-only and reject tampered originals.
- Permit Default apply/export; enforce immutable originals for save, overwrite, rename, and delete in both engine and TUI. Customize the running desktop and use Save As with a new Personal name.
- Add Default/Personal labels and qualified references, keeping Personal-first resolution for legacy unqualified names. A Default and Personal profile may share an ID; official updates cannot replace the Personal copy.
- Add confirmation and package backups for Personal overwrite/import replacement/rename/delete, and an export operation whose copies import as Personal.
- Install only curated hash-validated Default packages during manager upgrade. No profile is applied and no Personal data is migrated or changed.

### Verification and documentation

- Add regression coverage for template/hook exclusion, exact preservation, safe/opted-in apply/restoration, callback consent isolation, TUI workflows, immutable defaults, namespace collisions, release authenticity, Personal backups, and operation failure recovery.
- Update README, CLI/TUI guidance, safety policy, verification report, release version, and installer. Preserve every v0.5 plugin, keybinding, hardware, field-validation, and rollback safeguard.

## 0.5.0 — 2026-10-15

### Fixed

- Separate profile IDs from configuration names. Case-sensitive bars such as `Main` no longer fail the lowercase-only ID rule and disappear from exports.
- Discover named bars using `bar.order`, appending unlisted legacy bars without importing creation order.
- Parse and export real `capsule_group` arrays of tables and `group:ID` references, including approved native members and shared appearance fields.
- Export approved workspace indicators and bracket-only decorations wherever referenced, including duplicated bracket decorations instances separated from an indicator by other widgets.
- Resolve every widget through its configured type. Native-looking plugin aliases and unknown plugins remain protected.
- Count duplicate references during safe layout merging. Keep protected lane/index positions and capsule membership fixed; skip incompatible transformations.
- Use Umbriel's installed `config validate -c PATH` command instead of the invalid `validate` command.
- Correct replacement-patch cleanup in the original tests, preventing mocked exports from leaking into subsequent tests.
- Accept bundled BMP assets consistently with the existing wallpaper suffix policy.

### Safety and compatibility

- Add field allowlists for approved native widget settings, native capsule groups, shell panel appearance, and explicit Umbriel color fields.
- Omit entire capsules with plugin/unknown members. Preserve live group array identity, unknown properties, plugin settings, bar order, actions, keybindings, hardware, and security settings.
- Apply native widget styles only to matching existing instances. Map differently named bars only for an unambiguous single-bar pair.
- Skip monitor-specific layout transformations, relocation of protected lower-layer layout data/capsule arrays, and enabling/disabling bars that contain protected widgets.
- Export only consistent, valid five-label workspace inventories. Skip incompatible counts, duplicate labels, dynamic workspaces, and minimum inventories greater than five.
- Combine full Noctalia defaults with merged user values so animations and current wallpaper paths are available before filtering; preserve the older merged-only export path.
- Validate offline candidates before writes, keep backups and atomic per-file writes, detect concurrent preparation edits, and roll back validation/write/reload failures.
- Refuse imports/restoration when effective widget resolution or native validators are unavailable.
- Restore approved appearance only: keep every current plugin configuration, installation state, bar placement, and capsule membership, including unknown plugins changed since the snapshot. Never reinstate a removed plugin. Legacy snapshots are filtered through the same allowlists.
- Preserve concurrent external/plugin edits during rollback; skip conflicting file recovery with an explicit warning and retain the private recovery snapshot.
- Reject unknown profile sidecar files/directories so plugin config and executable hooks cannot be copied by local-profile installation.
- Skip differing theme/wallpaper fields when enabled Noctalia app templates or related hooks could rewrite unrelated application configurations.

### Release preparation

- Add `--version`, `VERSION`, Fish-compatible verification instructions, and the prominent workspace-renaming warning.
- Add `install.sh --check` and `--upgrade`; upgrade only the manager with staged files and backups, preserving existing profiles without reinstalling apps.
- Add a sanitized real-schema fixture and regression/installer tests. Document native validation and isolated round trips.
- No profile was applied to a running live desktop, no existing profile was replaced, and no repository was published.

## 0.4

Existing release supplied by the user. Exported appearance and five static workspace labels, but omitted uppercase bars and lacked a running capsule-group representation.

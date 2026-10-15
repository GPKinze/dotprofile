# Dotprofile v0.6.2-beta source review

Prepared 2026-10-15 for review before the first public release. No repository push or hosted release is part of this package.

## Source identity

The runtime behavior is the tested v0.6.2 implementation. The engine differs from that baseline only in `VERSION = '0.6.2-beta'`. The top-level VERSION, installer messages, README, and changelog use the beta identity. The TUI is byte-for-byte unchanged.

Packaging-only adjustments replace development-derived fixtures with synthetic layouts, aliases, options, and hardware identifiers. Tests retain the same regression scenarios. The optional native layout runner now creates only synthetic temporary configs instead of copying an existing desktop. Its runtime IPC is prohibited. The wallpaper CLI adapter simulates every `msg` and forwards only offline configuration commands to installed native tools. The native wallpaper test generates a single gray pixel PNG in its temporary folder; no image files or encoded wallpapers are distributed.

## Included and excluded

Included: engine, TUI, installer, automated tests and their synthetic fixtures, VERSION, README, CHANGELOG, MIT license, safety policy, this review record, ignore rules, and the release-owned `example-minimal` default/example package. Its file digests match the engine's trusted default catalogue. No third-party dependencies are vendored.

Excluded: local verification histories, personal profile placeholder directories, installed Personal libraries, wallpapers and previews, desktop/application configuration files, backups, logs, temporary files, secrets, repository metadata, caches, bytecode, compiled objects, and local build outputs. The small example package contains appearance values only and no hardware, plugin, template, hook, or wallpaper data.

## Checks on the packaged source

- Full unittest discovery: **153 tests passed**, including 24 wallpaper regressions and isolated installer/TUI tests.
- Optional native layout runner: **31 isolated apply/restore operations passed**, including all twelve directed position transitions, using synthetic temporary configs and installed Noctalia 5.2.1 / Umbriel 0.1.0 validators. No runtime reload or wallpaper IPC was sent.
- The unittest CLI integration uses real installed native validators with simulated IPC. No native-validator integration was skipped on the preparation host.
- Shell syntax checks for installer/TUI, Python AST parsing, TOML parsing, version consistency, executable permissions, default catalogue hashes, and staging/extracted-tree manifest consistency pass.
- Extracted source is tested again; the archive is checked for safe relative member paths, one root directory, regular files/directories only, no links/special entries, and complete required installation files.

## Privacy review

Every included file is UTF-8 source/documentation and is examined in full by content scans. Credential checks cover private-key blocks, common cloud/GitHub/API token formats, JWTs, credential-bearing URLs, secret assignments, and high-entropy literals. Identity checks cover personal filesystem locations, emails, network addresses, machine identifiers, and local-history references. Archive headers are reviewed too: user/group names, uid/gid, timestamps, and extended filesystem metadata are normalized or omitted.

No actual credentials, tokens, personal paths, machine-specific configurations, or private user data were found. Remaining security-related strings are deliberate synthetic regression inputs (for example `secret="private"`, `token="private"`, `${SECRET}`, and `/home/private`) or field denylist text. Those are test sentinels, not working credentials or personal locations. Synthetic output IDs, sample resolutions/keybindings, plugin aliases/settings, and fake application paths exist only in tests. Runtime `$HOME`/XDG paths are portable application defaults. The public author credit and public documentation/plugin identifiers are intentional.

`MANIFEST.sha256` covers every other included file and can be checked from the extracted root with `sha256sum -c MANIFEST.sha256`. The archive's separate SHA-256 sidecar identifies the compressed artifact; neither checksum is a cryptographic signature or a substitute for publication review.

## Remaining review concerns

This is a beta. Live rendering, real multi-monitor runtime IPC, and opted-in template/hook effects were not exercised during preparation. Configuration rollback does not guarantee restoration of displayed wallpaper after partial IPC/timeouts, and external template/hook effects cannot be rolled back. Supported environment is Linux with Python 3.11+, tomlkit, Gum, Noctalia, and Umbriel; native checks require installed validators. No wallpaper rights have been verified, so none are included.

The archive is prepared for independent ChatGPT review before any publication to `GPKinze/dotprofile`. Review is still needed before creating a repository release. Existing source and installed Dotprofile are left untouched by packaging.

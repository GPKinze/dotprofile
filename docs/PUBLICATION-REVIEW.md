# v0.6.2-beta publication verification

Prepared 2026-10-16 for the source pull request from `release/v0.6.2-beta` into `main` in `GPKinze/dotprofile`. This submission does not merge the pull request or create a GitHub Release.

## Reviewed input

The maintainer approved the independently reviewed `dotprofile-v0.6.2-beta-source.tar.gz` archive for publication. Its SHA-256 was verified before extraction:

```text
9b3930404ecd4696fbc4dca86ee50d601833efb945f00d5ee78538f9646f0903
```

The archive's per-file manifest was also verified. The engine, TUI, installer, tests, synthetic fixtures, curated default/example, VERSION, LICENSE, safety policy, and historical archive review are copied byte-for-byte from that input. The CHANGELOG content is retained with a single trailing-space cleanup. No runtime source changes were made during repository integration.

## Repository integration

- Preserve the existing root README's personal note, warnings, upstream links/credits, and profile documentation links. Update development status, implemented workflows, and installation guidance to match the included beta source.
- Preserve `profiles/gruvbox-kanji/README.md` and `profiles/rdr/README.md` byte-for-byte, including confirmed Wallhaven source links and unresolved artist/redistribution notices. These remain documentation-only folders, with no personal profile configurations or wallpapers.
- Retain the archive's technical README as [USAGE.md](USAGE.md). Fix documentation-relative links and checkout-directory instructions; remove the nonexistent `profiles/review-copy/` folder reference. The temporary `review-copy` profile ID remains only in commands that create it.
- Merge all existing ignore rules with the archive's protections and additional local-artifact/image exclusions. No archive, generated test output, personal configuration, or image file is committed.
- Regenerate root `MANIFEST.sha256` over the complete final published source/documentation tree, excluding the manifest itself and Git metadata. The archive digest above remains the provenance of the reviewed input; the regenerated manifest identifies the integrated repository contents.

## Verification

- **153 automated tests passed**, with no skipped native-validator CLI integration on the preparation host.
- **31 native layout apply/restore operations passed**, including all twelve directed position transitions, using Noctalia 5.2.1 / Umbriel 0.1.0 validators and synthetic temporary configurations. Runtime reload and wallpaper IPC are suppressed or simulated throughout these checks.
- Installer/TUI shell syntax, Python/TOML parsing, required executable modes, documentation-relative links, and manifest checks pass.
- Engine/TUI/installer/test/default/example bytes match the reviewed archive. Both protected profile README hashes match the fetched release branch. Existing root README warning/note blocks and upstream credits remain present, and prior ignore rules are retained.
- Inspect the full proposed source tree for credentials, tokens, private keys, identifying local paths, personal configs, image/media files, caches, compiled artifacts, and logs. Only documented synthetic security-test inputs and portable runtime paths are retained.

No other repository, installed Dotprofile, or live desktop configuration is changed by this publication task. Tests create temporary installations/configurations only. There is no live profile application or wallpaper/reload command against the running desktop.

## Remaining beta limits

The root README retains the maintainer's report of successful live switching on their own setup. That is separate from the isolated checks run for this submission and does not establish broader hardware compatibility. Configuration rollback cannot guarantee restoration of displayed wallpapers after partial IPC/timeouts, and external Noctalia template/hook effects cannot be rolled back. Original artist attribution and redistribution rights for the documented wallpapers remain unverified; no images or installable Gruvbox Kanji/RDR bundles are included.

Review this pull request before merging. A final GitHub Release remains a separate explicit action.

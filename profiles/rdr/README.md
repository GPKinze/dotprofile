# RDR

A wallpaper-free **Personal appearance example** for **Umbriel + Noctalia**, prepared for Dotprofile **0.6.3-beta** from the author's corrected appearance. It includes supported shell/compositor styling, a bottom bar, and Roman workspace labels.

> [!IMPORTANT]
> **Installable Personal profile, not an immutable Default.** No wallpaper or preview image is bundled. Original wallpaper attribution and redistribution permissions remain unverified. Importing copies the example; applying its appearance requires a separate preview and confirmation.

## Installation

With Dotprofile 0.6.3-beta and its prerequisites available, run from the repository root:

```sh
python3 engine/profilectl.py install-profile ./profiles/rdr
python3 engine/profilectl.py apply personal:rdr --dry-run
```

Open `dotprofile`, choose **Switch Profile → Personal: rdr**, and review the preview before confirming. The installer also offers local profiles as a separate optional selection. Manager upgrades do not replace Personal profiles.

An existing Personal `rdr` is refused by default. Keep your existing copy unless you deliberately choose replacement with explicit confirmation and a backup. These instructions do not request replacement. Imported RDR remains editable as a Personal profile and is never promoted into the official Default catalogue.

## Appearance

- **Bar:** Bottom position; clock/weather at the start and volume/notifications/tray/session at the end, with approved built-in styling.
- **Center capsule:** `group:g1` contains exactly `launcher` and `workspaces`. The group has **no explicit `radius`**: Noctalia supplies automatic pill rounding. Dotprofile 0.6.3-beta clears a previous native group's explicit radius for this complete layout. Bar-level corner radii and individual widget capsule settings are separate and remain intentional.
- **Workspaces:** Compatible five-workspace outputs receive **Ⅰ Ⅱ Ⅲ Ⅳ Ⅴ** labels and indicator styling. Keybindings, workspace counts, and behavior remain protected. Review label changes before applying.
- **Palette:** Retains the author's `theme.source = "wallpaper"` and `m3-rainbow` scheme; colors depend on the recipient's existing wallpaper. `Geist Mono` must be available for matching font appearance; no font is installed by this package.
- **Wallpaper:** No wallpaper section, lockscreen wallpaper override, `@profile/` asset reference, or image. Applying this package sends no wallpaper IPC and preserves existing wallpaper paths/options. Palette changes may still trigger the recipient's existing automation, so normal propagation guards apply.
- **Customization:** Save your own appearance under a new Personal name; the only immutable Default remains `example-minimal`.

## Wallpaper attribution

| Detail | Information |
| --- | --- |
| Hosting site | [Wallhaven](https://wallhaven.cc/) |
| **Confirmed wallpaper source** | [wallhaven.cc/w/powrge](https://wallhaven.cc/w/powrge) — confirmed by the profile author |
| Original creator | **Not verified** |
| Wallhaven uploader | **Not verified**; not necessarily the creator |
| License / redistribution permission | **Not verified** |
| Local edits or resizing | **To be confirmed** |

The profile author confirmed this Wallhaven page as the source of the RDR wallpaper. **The original artist's identity and redistribution rights are not yet verified**; the Wallhaven uploader should not automatically be treated as the artist.

**No wallpaper or preview image is distributed in this folder.** Credit alone does not authorize redistribution. Obtain a wallpaper independently through its source and respect its license; Dotprofile does not download it. No missing image is required to import this package.

## Compatibility

Made for Umbriel + Noctalia. Plugins, templates, hardware configuration, keybindings, and application preferences remain under each user's control. Existing Noctalia templates may react to palette or wallpaper changes.

Schema checks use Noctalia **5.2.1** and Umbriel **0.1.0**. Unknown widgets, protected/mixed capsules, unresolved ownership, incompatible workspace layouts, or recipient monitor overrides can cause affected changes to be skipped with warnings. Wallpaper-derived colors and unavailable fonts can differ between machines. The default-safe template/hook guard may skip palette changes; an explicit per-operation propagation opt-in permits existing recipient automation, whose external effects cannot be rolled back.

Refer to the [main project README](../../README.md) for limitations, safety details, and release status.

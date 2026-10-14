# Dotprofile

> [!NOTE]
> **A personal note:** I originally made Dotprofile simply for my own Umbriel + Noctalia setup—to make saving and switching desktop themes easier for myself. I decided to share it publicly in case others find it useful too. You're welcome to try it, fork it, or adapt it to your own preferences. You don't have to follow my setup or keep my default themes. Use what works for you, and please keep a backup before experimenting.

## Requirements

Dotprofile is intended for setups running **both** of these projects:

- **[Umbriel](https://github.com/noctalia-dev/umbriel)** — Wayland compositor ([official GitHub repository](https://github.com/noctalia-dev/umbriel)).
- **[Noctalia](https://github.com/noctalia-dev/noctalia)** — Desktop shell ([official GitHub repository](https://github.com/noctalia-dev/noctalia) · [website](https://noctalia.dev/)).

> **Independent project:** Dotprofile is a personal, community-shared project. It is **not officially affiliated with or endorsed by** the Umbriel or Noctalia development teams.

**A lightweight terminal UI for saving, switching, and sharing desktop appearance profiles for Umbriel + [Noctalia](https://noctalia.dev/).**

**Made for Umbriel + Noctalia. Shared by us, customized by you.**

> [!IMPORTANT]
> **Umbriel + Noctalia only.** Dotprofile is being built specifically for systems using the Umbriel Wayland compositor together with the Noctalia shell. It is **not** a general-purpose Linux theme manager, compositor installer, or dotfiles installer.

## Why Dotprofile?

Customizing a desktop should be enjoyable, not something you have to rebuild whenever you want a new look.

Dotprofile aims to make it easy to **save an appearance**, **try another**, **share it**, and **return to a previous setup**—without replacing the user's personal configuration.

## What a profile includes

| Included appearance | Notes |
| --- | --- |
| Noctalia colors and shell styling | Uses supported appearance settings |
| Wallpaper | Bundled when distribution is permitted |
| Bar appearance and supported layout | Preserves unrelated widgets and configuration |
| Workspace indicators | Shared defaults use workspaces **1–5** |
| Lockscreen appearance | **Visual settings only**, not authentication |
| Umbriel appearance and animations | Appearance-only fields, not hardware or keybindings |

A profile is a **starting point**, not a requirement to keep someone else's choices.

## Defaults belong to everyone; customization belongs to you

Official shared profiles will be **protected originals** within Dotprofile. Apply a default, customize your desktop using Umbriel or Noctalia, and **Save As** a personal profile under another name. The original default should always remain available.

For example:

```text
gruvbox-kanji           # official default — protected
gruvbox-kanji-personal  # your customization — editable
```

**The default workspace layout is 1–5.** The sample `gruvbox-kanji` appearance uses **【 一 二 三 四 五 】**. Users who prefer different names, indicators, or arrangements can adjust those locally and save their own profile. An incompatible workspace layout should be **skipped with a warning**, not forcibly overwritten.

> [!WARNING]
> Applying a compatible profile may restyle the workspace indicator and rename **workspaces 1–5**. Check the preview before applying.

## Your plugins, templates, and system are yours

Dotprofile is **not** a plugin manager, template manager, hardware configurator, or application installer.

It must **not install, uninstall, enable, disable, export, import, or rewrite** the following:

- **Noctalia plugins**: plugin settings and widget placements remain under the user's control, including unknown and future plugins.
- **Noctalia theme templates and user hooks**: the user's selections and configuration remain untouched by Dotprofile.
- **Hardware and system settings**: monitor resolution and refresh rate, GPU settings, devices, mounts, system services, and other machine-specific settings.
- **Personal controls**: keybindings, workspace behavior outside the supported 1–5 labels, and lockscreen authentication/security settings.
- **Application configuration**: terminal, editor, GTK/Qt, and other application dotfiles are not bundled as profile configuration.

**A note about existing templates:** If you *already chose* to enable Noctalia templates, Noctalia itself may update applications when a wallpaper or palette changes. Dotprofile does not remove or reconfigure those templates. That theme propagation is controlled by your Noctalia setup and may modify application files.

Where a change cannot be made safely, Dotprofile should **skip it and explain why** rather than alter unrelated settings.

## Planned TUI workflow

```text
Desktop Profile Manager
❯ Switch Profile
  Save Current Appearance
  Import Profile
  Export Profile
  Restore Previous Configuration
  Manage Profiles
  Exit
```

- **Switch Profile:** Preview and apply a saved appearance.
- **Save Current Appearance:** Capture supported appearance settings into a personal profile.
- **Import Profile:** Add a shared profile to your local library; importing alone does **not** apply it.
- **Export Profile:** Package a saved profile for sharing or backup.
- **Restore Previous Configuration:** Recover the configuration backed up before an application.
- **Manage Profiles:** View, rename, or delete **personal** profiles; protected defaults cannot be overwritten, renamed, or deleted through Dotprofile.

The distinction between **official defaults** and **personal copies**, along with the full TUI menu above, is part of the intended next release and should not be assumed to be present in every development build.

## Safety first

The project is designed around:

1. **Field-level allowlists** instead of replacing entire configuration files.
2. **Automatic backups**, dry-run previews, validation, and a recovery path.
3. **Fail-closed handling** of unknown widgets and unsafe layouts.
4. **No executable hooks inside shared profiles.**
5. **No silent changes** to plugins, templates, hardware, keybindings, or authentication.

> [!CAUTION]
> **Development status:** The local v0.5 engine has undergone automated and isolated testing, but live profile switching and recovery on a running desktop have **not yet been verified**. Some features described here are planned rather than released. This repository currently contains documentation only; **installation instructions and official profile downloads will be added after testing**. Keep independent backups of working configurations.

## Sharing and contributing

Everyone is welcome to create their own profile. Importing one to your computer **does not modify this GitHub repository**.

Once releases are available, contributors will be able to propose new profiles through pull requests for review. Shared profiles must be safe to distribute: **no secrets, private data, plugin or template configuration, or unlicensed wallpapers**.

## Project status

**In development — documentation-first repository.**

First goals: verify safe live switching and rollback, finish protected default/personal profiles, document installation, and publish tested example themes.

---

*Dotprofile supplies the appearance. You decide the rest.*

# Dotprofile

> [!NOTE]
> **A personal note:** I originally made Dotprofile simply for my own Umbriel + Noctalia setup—to make saving and switching desktop themes easier for myself. I decided to share it publicly in case others find it useful too. You're welcome to try it, fork it, or adapt it to your own preferences. You don't have to follow my setup or keep my default themes. Use what works for you, and please keep a backup before experimenting.

**A lightweight terminal UI (TUI) for saving, switching, and sharing desktop appearance profiles.**

*Made for Umbriel + Noctalia. Shared by us, customized by you.*

> [!IMPORTANT]
> **Umbriel + Noctalia only.** Dotprofile is designed for systems running both projects together. It is not a general-purpose Linux theme manager, desktop installer, or complete dotfiles manager.

## Requirements

| Project | What it provides | Official links |
| --- | --- | --- |
| **Umbriel** | Wayland compositor | [GitHub](https://github.com/noctalia-dev/umbriel) |
| **Noctalia** | Desktop shell | [GitHub](https://github.com/noctalia-dev/noctalia) · [Website](https://noctalia.dev/) |

Dotprofile is an **independent personal project**, not officially affiliated with or endorsed by the Umbriel or Noctalia development teams.

## What Dotprofile does

The idea is simple: **save an appearance, try another, and return to the one you like**—without replacing your personal setup.

### Planned TUI

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

| Action | Purpose |
| --- | --- |
| **Switch Profile** | Preview and apply a saved appearance |
| **Save Current Appearance** | Capture supported appearance settings into a personal profile |
| **Import Profile** | Add a shared profile to your local library; **does not apply it** |
| **Export Profile** | Package a profile for sharing or backup |
| **Restore Previous Configuration** | Restore the backup made before applying a profile |
| **Manage Profiles** | View, rename, or delete personal profiles |

This menu describes the **intended user experience**. Some options are still being developed; see [Project status](#project-status).

## What's in a profile?

| Appearance | Scope |
| --- | --- |
| **Noctalia theme** | Colors and supported shell styling |
| **Wallpaper** | Included when redistribution is permitted |
| **Bar** | Supported appearance, layout, and built-in widget styling |
| **Workspaces** | Indicator appearance and labels for workspaces **1–5** |
| **Lockscreen** | Visual appearance only; never authentication |
| **Umbriel** | Appearance and animation settings, not hardware or keybindings |

### Five-workspace default

Shared profiles use **workspaces 1–5** by default. For example, `gruvbox-kanji` uses:

```text
【 一 二 三 四 五 】
```

> [!WARNING]
> Applying a compatible profile **may change the workspace indicator and labels for workspaces 1–5**. If you prefer different labels or styling, customize them manually in your own setup and save the result under a new profile name. Incompatible workspace layouts should be skipped with a warning rather than forced.

### Default vs. personal profiles

The **planned** profile-library design keeps official default profiles protected, so anyone can return to the original appearance.

```text
gruvbox-kanji           # shared default — protected
gruvbox-kanji-personal  # your customized copy
```

Apply a default, adjust your desktop with Umbriel or Noctalia, then **Save As** a personal profile. Personal profiles can be managed by their owners; defaults should not be overwritten, renamed, or deleted through Dotprofile.

## What Dotprofile leaves alone

**Your setup, your preferences.** Appearance profiles do **not** include or manage:

- **Noctalia plugins:** Installation state, settings, plugin widgets, and their placement—including unknown or future plugins.
- **Noctalia templates and hooks:** Installed/configured templates, enabled states, and user-defined hooks.
- **Hardware and system settings:** Monitors, refresh rates, GPUs, devices, mounts, and system services.
- **Personal controls:** Keybindings, unsupported workspace behavior, and lockscreen authentication.
- **Application configuration:** Terminal, editor, GTK/Qt, and other app dotfiles.

**Already use Noctalia templates?** They stay configured as you chose. When a wallpaper or palette changes, **Noctalia itself may automatically update applications** through those templates. Dotprofile does not manage them, but this normal Noctalia behavior can modify application files.

When Dotprofile cannot safely apply part of a profile, it should **skip that change and explain why**, rather than silently change unrelated settings.

## Safety and recovery

The project aims to provide:

- **Preview and validation** before applying appearance changes.
- **Automatic backups** and a recovery path.
- **Allowlisted appearance fields**, not wholesale configuration replacement.
- **Protection for unknown widgets and unsafe layouts.**
- **No executable scripts or hooks** bundled inside shared profiles.

Keep your own backup of working Umbriel and Noctalia configurations before experimenting. A successful export or dry run does not guarantee that live switching will behave correctly on every setup.

## Profile documentation

Two appearance profiles are being prepared for the first public release:

| Profile | Description | Status |
| --- | --- | --- |
| **[Gruvbox Kanji](profiles/gruvbox-kanji/README.md)** | Gruvbox-inspired appearance with five Kanji workspace indicators | Documentation draft |
| **[RDR](profiles/rdr/README.md)** | Alternate bar layout, wallpaper, and palette | Documentation draft |

> [!NOTE]
> Both profile pages currently contain **provisional Wallhaven attribution**. The wallpaper IDs came from earlier local filenames; neither image has yet been independently matched to the final saved profile nor cleared for redistribution. **No wallpaper images or installable profile bundles are published in these folders.** Full profiles will be added only after source and rights review.

## Sharing and contributing

You're welcome to **use, customize, or fork** this project. Importing a profile to your PC **does not change this GitHub repository**.

When profile submissions open, contributors will be able to suggest new themes through **pull requests**, subject to review. Please avoid publishing secrets, private settings, plugin/template configurations, or wallpapers you don't have permission to redistribute.

## Project status

> [!CAUTION]
> **In development.** The local v0.5 engine has passed reported automated and isolated checks, but **live profile switching and recovery have not yet been verified**. The planned protected-default workflow and some TUI options are not necessarily implemented in the current build.

This repository currently contains **documentation only**. Tested source code, installation instructions, and official downloadable profiles will be added after verification.

---

*Dotprofile supplies the appearance. You decide the rest.*

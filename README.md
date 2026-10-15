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

### TUI

```text
Desktop Profile Manager
❯ Switch Profile
  Save As — current appearance
  Manage profiles
  Export a profile
  Import a Personal profile
  Restore desktop appearance from a backup
  See active profile
  Quit
```

| Action | Purpose |
| --- | --- |
| **Switch Profile** | Preview and apply a saved appearance |
| **Save As — current appearance** | Capture supported appearance settings into a personal profile |
| **Import a Personal profile** | Add a shared profile to your local library; **does not apply it** |
| **Export a profile** | Package a profile for sharing or backup |
| **Restore desktop appearance from a backup** | Restore approved appearance while retaining current plugins and unrelated settings |
| **Manage profiles** | View, rename, or delete personal profiles |

These workflows are implemented in the **v0.6.3-beta source**. The menu uses Default/Personal labels and previews appearance changes before confirmation. See [Project status](#project-status) for beta limits.

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

The profile library keeps release-owned **Default** profiles separate from **Personal** profiles. Default originals are read-only through both the engine and TUI. The only immutable Default remains `example-minimal`. [RDR](profiles/rdr/README.md) is an installable wallpaper-free **Personal** example; Gruvbox Kanji remains documentation-only.

```text
default:example-minimal  # release-owned original — protected
personal:my-appearance   # your customized copy
```

Apply a default, adjust your desktop with Umbriel or Noctalia, then **Save As** a personal profile. Personal profiles can be managed by their owners; defaults cannot be overwritten, renamed, or deleted through Dotprofile.

## What Dotprofile leaves alone

**Your setup, your preferences.** Appearance profiles do **not** include or manage:

- **Noctalia plugins:** Installation state, settings, plugin widgets, and their placement—including unknown or future plugins.
- **Noctalia templates and hooks:** Installed/configured templates, enabled states, and user-defined hooks.
- **Hardware and system settings:** Monitors, refresh rates, GPUs, devices, mounts, and system services.
- **Personal controls:** Keybindings, unsupported workspace behavior, and lockscreen authentication.
- **Application configuration:** Terminal, editor, GTK/Qt, and other app dotfiles.

**Already use Noctalia templates?** They stay configured as you chose. When a wallpaper or palette changes, **Noctalia itself may automatically update applications** through those templates. Dotprofile does not manage them, but this normal Noctalia behavior can modify application files.

The beta skips wallpaper/palette propagation when existing templates or hooks could run, unless you explicitly opt in for that operation. The opt-in does not permit changes to their configuration; external template/hook effects cannot be rolled back. See the [safety policy](docs/SAFETY.md) and [technical usage guide](docs/USAGE.md).

When Dotprofile cannot safely apply part of a profile, it should **skip that change and explain why**, rather than silently change unrelated settings.

## Safety and recovery

The beta provides:

- **Preview and validation** before applying appearance changes.
- **Automatic backups** and a recovery path.
- **Allowlisted appearance fields**, not wholesale configuration replacement.
- **Protection for unknown widgets and unsafe layouts.**
- **No executable scripts or hooks** bundled inside shared profiles.

Keep your own backup of working Umbriel and Noctalia configurations before experimenting. A successful export or dry run does not guarantee that live switching will behave correctly on every setup.

## Installation (v0.6.3-beta)

Before this PR is merged, use its `dev/v0.6.3-beta` checkout to review the update.

Requires **Linux, Python 3.11+, `tomlkit`, Gum, Umbriel, and Noctalia**. The reviewed schema tests use Noctalia **5.2.1** and Umbriel **0.1.0**; broader compatibility is still beta testing. On Arch/CachyOS, the interactive installer can offer only missing Python/tomlkit/Gum dependencies. It does not install Umbriel, Noctalia, application themes, or unrelated applications.

```fish
git clone https://github.com/GPKinze/dotprofile.git
cd dotprofile
./install.sh
fish_add_path ~/.local/bin
dotprofile --version
```

Installation copies the manager and curated default without applying a profile. Existing personal profiles and desktop settings are preserved. Before upgrading an existing installation, run `./install.sh --check`; with dependencies available, `./install.sh --upgrade` updates the manager with backups. Do not run the installer as root.

For profile previews, export/import, propagation opt-in, workspace warnings, recovery limits, and developer checks, see [docs/USAGE.md](docs/USAGE.md). This beta includes the immutable `example-minimal` Default and the wallpaper-free RDR Personal example. Import RDR explicitly with `python3 engine/profilectl.py install-profile ./profiles/rdr`, then review it under **Switch Profile → Personal: rdr**. Importing does not apply it and refuses an existing Personal `rdr` unless replacement is explicitly confirmed with a backup. No wallpaper or preview images are included.

## Profile documentation

The following appearance profiles have different publication status:

| Profile | Description | Status |
| --- | --- | --- |
| **[Gruvbox Kanji](profiles/gruvbox-kanji/README.md)** | Gruvbox-inspired appearance with five Kanji workspace indicators | Documentation draft |
| **[RDR](profiles/rdr/README.md)** | Bottom bar, automatic launcher/workspaces pill capsule, Roman workspace labels, and supported appearance | Installable Personal example; no wallpaper |

> [!NOTE]
> The maintainer has **confirmed the Wallhaven source links** for both profiles. Original artist attribution and redistribution permissions have **not** been verified. **No wallpaper images are bundled.** RDR ships approved appearance TOML without wallpaper references; Gruvbox Kanji remains documentation-only. Obtain any wallpaper independently and respect its license.

## Sharing and contributing

You're welcome to **use, customize, or fork** this project. Importing a profile to your PC **does not change this GitHub repository**.

When profile submissions open, contributors will be able to suggest new themes through **pull requests**, subject to review. Please avoid publishing secrets, private settings, plugin/template configurations, or wallpapers you don't have permission to redistribute.

## Project status

> [!CAUTION]
> **Source beta — v0.6.3-beta.** This update fixes explicit native capsule radius leaking into an incoming automatic pill layout and publishes the wallpaper-free RDR Personal example. **159 automated tests**, **36 isolated native layout operations**, and isolated RDR import checks pass locally. GitHub Actions runs offline checks on Python 3.11 and 3.12; native validators are not installed in CI. Native tests use synthetic temporary configurations, with runtime IPC simulated or suppressed. Broader hardware compatibility remains beta testing.

The earlier [v0.6.2-beta publication verification](docs/PUBLICATION-REVIEW.md) remains historical provenance. See [v0.6.3-beta verification](docs/V0.6.3-BETA-VERIFICATION.md) for this update and [GitHub Releases](https://github.com/GPKinze/dotprofile/releases) for published snapshots. This development update does not itself create a release. Broader compatibility and wallpaper redistribution review remain.

---

*Dotprofile supplies the appearance. You decide the rest.*

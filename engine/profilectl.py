#!/usr/bin/env python3
"""TUI-only portable Noctalia/Umbriel appearance profiles.

Exports/imports safe workspace-indicator styling and exactly five workspace
labels, but never plugins, arbitrary widgets, keybindings, hardware output
settings, services, or lock-screen authentication controls.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import math
import fcntl
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

try:
    import tomlkit
except ImportError:
    print('Install python-tomlkit (sudo pacman -S python-tomlkit)', file=sys.stderr)
    raise SystemExit(2)

VERSION = '0.6.2-beta'
HOME = Path.home()
PROFILE_ROOT = Path(os.environ.get('NDP_PROFILE_ROOT', HOME / '.local/share/dotprofile/profiles')).expanduser()
DEFAULT_ROOT = Path(os.environ.get('NDP_DEFAULT_ROOT', HOME / '.local/share/dotprofile/defaults')).expanduser()
STATE_ROOT = Path(os.environ.get('NDP_STATE_ROOT', HOME / '.local/state/dotprofile')).expanduser()
UMBRIEL_FILE = Path(os.environ.get('NDP_UMBRIEL_FILE', HOME / '.config/umbriel/config.toml')).expanduser()
NOCTALIA_FILE = Path(os.environ.get('NDP_NOCTALIA_FILE', Path(os.environ.get('NOCTALIA_STATE_HOME', os.environ.get('XDG_STATE_HOME', HOME / '.local/state'))) / 'noctalia/settings.toml')).expanduser()
# Release-owned names and file digests, never imported profile metadata.
OFFICIAL_DEFAULTS = {'example-minimal': {'noctalia.toml': 'f38e34e3212a00357bed54ce81a9f1c9bd1bca88be59403bfbfe019aac7304c7', 'profile.toml': '63428d82eb0773ed19c604f381ecdd051786fe27138f8196eb3bb71eea0fd139', 'umbriel.toml': '2524c16ac745fb23b26c966903c496d08feab3a054cfc1318da2d849bb47be8c'}}
ID = re.compile(r'^[a-z0-9][a-z0-9_-]{0,63}$')
PORTABLE = '@profile/'
IMAGE_SUFFIXES = frozenset(('.png', '.jpg', '.jpeg', '.webp', '.bmp'))
BAR_SECTIONS = ('start', 'center', 'end')
# Resolved native types only. Aliases may use these types; an alias that
# resolves to a plugin/unknown type is protected even if its ID is native.
NATIVE_WIDGET_TYPES = frozenset(('launcher', 'wallpaper', 'clock', 'media', 'tray',
    'notifications', 'clipboard', 'network', 'bluetooth', 'volume', 'brightness',
    'battery', 'control-center', 'control_center', 'session', 'cpu', 'memory',
    'disk', 'system-monitor', 'weather', 'power', 'spacer', 'separator',
    'audio_visualizer', 'active_window', 'keyboard_layout', 'lock_keys', 'sysmon',
    'taskbar', 'caffeine', 'nightlight', 'power_profile', 'privacy', 'screenshot',
    'settings', 'theme_mode'))
BAR_KEYS = frozenset(('position', 'enabled', 'auto_hide', 'auto_hide_delay_ms',
    'smart_auto_hide', 'show_on_workspace_switch', 'reserve_space', 'layer',
    'thickness', 'background_opacity', 'compositor_blur', 'border', 'border_width',
    'shadow', 'contact_shadow', 'panel_overlap', 'radius', 'radius_top_left',
    'radius_top_right', 'radius_bottom_left', 'radius_bottom_right',
    'concave_edge_corners', 'margin_ends', 'margin_edge', 'margin_opposite_edge',
    'padding', 'widget_spacing', 'hover_highlight', 'show_tooltip', 'scale',
    'font_scale', 'font_weight', 'font_family', 'capsule', 'capsule_fill',
    'capsule_thickness', 'capsule_radius', 'capsule_opacity', 'capsule_border',
    'capsule_border_width', 'capsule_padding', 'capsule_foreground', 'color', 'icon_color'))
THEME_KEYS = frozenset(('mode', 'shell_mode', 'source', 'builtin',
    'community_palette', 'custom_palette', 'wallpaper_scheme', 'pure_black_dark'))
WALLPAPER_KEYS = frozenset(('fill_mode', 'fill_color', 'transition',
    'transition_duration', 'edge_smoothness', 'transition_on_startup'))
LOCKSCREEN_KEYS = frozenset(('transition', 'transition_duration',
    'edge_smoothness', 'blur_intensity', 'tint_intensity', 'wallpaper'))
SHELL_KEYS = frozenset(('corner_radius_scale', 'button_borders',
    'input_borders', 'popup_borders', 'card_borders', 'popup_shadows',
    'font_family', 'settings_window_translucent', 'app_icon_colorize',
    'app_icon_color'))
SHELL_ANIM_KEYS = frozenset(('enabled', 'speed'))
SHELL_PANEL_KEYS = frozenset(('transparency_mode', 'borders', 'shadow', 'list_item_background'))
SHELL_SHADOW_KEYS = frozenset(('direction', 'alpha'))
UMBRIEL_APPEARANCE_KEYS = frozenset(('prefer_no_csd', 'border_width',
    'outer_border_width', 'corner_radius', 'drag_opacity'))
UMBRIEL_BLUR_KEYS = frozenset(('enabled', 'optimized', 'passes', 'radius',
    'noise', 'brightness', 'contrast', 'saturation'))
UMBRIEL_SHADOW_KEYS = frozenset(('enabled', 'softness', 'offset_x', 'offset_y'))
UMBRIEL_ANIM_ROOT = frozenset(('enabled', 'duration_ms', 'curve'))
UMBRIEL_ANIM_CHILD = frozenset(('enabled', 'duration_ms', 'curve', 'style',
    'scale', 'workspace_curve', 'dim', 'blur', 'maximize', 'fullscreen'))
UMBRIEL_ANIM_GROUPS = frozenset(('windows_in', 'windows_out', 'windows_move',
    'workspaces', 'overview', 'scratchpad', 'border', 'dim_unfocused', 'layers'))
# Native workspace indicators and bracket-only text are permitted.
# Other text widgets may contain personal content and are always excluded.
BRACKETS = frozenset(('【', '】', '［', '］', '[', ']', '(', ')', '〈', '〉', '「', '」'))
COMMON_INDICATOR_KEYS = frozenset(('scale', 'font_scale', 'font_weight',
    'font_family', 'capsule', 'capsule_radius', 'capsule_fill',
    'capsule_foreground', 'capsule_padding', 'capsule_opacity',
    'capsule_border', 'capsule_border_width', 'color', 'icon_color',
    'show_tooltip'))
WORKSPACE_WIDGET_KEYS = COMMON_INDICATOR_KEYS | frozenset(('type', 'style',
    'show_labels', 'show_icons', 'label_source', 'max_label_chars',
    'pill_scale', 'active_pill_size', 'inactive_pill_size',
    'focused_color', 'occupied_color', 'empty_color', 'urgent_color',
    'change_color_on_hover', 'focused_output_only',
    'labels_only_when_occupied', 'hide_when_empty', 'show_all_outputs'))
BRACKET_WIDGET_KEYS = COMMON_INDICATOR_KEYS | frozenset(('type', 'text'))


# Fields verified against Noctalia 5.2.1's export and bar schema. Never copy
# actions, commands, devices, paths, anchors, capsule_group, or plugin tables.
GROUP_KEYS = frozenset(('enabled', 'fill', 'foreground', 'border', 'border_width',
    'radius', 'opacity', 'padding', 'widget_spacing', 'accordion', 'accordion_direction'))
WIDGET_KEYS = {
    'launcher': {'glyph'},
    'clock': {'format', 'vertical_format', 'tooltip_format'},
    'audio_visualizer': {'width', 'bands', 'mirrored', 'centered', 'show_when_idle', 'color_1', 'color_2'},
    'weather': {'show_condition'},
    'notifications': {'hide_when_no_unread'},
    'tray': {'drawer', 'icon_size'},
    'media': {'hide_when_no_media', 'max_length', 'min_length', 'title_scroll', 'art_size', 'rotate_album_art'},
    'active_window': {'icon_size', 'max_length', 'min_length', 'title_scroll'},
    'spacer': {'width'},
    'sysmon': {'stat', 'show_glyph', 'format'},
}


def config_name(name):
    return isinstance(name, str) and 0 < len(name) <= 128 and name.isprintable() and safe_scalar(name)


def string_array(value):
    return isinstance(value, (list, tuple)) and all(isinstance(v, str) for v in value)


def bar_names(bars):
    """Follow case-sensitive creation order; append unlisted named bars (legacy)."""
    if not table(bars):
        raise ProfileError('bar must be a table')
    order = bars.get('order', [])
    if not string_array(order) or len(set(order)) != len(order):
        raise ProfileError('bar.order must contain unique bar names')
    return list(dict.fromkeys([*order, *(k for k in bars if k != 'order')]))


def approved_widget(wid, widgets):
    if not config_name(wid) or wid.startswith('group:'):
        return None
    if wid in widgets and not table(widgets[wid]):
        return None
    kind = widget_type(wid, widgets)
    if not isinstance(kind, str):
        return None
    if kind == 'workspaces':
        return kind
    if kind == 'text':
        return 'text' if section(widgets, wid).get('text') in BRACKETS else None
    return kind if kind in NATIVE_WIDGET_TYPES else None


def group_index(bar):
    raw = bar.get('capsule_group', [])
    if not isinstance(raw, (list, tuple)) or any(not table(g) for g in raw):
        raise ProfileError('capsule_group must be an array of tables')
    ids = [g.get('id') for g in raw]
    if any(not config_name(i) for i in ids) or len(set(ids)) != len(ids):
        raise ProfileError('Capsule group IDs must be unique printable strings')
    return {g['id']: g for g in raw}


def safe_group(group, widgets):
    members = group.get('members')
    return string_array(members) and bool(members) and all(approved_widget(v, widgets) for v in members)


def referenced_widgets(bar):
    groups = group_index(bar)
    result = []
    for lane in BAR_SECTIONS:
        for wid in bar.get(lane, []):
            if isinstance(wid, str) and wid.startswith('group:'):
                result.extend(groups.get(wid[6:], {}).get('members', []))
            else:
                result.append(wid)
    return result


class ProfileError(Exception):
    pass


def parse(path: Path):
    if path.is_symlink():
        raise ProfileError(f'Symlinked config refused: {path}')
    if not path.exists():
        return tomlkit.document()
    return tomlkit.parse(path.read_text(encoding='utf-8'))


def table(obj):
    return hasattr(obj, 'items')


def section(obj, *names):
    cur = obj
    for name in names:
        if not table(cur) or name not in cur:
            return {}
        cur = cur[name]
    return cur if table(cur) else {}


def put(doc, path, value):
    cur = doc
    for key in path[:-1]:
        if key not in cur:
            cur[key] = tomlkit.table()
        if not table(cur[key]):
            raise ProfileError(f'Non-table at {key}')
        cur = cur[key]
    cur[path[-1]] = copy.deepcopy(value)


def safe_scalar(value):
    # Profile fields are data only, and must not contain nested unreviewed
    # commands, references to private files, or shell interpolation.
    if isinstance(value, (str, int, float, bool)):
        if isinstance(value, float) and not math.isfinite(value):
            return False
        if isinstance(value, str) and any(x in value.lower() for x in ('/home/', '/users/', '${', '$(', '`', '\n')):
            return False
        return True
    return isinstance(value, (list, tuple)) and len(value) <= 30 and all(safe_scalar(v) for v in value)


def filter_keys(src, dst, prefix, allowed, strict, *, multiline=frozenset()):
    if not table(src):
        raise ProfileError(f'Expected TOML table: {".".join(prefix)}')
    for key, val in src.items():
        if key not in allowed:
            if strict:
                raise ProfileError(f'Forbidden profile setting: {".".join((*prefix, key))}')
            continue
        # Native clock formats explicitly support line breaks for vertical bars.
        # Keep every other portability/interpolation check, and keep this
        # exception out of names, metadata, plugins, and executable fields.
        safe = safe_scalar(val) or (key in multiline and isinstance(val, str)
                                   and safe_scalar(val.replace('\n', '')))
        if not safe:
            if strict:
                raise ProfileError(f'Unsafe or nonportable value: {".".join((*prefix, key))}')
            # For exports, omit non-portable values instead of sharing them.
            continue
        put(dst, (*prefix, key), val)


def widget_type(widget_id, widgets):
    definition = section(widgets, widget_id)
    return definition.get('type', widget_id)


def clean_workspace(src, strict=False):
    """A profile may define ONLY the five workspace labels, never monitor identity/mode."""
    out = tomlkit.document()
    if not src:
        return out
    if set(src.keys()) != {'workspace_indicator'}:
        raise ProfileError('Workspace profile can only contain [workspace_indicator]')
    data = src['workspace_indicator']
    if not table(data) or set(data.keys()) != {'labels'}:
        raise ProfileError('Workspace profile must contain only workspace_indicator.labels')
    labels = data['labels']
    if not isinstance(labels, (list, tuple)) or len(labels) != 5 or any(
        not isinstance(v, str) or not v or len(v) > 8 or not v.isprintable()
        or not safe_scalar(v) for v in labels
    ) or len(set(labels)) != 5:
        raise ProfileError('Exactly five distinct, printable workspace names are required (1–5)')
    put(out, ('workspace_indicator', 'labels'), list(labels))
    return out


def extract_workspaces(live_umbriel):
    """Only an unambiguous, valid static five-label inventory is portable."""
    inventories = []
    for output in section(live_umbriel, 'output').values():
        if table(output):
            labels = output.get('workspaces')
            if string_array(labels) and len(labels) == 5 and output.get('min_workspaces', 1) <= 5:
                doc = tomlkit.document()
                put(doc, ('workspace_indicator', 'labels'), list(labels))
                try:
                    clean_workspace(doc)
                except ProfileError:
                    continue
                inventories.append(tuple(labels))
    if not inventories or len(set(inventories)) != 1:
        return tomlkit.document()
    out = tomlkit.document()
    put(out, ('workspace_indicator', 'labels'), list(inventories[0]))
    return clean_workspace(out)


def patch_workspace_names(live, profile):
    notes = []
    if not profile:
        return notes
    labels = list(profile['workspace_indicator']['labels'])
    configured = 0
    for output_id, item in section(live,'output').items():
        # Do not change monitors with dynamic or non-five-workspace inventories.
        if not table(item):
            continue
        current = item.get('workspaces')
        if string_array(current) and len(current) == 5 and len(set(current)) == 5 and all(current) and item.get('min_workspaces', 1) <= 5:
            put(live, ('output',output_id,'workspaces'), labels)
            configured += 1
        else:
            notes.append(f'output.{output_id} workspace names skipped (not five distinct static labels)')
    if not configured:
        notes.append('workspace labels skipped (no existing static five-workspace Umbriel output; set it manually first)')
    return notes


def clean_noctalia(src, strict=False):
    out = tomlkit.document()
    if strict and ('templates' in section(src, 'theme') or 'hooks' in src):
        raise ProfileError('Theme templates and user-defined hooks are forbidden in appearance profiles (including with propagation opt-in)')
    allowed_top = {'theme', 'wallpaper', 'lockscreen', 'shell', 'bar', 'widget'}
    if strict and set(src.keys()) - allowed_top:
        raise ProfileError('Prohibited Noctalia sections: ' + ', '.join(sorted(set(src.keys()) - allowed_top)))
    for name, keys in (('theme', THEME_KEYS), ('lockscreen', LOCKSCREEN_KEYS)):
        if name in src:
            filter_keys(src[name], out, (name,), keys, strict)
    if 'wallpaper' in src:
        wall = src['wallpaper']
        if not table(wall):
            raise ProfileError('wallpaper must be a table')
        if strict and (set(wall.keys()) - (WALLPAPER_KEYS | {'default'})):
            raise ProfileError('Forbidden wallpaper setting (monitor/directory/automation/favorites)')
        filter_keys({k:v for k,v in wall.items() if k in WALLPAPER_KEYS}, out,
                    ('wallpaper',), WALLPAPER_KEYS, strict)
        if 'default' in wall:
            filter_keys(wall['default'], out, ('wallpaper', 'default'), {'path'}, strict)
    if 'shell' in src:
        sh = src['shell']
        if not table(sh):
            raise ProfileError('shell must be a table')
        if strict and set(sh.keys()) - (SHELL_KEYS | {'animation', 'shadow', 'panel'}):
            raise ProfileError('Forbidden shell setting (keybinds, services or plugin options)')
        filter_keys({k:v for k,v in sh.items() if k in SHELL_KEYS}, out, ('shell',), SHELL_KEYS, strict)
        for child, keys in (('animation', SHELL_ANIM_KEYS), ('shadow', SHELL_SHADOW_KEYS), ('panel', SHELL_PANEL_KEYS)):
            if child in sh:
                filter_keys(sh[child], out, ('shell', child), keys, strict)

    widgets = src.get('widget', {})
    if not table(widgets):
        raise ProfileError('widget must be a table')
    allowed_widget_ids = {}
    if 'bar' in src:
        bars = src['bar']
        if not table(bars):
            raise ProfileError('bar must be a table')
        if strict and 'order' in bars:
            raise ProfileError('bar.order is protected')
        for name in bar_names(bars):
            item = bars.get(name)
            if not config_name(name) or not table(item):
                if strict:
                    raise ProfileError('Invalid bar name or table')
                continue
            allowed = BAR_KEYS | set(BAR_SECTIONS) | {'capsule_group'}
            if strict and set(item) - allowed:
                raise ProfileError(f'Forbidden bar.{name} key (actions/monitor overrides)')
            filter_keys({k:v for k,v in item.items() if k in BAR_KEYS}, out,
                        ('bar', name), BAR_KEYS, strict)
            groups = group_index(item)
            used_groups = []
            for lane in BAR_SECTIONS:
                if lane not in item:
                    continue
                if not string_array(item[lane]):
                    raise ProfileError(f'bar.{name}.{lane} must be a string array')
                filtered = []
                for wid in item[lane]:
                    if wid.startswith('group:'):
                        gid = wid[6:]
                        group = groups.get(gid)
                        # Omit the ENTIRE plugin/unknown-bearing container:
                        # even its membership and lane token are protected data.
                        ok = group is not None and safe_group(group, widgets)
                        if ok:
                            if gid not in used_groups:
                                used_groups.append(gid)
                            for member in group['members']:
                                allowed_widget_ids[member] = approved_widget(member, widgets)
                    else:
                        kind = approved_widget(wid, widgets)
                        ok = bool(kind)
                        if ok:
                            allowed_widget_ids[wid] = kind
                    if not ok and strict:
                        raise ProfileError(f'bar.{name}.{lane} contains plugin/unknown/unsafe widgets')
                    if ok:
                        filtered.append(wid)
                put(out, ('bar', name, lane), filtered)
            if strict and set(groups) - set(used_groups):
                raise ProfileError('Unreferenced capsule group in profile')
            if used_groups:
                aot = tomlkit.aot()
                for gid in used_groups:
                    raw = groups[gid]
                    doc = tomlkit.document()
                    filter_keys(raw, doc, (), GROUP_KEYS | {'id', 'members'}, strict)
                    entry = tomlkit.table()
                    for k, v in doc.items():
                        entry[k] = copy.deepcopy(v)
                    aot.append(entry)
                put(out, ('bar', name, 'capsule_group'), aot)

    if strict and set(widgets) - set(allowed_widget_ids):
        raise ProfileError('Profile includes unreferenced or protected widget settings')
    for wid, kind in allowed_widget_ids.items():
        if wid not in widgets:
            put(out, ('widget', wid, 'type'), kind)
            continue
        keys = (WORKSPACE_WIDGET_KEYS if kind == 'workspaces' else
                BRACKET_WIDGET_KEYS if kind == 'text' else
                COMMON_INDICATOR_KEYS | {'type'} | WIDGET_KEYS.get(kind, set()))
        filter_keys(widgets[wid], out, ('widget', wid), keys, strict,
                    multiline={'format', 'vertical_format', 'tooltip_format'} if kind == 'clock' else frozenset())

    return out


def clean_umbriel(src, strict=False):
    out = tomlkit.document()
    allow_top = {'appearance','animation','colors','layout'}
    if strict and set(src.keys()) - allow_top:
        raise ProfileError('Forbidden Umbriel section: ' + ', '.join(sorted(set(src.keys())-allow_top)))
    if 'appearance' in src:
        ap=src['appearance']
        if not table(ap): raise ProfileError('appearance must be a table')
        if strict and set(ap.keys()) - (UMBRIEL_APPEARANCE_KEYS | {'blur','shadow'}):
            raise ProfileError('Forbidden Umbriel appearance key')
        filter_keys({k:v for k,v in ap.items() if k in UMBRIEL_APPEARANCE_KEYS}, out,('appearance',),UMBRIEL_APPEARANCE_KEYS, strict)
        for child, keys in (('blur',UMBRIEL_BLUR_KEYS),('shadow',UMBRIEL_SHADOW_KEYS)):
            if child in ap: filter_keys(ap[child],out,('appearance',child),keys,strict)
    if 'animation' in src:
        anim=src['animation']
        if not table(anim): raise ProfileError('animation must be a table')
        if strict and set(anim.keys()) - (UMBRIEL_ANIM_ROOT | UMBRIEL_ANIM_GROUPS):
            raise ProfileError('Animation shaders/custom curves are not portable')
        filter_keys({k:v for k,v in anim.items() if k in UMBRIEL_ANIM_ROOT},out,('animation',),UMBRIEL_ANIM_ROOT,strict)
        for group in UMBRIEL_ANIM_GROUPS:
            if group in anim:
                filter_keys(anim[group],out,('animation',group),UMBRIEL_ANIM_CHILD,strict)
    if 'colors' in src:
        color = src['colors']
        if not table(color):
            raise ProfileError('Umbriel colors must be table')
        root_keys = {'accent_primary', 'accent_secondary', 'backdrop', 'background',
                     'error', 'insert_hint', 'shadow', 'text_muted', 'text_primary', 'warning'}
        children = {'border': {'focused', 'outer', 'unfocused'},
                    'overview': {'background_tint', 'badge', 'workspace_background'},
                    'tab_bar': {'active', 'active_text', 'active_unfocused',
                                'active_unfocused_text', 'background', 'text', 'urgent', 'urgent_text'}}
        def colors(data, path, allowed):
            for key, value in data.items():
                if key not in allowed or not isinstance(value, str) or not re.fullmatch('#[a-fA-F0-9]{6}(?:[a-fA-F0-9]{2})?', value):
                    if strict:
                        raise ProfileError('Forbidden color key or non-hex color: ' + '.'.join((*path, key)))
                    continue
                put(out, (*path, key), value)
        colors({k:v for k,v in color.items() if k not in children}, ('colors',), root_keys)
        for child, allowed in children.items():
            if child in color:
                if not table(color[child]):
                    raise ProfileError('Umbriel color subtable invalid')
                colors(color[child], ('colors', child), allowed)
    if 'layout' in src:
        if not table(src['layout']): raise ProfileError('layout must be a table')
        if strict and set(src['layout'].keys())-{'gap'}:
            raise ProfileError('Only [layout].gap is a visual profile setting')
        filter_keys({k:v for k,v in src['layout'].items() if k=='gap'},out,('layout',),{'gap'},strict)
    return out


def check_profile_files(root):
    allowed = {'profile.toml', 'noctalia.toml', 'umbriel.toml', 'workspace.toml',
               'README.md', 'preview.png'} | {base+suffix for base in ('wallpaper', 'lockscreen') for suffix in IMAGE_SUFFIXES}
    for path in root.iterdir():
        if path.is_symlink() or not path.is_file() or path.name not in allowed:
            raise ProfileError(f'Unsupported profile file/directory (no plugin configs or hooks): {path.name}')


def profile_ref(value):
    personal_base, default_base = PROFILE_ROOT.resolve(), DEFAULT_ROOT.resolve()
    if personal_base.is_relative_to(default_base) or default_base.is_relative_to(personal_base):
        raise ProfileError('Default and Personal storage must be separate')
    namespace, sep, name = value.partition(':')
    if not sep:
        name = value
        namespace = ('personal' if (PROFILE_ROOT/name).exists() or name not in OFFICIAL_DEFAULTS
                     else 'default')
    if namespace not in ('personal', 'default') or not ID.fullmatch(name):
        raise ProfileError('Use a valid ID or personal:ID/default:ID')
    return namespace, name


def profile_key(value):
    source, name = profile_ref(value)
    return source+':'+name


def personal_name(value):
    source, name = profile_ref(value)
    if source == 'default':
        raise ProfileError('Default profiles are immutable. Use Save As with a new Personal name.')
    return name


def manifest_for_folder(root, name):
    if root.is_symlink() or not root.is_dir():
        raise ProfileError(f'Profile not found: {name}')
    check_profile_files(root)
    man = parse(root/'profile.toml')
    if man.get('id') != name:
        raise ProfileError('Missing or mismatched profile id')
    if set(man) - {'id', 'name', 'description'}:
        raise ProfileError('Manifest contains unsupported metadata; imported metadata cannot grant Default status')
    return man


def verify_default(folder, name):
    expected = OFFICIAL_DEFAULTS.get(name)
    if expected is None:
        raise ProfileError('Not an official profile in this release catalogue')
    manifest_for_folder(folder, name)
    actual = {file.name: hashlib.sha256(file.read_bytes()).hexdigest() for file in folder.iterdir()}
    if actual != expected:
        raise ProfileError(f'Default {name} does not match the official release; reinstall trusted defaults')


def ensure_manifest(value):
    source, name = profile_ref(value)
    root = (DEFAULT_ROOT if source == 'default' else PROFILE_ROOT)/name
    man = manifest_for_folder(root, name)
    if source == 'default':
        verify_default(root, name)
    return root, man


def profiles():
    out = []
    for source, base in (('default', DEFAULT_ROOT), ('personal', PROFILE_ROOT)):
        if not base.exists():
            continue
        for folder in sorted(base.iterdir()):
            try:
                key = source+':'+folder.name
                _, manifest = ensure_manifest(key)
                out.append({'id':folder.name, 'name':str(manifest.get('name', folder.name)),
                            'source':source.title(), 'key':key})
            except (ProfileError, ValueError, OSError):
                pass
    return out



def effective_noctalia():
    override = os.environ.get('NDP_NOCTALIA_EXPORT_FILE')
    if override:
        return parse(Path(override))
    if not shutil.which('noctalia'):
        return None
    try:
        r = subprocess.run(['noctalia', 'config', 'export'], capture_output=True,
                           text=True, timeout=25, check=False)
        if r.returncode or not r.stdout.strip():
            return None
        merged = tomlkit.parse(r.stdout)
        # Some older versions lack full export; retain their merged format.
        full = subprocess.run(['noctalia', 'config', 'export', 'full'], capture_output=True,
                              text=True, timeout=25, check=False)
        if full.returncode == 0 and full.stdout.strip():
            result = tomlkit.parse(full.stdout)
            merge_fields(result, merged)
            return result
        return merged
    except (OSError, subprocess.TimeoutExpired, ValueError):
        return None


def is_mutable(wid, widget_defs):
    return bool(approved_widget(wid, widget_defs))


def protected_layout_context(current, widgets):
    """Freeze unresolved instances and every member shared with a protected capsule."""
    frozen = {wid for wid in widgets if approved_widget(wid, widgets) is None}
    all_groups = []
    for bar in section(current, 'bar').values():
        if not table(bar):
            continue
        contexts = [bar, *section(bar, 'monitor').values()]
        for context in contexts:
            if not table(context):
                continue
            for lane in BAR_SECTIONS:
                values = context.get(lane, [])
                if string_array(values):
                    frozen.update(wid for wid in values if not wid.startswith('group:')
                                  and approved_widget(wid, widgets) is None)
            try:
                all_groups.extend(group_index(context).values())
            except ProfileError:
                # A malformed context is refused by its planner/validator.
                continue
    while True:
        before = set(frozen)
        for group in all_groups:
            members = group.get('members', [])
            if string_array(members) and (not safe_group(group, widgets) or set(members) & frozen):
                frozen.update(members)
        if frozen == before:
            return frozen


def anchored_lane(old, desired, protected):
    """Insert protected tokens in their original order; retain indices when feasible."""
    result = []
    cursor = 0
    for index, token in enumerate(old):
        if protected(token):
            count = min(max(index - len(result), 0), len(desired) - cursor)
            result.extend(desired[cursor:cursor+count])
            cursor += count
            result.append(token)
    result.extend(desired[cursor:])
    return result


def plan_bar_layout(old, requested, widgets, profile_widgets, frozen):
    """Plan complete native lanes and capsules without altering protected containers.

    All dependent lanes/groups form one bar-layout transaction. Configuration
    definitions are retained when native placements are removed.
    """
    if set(requested) & set(BAR_SECTIONS) != set(BAR_SECTIONS):
        raise ProfileError('all three lanes are required for a layout transition')
    if any(not string_array(old.get(k, [])) or not string_array(requested[k]) for k in BAR_SECTIONS):
        raise ProfileError('invalid lane arrays')
    if any(table(m) and any(k in m for k in (*BAR_SECTIONS, 'capsule_group'))
           for m in section(old, 'monitor').values()):
        raise ProfileError('per-monitor layout overrides cannot be transformed safely')
    old_groups = group_index(old)
    incoming = group_index(requested)
    protected_groups = {gid for gid, group in old_groups.items()
                        if not safe_group(group, widgets) or set(group.get('members', [])) & frozen}
    unresolved_groups = {token[6:] for lane in BAR_SECTIONS for token in old.get(lane, [])
                         if token.startswith('group:') and token[6:] not in old_groups}

    def protected(token):
        if token.startswith('group:'):
            return token[6:] in unresolved_groups | protected_groups
        # New profile-owned native aliases have no current definition yet.
        # Only recipient-owned unresolved instances are frozen.
        return token in frozen

    def approve(wid):
        kind = approved_widget(wid, profile_widgets)
        if kind is None or wid in frozen:
            raise ProfileError(f'widget.{wid} is protected or belongs to a protected capsule')
        existing = approved_widget(wid, widgets)
        if (wid in widgets or existing is not None) and existing != kind:
            raise ProfileError(f'widget.{wid} has a conflicting resolved type')
        return kind

    used_groups = set()
    used_widgets = set()
    for lane in BAR_SECTIONS:
        for token in requested[lane]:
            if token.startswith('group:'):
                gid = token[6:]
                if gid in protected_groups | unresolved_groups:
                    raise ProfileError(f'group:{gid} skipped (reused ID has protected membership)')
                if gid not in incoming or not safe_group(incoming[gid], profile_widgets):
                    raise ProfileError(f'group:{gid} is missing or not an approved native capsule')
                if set(incoming[gid]) - (GROUP_KEYS | {'id', 'members'}):
                    raise ProfileError(f'group:{gid} contains unapproved settings')
                used_groups.add(gid)
                for member in incoming[gid]['members']:
                    approve(member)
                    used_widgets.add(member)
            else:
                approve(token)
                used_widgets.add(token)
    if set(incoming) != used_groups:
        raise ProfileError('unreferenced incoming capsule definitions')
    layouts = {lane: anchored_lane(list(old.get(lane, [])), list(requested[lane]), protected)
               for lane in BAR_SECTIONS}
    # Keep existing rows (including unused/unknown settings) in place. Only
    # native rows are patched; a fresh native ID can be appended safely.
    groups = copy.deepcopy(old.get('capsule_group', tomlkit.aot()))
    if not isinstance(groups, tomlkit.items.AoT):
        converted = tomlkit.aot()
        for group in groups:
            converted.append(copy.deepcopy(group))
        groups = converted
    planned_groups = {g['id']: g for g in groups}
    for gid in incoming:
        if gid not in planned_groups:
            entry = tomlkit.table()
            for key, value in incoming[gid].items():
                entry[key] = copy.deepcopy(value)
            groups.append(entry)
        else:
            entry = planned_groups[gid]
            for key, value in incoming[gid].items():
                if key != 'id' and entry.get(key) != value:
                    entry[key] = copy.deepcopy(value)
    # Prove protected lane/order/count and capsule rows survive before any write.
    for lane in BAR_SECTIONS:
        expected = [v for v in old.get(lane, []) if protected(v)]
        actual = [v for v in layouts[lane] if protected(v)]
        if actual != expected:
            raise ProfileError(f'protected {lane} placements would change')
    for gid in protected_groups:
        original = old_groups[gid]
        result = next(g for g in groups if g['id'] == gid)
        if result.unwrap() != original.unwrap() or result.as_string() != original.as_string():
            raise ProfileError(f'protected group:{gid} would change')
    return layouts, groups, used_widgets


def resolve_asset(value,folder):
    if not isinstance(value,str): raise ProfileError('Image path must be a string')
    if value.startswith(PORTABLE):
        name=value[len(PORTABLE):]
        if name not in ('wallpaper.png','wallpaper.jpg','wallpaper.jpeg','wallpaper.webp','wallpaper.bmp',
                        'lockscreen.png','lockscreen.jpg','lockscreen.jpeg','lockscreen.webp','lockscreen.bmp'):
            raise ProfileError('Profile asset name is not permitted')
        path=folder/name
        if path.is_symlink() or not path.is_file(): raise ProfileError('Missing profile wallpaper: '+name)
        return str(path.resolve())
    if value=='' or re.fullmatch(r'color:#[a-fA-F0-9]{6}(?:[a-fA-F0-9]{2})?',value):
        return value
    raise ProfileError('Wallpaper paths must use bundled @profile/ assets or color:#RRGGBB')


def prepare_profile(name):
    folder, _ = ensure_manifest(name)
    return read_profile_folder(folder)


def read_profile_folder(folder):
    npath=folder/'noctalia.toml'; upath=folder/'umbriel.toml'; wpath=folder/'workspace.toml'
    if not npath.is_file() and not upath.is_file() and not wpath.is_file(): raise ProfileError('Profile contains no appearance settings')
    n=clean_noctalia(parse(npath),True) if npath.exists() else tomlkit.document()
    u=clean_umbriel(parse(upath),True) if upath.exists() else tomlkit.document()
    w=clean_workspace(parse(wpath),True) if wpath.exists() else tomlkit.document()
    for path in (('wallpaper','default','path'),('lockscreen','wallpaper')):
        cur=section(n,*path[:-1])
        if path[-1] in cur: put(n,path,resolve_asset(cur[path[-1]],folder))
    return n,u,w


def merge_fields(dst, src, path=()):
    for k, v in src.items():
        if table(v):
            merge_fields(dst, v, (*path, k))
        else:
            put(dst, (*path, k), v)


PROPAGATION_OPTION = '--allow-noctalia-propagation'
PROPAGATION_NOTICE = ('WARNING: Noctalia propagation explicitly allowed for this operation: existing templates may rewrite application configs and existing hooks may execute commands; '
                      'Dotprofile preserves their configuration and cannot undo those external effects')


def noctalia_propagation_sources(current):
    """Read recipient-owned configuration without enabling/disabling anything."""
    sources = []
    templates = section(current, 'theme', 'templates')
    for category in ('builtin', 'community'):
        if templates.get(category+'_ids') and templates.get('enable_'+category+'_templates', True):
            sources.append(f'enabled {category} templates')
    user = templates.get('user', {})
    if user and (not table(user) or any(not table(entry) or entry.get('enabled', True)
                                      for entry in user.values())):
        sources.append('enabled user templates')
    if set(templates) - {'builtin_ids', 'community_ids', 'enable_builtin_templates',
                         'enable_community_templates', 'user'}:
        sources.append('unrecognized template configuration')
    hooks = section(current, 'hooks')
    known_hooks = {'started', 'session_locked', 'session_unlocked', 'logging_out',
                   'rebooting', 'shutting_down', 'wifi_enabled', 'wifi_disabled',
                   'bluetooth_enabled', 'bluetooth_disabled', 'battery_charging',
                   'battery_discharging', 'battery_plugged', 'battery_percentage_changed',
                   'power_profile_changed', 'colors_changed', 'theme_mode_changed', 'wallpaper_changed'}
    if any(hooks.get(k) for k in ('colors_changed', 'theme_mode_changed', 'wallpaper_changed')):
        sources.append('color/theme/wallpaper hooks')
    if any(v for k, v in hooks.items() if k not in known_hooks):
        sources.append('unrecognized hook events')
    return sources


def patch_noctalia(live, profile, effective, allow_noctalia_propagation=False):
    note = []
    # Defense in depth: opting in to the recipient's propagation never allows
    # profile-supplied automation configuration through this merge boundary.
    if 'templates' in section(profile, 'theme') or 'hooks' in profile:
        raise ProfileError('Profiles cannot change theme templates or hooks')
    current = copy.deepcopy(effective if effective is not None else live)
    sources = noctalia_propagation_sources(current)
    if allow_noctalia_propagation:
        note.append(PROPAGATION_NOTICE)
    for name in ('theme', 'wallpaper', 'lockscreen', 'shell'):
        if name in profile:
            changed = any(section(current, name).get(k) != v for k, v in profile[name].items())
            # Reapplying the same default still changes live monitor choices
            # through IPC, so it must pass the propagation guard again.
            if name == 'wallpaper' and section(profile, 'wallpaper', 'default').get('path'):
                changed = True
            if name in ('theme', 'wallpaper') and changed and sources and not allow_noctalia_propagation:
                note.append(f'{name} skipped (Noctalia propagation blocked: {", ".join(sources)}; existing templates may rewrite application configs and hooks may execute commands; '
                            f'review them before explicitly opting in with {PROPAGATION_OPTION})')
                continue
            merge_fields(live, profile[name], (name,))
    bars = section(current, 'bar')
    widgets = section(current, 'widget')
    profile_widgets = section(profile, 'widget')
    frozen = protected_layout_context(current, widgets)
    matched_widgets = set()
    creatable_widgets = set()
    for name, values in section(profile, 'bar').items():
        target = name
        if name not in bars:
            targets = [k for k in bar_names(bars) if table(bars.get(k))]
            if len(targets) == 1 and len(section(profile, 'bar')) == 1:
                target = targets[0]
                note.append(f'bar.{name} mapped to existing bar.{target}')
            else:
                note.append(f'bar.{name} skipped (no unambiguous existing bar)')
                continue
        old = bars[target]
        if not table(old):
            note.append(f'bar.{target} layout skipped (existing bar is not a table)')
            continue
        try:
            old_references = referenced_widgets(old)
            protected = any(wid in frozen or approved_widget(wid, widgets) is None
                            for context in [old, *section(old, 'monitor').values()] if table(context)
                            for wid in referenced_widgets(context)) or any(
                                token.startswith('group:') and token[6:] not in group_index(old)
                                for lane in BAR_SECTIONS for token in old.get(lane, []))
        except ProfileError as error:
            note.append(f'bar.{target} skipped (unsafe existing layout: {error})')
            continue
        overridden = {key for monitor in section(old, 'monitor').values() if table(monitor)
                      for key in BAR_KEYS & set(values) & set(monitor) if monitor[key] != values[key]}
        if overridden:
            note.append(f'bar.{target} recipient monitor overrides retained '
                        f'(profile fields may not apply on matching monitors: {", ".join(sorted(overridden))})')
        for key, value in values.items():
            if key in BAR_KEYS:
                if key == 'enabled' and protected and old.get(key, True) != value:
                    note.append(f'bar.{target}.enabled skipped (would hide/reveal protected widgets)')
                    continue
                put(live, ('bar', target, key), value)
        matched_widgets.update(old_references)
        if any(key in values for key in BAR_SECTIONS):
            try:
                layouts, groups, accepted = plan_bar_layout(old, values, widgets, profile_widgets, frozen)
                for lane in BAR_SECTIONS:
                    if (lane not in section(live, 'bar', target)
                            and list(old.get(lane, [])) != layouts[lane]
                            and any(wid.startswith('group:') or wid in frozen or approved_widget(wid, widgets) is None
                                    for wid in old.get(lane, []))):
                        raise ProfileError('protected lower-layer layout cannot be relocated to GUI overrides')
                groups_changed = groups != old.get('capsule_group', [])
                if groups_changed and old.get('capsule_group') and 'capsule_group' not in section(live, 'bar', target):
                    raise ProfileError('lower-layer capsule array cannot be relocated safely')
                if groups_changed and 'capsule_group' in section(live, 'bar', target):
                    # The effective export can normalize/add defaults to rows.
                    # Patch source-native rows only, preserving protected rows'
                    # exact configuration, comments, and ownership in this file.
                    groups = copy.deepcopy(live['bar'][target]['capsule_group'])
                    local_index = group_index({'capsule_group': groups})
                    if set(local_index) != set(group_index(old)):
                        raise ProfileError('capsule definitions span ambiguous configuration layers')
                    for gid, props in group_index(values).items():
                        if gid not in local_index:
                            groups.append(copy.deepcopy(props))
                        else:
                            for key, value in props.items():
                                if key != 'id' and local_index[gid].get(key) != value:
                                    local_index[gid][key] = copy.deepcopy(value)
            except ProfileError as error:
                note.append(f'bar.{target} widget slots skipped (layout transition skipped: {error})')
                continue
            for lane, result in layouts.items():
                if list(old.get(lane, [])) != result:
                    put(live, ('bar', target, lane), result)
            if groups_changed:
                put(live, ('bar', target, 'capsule_group'), groups)
            matched_widgets.update(accepted)
            creatable_widgets.update(accepted)
    # Keep definitions for removed native placements: other bars, unapproved
    # settings, and future switches can still depend on those same IDs.
    for wid, props in profile_widgets.items():
        kind = approved_widget(wid, profile_widgets)
        existing = approved_widget(wid, widgets)
        if wid in frozen:
            note.append(f'widget.{wid} skipped (protected instance/capsule)')
            continue
        new_instance = wid not in widgets and existing is None and wid in creatable_widgets
        if wid not in matched_widgets or kind is None or not (new_instance or existing == kind):
            note.append(f'widget.{wid} skipped (no compatible native instance or accepted layout)')
            continue
        if new_instance:
            put(live, ('widget', wid, 'type'), kind)
        for key, value in props.items():
            if key != 'type' and section(current, 'widget', wid).get(key) != value:
                put(live, ('widget', wid, key), value)
    return note


def patch_umbriel(live,profile):
    def merge(src,path):
        for key,val in src.items():
            if table(val): merge(val,(*path,key))
            else: put(live,(*path,key),val)
    merge(profile,())


def atomic_write(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(prefix='.dotprofile-',dir=path.parent)
    try:
        with os.fdopen(fd,'w',encoding='utf8') as fp:
            fp.write(data); fp.flush(); os.fsync(fp.fileno())
        os.chmod(tmp,0o600)
        os.replace(tmp,path)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)


def backup_file(src,dst):
    if src.is_symlink(): raise ProfileError(f'Symlinked live config refused: {src}')
    if src.exists(): shutil.copy2(src,dst)
    else: (dst.with_suffix('.absent')).touch()


def restore_file(src,dst):
    if src.with_suffix('.absent').exists():
        dst.unlink(missing_ok=True)
    elif src.exists(): atomic_write(dst,src.read_text(encoding='utf8'))
    else: raise ProfileError('Incomplete backup')


def validate(noctalia_path=None, umbriel_path=None):
    ncmd = ['noctalia', 'config', 'validate']
    if noctalia_path is not None:
        ncmd.append(str(noctalia_path))
    for cmd in (ncmd, ['umbriel', 'config', 'validate', '-c', str(umbriel_path or UMBRIEL_FILE)]):
        if not shutil.which(cmd[0]):
            raise ProfileError(f'Cannot validate {cmd[0]}: executable not installed')
        try:
            r=subprocess.run(cmd,text=True,capture_output=True,timeout=30,check=False)
        except (OSError,subprocess.TimeoutExpired) as e: raise ProfileError(f'{cmd[0]} validation error: {e}') from e
        if r.returncode: raise ProfileError(f'{cmd[0]} validation failed: {(r.stderr or r.stdout)[-1200:]}')


def reload():
    failed=[]
    for cmd in (['noctalia','msg','config-reload'],['umbriel','msg','config-reload']):
        if not shutil.which(cmd[0]): continue
        try:
            r=subprocess.run(cmd,timeout=12,capture_output=True,text=True,check=False)
            if r.returncode: failed.append(cmd[0])
        except (OSError,subprocess.TimeoutExpired): failed.append(cmd[0])
    return failed


def wallpaper_request(profile, effective, allow_noctalia_propagation):
    """An explicit accepted image/color always needs IPC, even on reapplication."""
    path = section(profile, 'wallpaper', 'default').get('path')
    if not path or (noctalia_propagation_sources(effective) and not allow_noctalia_propagation):
        return None
    if not isinstance(path, str) or ('\n' in path or '\r' in path or '\x00' in path):
        raise ProfileError('Invalid wallpaper IPC path')
    if path.startswith('color:'):
        if not re.fullmatch(r'color:#[a-fA-F0-9]{6}(?:[a-fA-F0-9]{2})?', path):
            raise ProfileError('Invalid wallpaper color')
    else:
        image = Path(path).expanduser()
        if not image.is_absolute():
            raise ProfileError('Wallpaper image path must be absolute; no wallpaper IPC sent')
        if not image.is_file():
            raise ProfileError('Wallpaper image is missing; no wallpaper IPC sent')
        path = str(image)
    return path


def wallpaper_set(path):
    """Use Noctalia's all-connected-monitor command; never enumerate outputs."""
    try:
        result = subprocess.run(['noctalia', 'msg', 'wallpaper-set', path],
                                capture_output=True, text=True, timeout=20, check=False)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise ProfileError(f'Wallpaper IPC failed: {error}') from error
    if result.returncode:
        detail = (result.stderr or result.stdout).strip()[-1200:]
        raise ProfileError(f'Wallpaper IPC failed (exit {result.returncode}): {detail}')


def wallpaper_ipc_write(expected, observed, requested):
    """Recognize ONLY normal IPC path persistence, never unrelated config edits.

    Noctalia also persists wallpaper.last.path and connected monitor paths.
    Formatting alone is harmless; every other value must remain identical.
    """
    missing = object()

    def permitted(old, new, path=()):
        if old == new:
            return True
        if path in (('wallpaper', 'default', 'path'), ('wallpaper', 'last', 'path')) or (
                len(path) == 4 and path[:2] == ('wallpaper', 'monitors') and path[-1] == 'path'):
            return new == requested
        if isinstance(new, dict) and (isinstance(old, dict) or old is missing):
            if old is missing and not new:
                return False
            previous = {} if old is missing else old
            return all(permitted(previous.get(k, missing), new.get(k, missing), (*path, k))
                       for k in previous.keys() | new.keys())
        return False

    try:
        return permitted(tomlkit.parse(expected).unwrap(), tomlkit.parse(observed).unwrap())
    except (ValueError, TypeError):
        return False


def apply_wallpaper_ipc(path, before, data, changes):
    """Track authorized shell writes so ordinary failure rollback can recover them."""
    if any(file_bytes(file) != (data[i].encode('utf8') if changes[i] else before[i])
           for i, file in enumerate((NOCTALIA_FILE, UMBRIEL_FILE))):
        raise ProfileError('Desktop configuration changed before wallpaper IPC; no command sent')
    error = None
    try:
        wallpaper_set(path)
    except Exception as failure:
        # A timeout/nonzero reply may follow a partial, persisted application.
        error = failure
    observed = file_bytes(NOCTALIA_FILE)
    if observed != data[0].encode('utf8'):
        changes[0] = True
        try:
            text = observed.decode('utf8') if observed is not None else ''
        except UnicodeError:
            text = ''
        if observed is None or not wallpaper_ipc_write(data[0], text, path):
            raise ProfileError('Wallpaper IPC left unexpected/concurrent configuration changes; '
                               'protected edits retained; configuration rollback may be skipped') from error
        data[0] = text
        changes[0] = observed != before[0]
    if error is not None:
        raise error


WALLPAPER_RECOVERY_NOTICE = ('Live wallpapers may have changed, including after a timeout; '
    'configuration recovery does not guarantee restoration of displayed monitor images. '
    'External template/hook effects cannot be rolled back by Dotprofile')


def locked():
    STATE_ROOT.mkdir(parents=True,exist_ok=True)
    f=(STATE_ROOT/'.lock').open('a+')
    fcntl.flock(f.fileno(),fcntl.LOCK_EX)
    return f


def validate_candidates(n, u, effective):
    """Native validators run offline against candidates, never reload them."""
    candidate = copy.deepcopy(effective) if effective is not None else tomlkit.document()
    merge_fields(candidate, n)
    compositor = copy.deepcopy(u)
    # Resolve only the validation copy's existing includes relative to the
    # original file, so staging in /tmp does not lose split config files.
    for names in (('include',), ('include', 'optional')):
        inc = section(compositor, *names)
        if string_array(inc.get('files')):
            inc['files'] = [str((UMBRIEL_FILE.parent / Path(v).expanduser()).resolve()) for v in inc['files']]
    with tempfile.TemporaryDirectory(prefix='dotprofile-validate-') as temp:
        npath = Path(temp) / 'noctalia.toml'
        upath = Path(temp) / 'umbriel.toml'
        npath.write_text(tomlkit.dumps(candidate), encoding='utf8')
        upath.write_text(tomlkit.dumps(compositor), encoding='utf8')
        # TOML syntax is checked even where native validators are unavailable.
        parse(npath); parse(upath)
        validate(npath, upath)


def file_bytes(path):
    return path.read_bytes() if path.exists() else None


def appearance_snapshot(src):
    result = clean_noctalia(src)
    for keys in (('wallpaper', 'default', 'path'), ('lockscreen', 'wallpaper')):
        value = section(src, *keys[:-1]).get(keys[-1])
        if isinstance(value, str):
            put(result, keys, value)
    return result


def restore_candidates(backup, live_n, live_u, effective, allow_noctalia_propagation=False):
    npath = backup/'noctalia-appearance.toml'
    if not npath.exists():
        npath = backup/'noctalia.toml'
    snapshot_n = parse(npath)
    snapshot_u = parse(backup/'umbriel.toml')
    notes = patch_noctalia(live_n, appearance_snapshot(snapshot_n), effective, allow_noctalia_propagation)
    patch_umbriel(live_u, clean_umbriel(snapshot_u))
    notes += patch_workspace_names(live_u, extract_workspaces(snapshot_u))
    if not snapshot_n:
        notes.append('Noctalia appearance skipped (backup has no configuration; current plugins/config retained)')
    if not (backup/'noctalia-appearance.toml').exists():
        notes.append('legacy snapshot: appearance fields absent from the backup are retained for safety')
    return notes


def rollback_configs(backup, before, data, changes):
    """Never replace a file containing an edit made after our staged write."""
    notes = []
    for i, (path, filename) in enumerate(((NOCTALIA_FILE, 'noctalia.toml'), (UMBRIEL_FILE, 'umbriel.toml'))):
        if not changes[i]:
            continue
        now = file_bytes(path)
        if now == before[i]:
            continue
        if now != data[i].encode('utf8'):
            notes.append(f'rollback skipped {path}: changed externally; protected data retained')
            continue
        try:
            restore_file(backup/filename, path)
        except (OSError, ProfileError) as error:
            notes.append(f'rollback failed {path}: {error}; recovery snapshot retained')
    return notes


def apply(name, dry=False, allow_noctalia_propagation=False):
    selection = profile_key(name)
    def plan():
        n, u, w = prepare_profile(name)
        before = (file_bytes(NOCTALIA_FILE), file_bytes(UMBRIEL_FILE))
        old_n = parse(NOCTALIA_FILE); old_u = parse(UMBRIEL_FILE)
        eff = effective_noctalia()
        if n and eff is None:
            raise ProfileError('Noctalia effective export unavailable; cannot resolve protected aliases safely')
        notes = patch_noctalia(old_n, n, eff, allow_noctalia_propagation)
        patch_umbriel(old_u, u)
        notes += patch_workspace_names(old_u, w)
        validate_candidates(old_n, old_u, eff)
        data = (tomlkit.dumps(old_n), tomlkit.dumps(old_u))
        changes = tuple(before[i] != data[i].encode('utf8') and not (before[i] is None and not data[i]) for i in range(2))
        if not (n or u or w):
            raise ProfileError('Profile contains no settings')
        request = wallpaper_request(n, eff, allow_noctalia_propagation)
        if request:
            notes.append('wallpaper IPC: wallpaper-set for all connected monitors after validation and backup')
        elif 'path' in section(n, 'wallpaper', 'default') and not section(n, 'wallpaper', 'default')['path']:
            notes.append('live wallpaper skipped (empty path has no supported wallpaper-set target)')
        return before, data, changes, notes, eff, request

    if dry:
        _, _, changes, notes, _, _ = plan()
        targets = ', '.join(str(path) for path, changed in zip((NOCTALIA_FILE, UMBRIEL_FILE), changes) if changed) or 'no file changes'
        return f'VALID {name}: would update {targets}; backup before writes; ' + ('; '.join(notes) or 'protected settings kept')
    with locked():
        before, data, changes, notes, eff, request = plan()
        data, changes = list(data), list(changes)
        if not any(changes) and not request:
            return f'Unchanged {name}; ' + ('; '.join(notes) or 'already matches')
        backup = STATE_ROOT/'backups'/(time.strftime('%Y%m%d-%H%M%S')+'-'+str(time.time_ns()))
        backup.mkdir(parents=True, mode=0o700)
        backup_file(NOCTALIA_FILE, backup/'noctalia.toml')
        backup_file(UMBRIEL_FILE, backup/'umbriel.toml')
        if eff is not None:
            atomic_write(backup/'noctalia-appearance.toml', tomlkit.dumps(appearance_snapshot(eff)))
        active = STATE_ROOT/'active-profile'
        backup_file(active, backup/'active-profile')
        # Our lock serializes engine writes, but cannot lock the GUI. Abort if
        # a user edit arrived while resolving aliases or validating candidates.
        if before != (file_bytes(NOCTALIA_FILE), file_bytes(UMBRIEL_FILE)):
            raise ProfileError('Desktop configuration changed during preparation; retry')
        try:
            for path, changed, content in zip((NOCTALIA_FILE, UMBRIEL_FILE), changes, data):
                if changed:
                    atomic_write(path, content)
            validate()
            failed = reload()
            if failed:
                raise ProfileError('Reload failed: '+','.join(failed)+'; restoring previous configuration')
            if request:
                apply_wallpaper_ipc(request, before, data, changes)
                validate()
            atomic_write(active, selection+'\n')
        except Exception as error:
            warnings = rollback_configs(backup, before, data, changes)
            if file_bytes(active) in (None, (selection+'\n').encode('utf8')):
                restore_file(backup/'active-profile', active)
            recovery_failed = reload()
            if recovery_failed:
                warnings.append('Recovery reload failed: '+','.join(recovery_failed))
            if request:
                warnings.append(WALLPAPER_RECOVERY_NOTICE)
            elif allow_noctalia_propagation:
                warnings.append('External template/hook effects cannot be rolled back by Dotprofile')
            if warnings:
                raise ProfileError(f'{error}; ' + '; '.join(warnings) + f'; recovery snapshot: {backup.name}') from error
            raise
        return f'Applied {name}. Recovery backup: {backup.name}' + ('; '+'; '.join(notes) if notes else '')


def restore(id, dry=False, allow_noctalia_propagation=False):
    if not ID.fullmatch(id) and not re.fullmatch(r'\d{8}-\d{6}-\d+', id):
        raise ProfileError('Invalid backup name')
    backup = STATE_ROOT/'backups'/id
    if backup.is_symlink() or not backup.is_dir() or any(p.is_symlink() for p in backup.rglob('*')):
        raise ProfileError('Backup is missing or contains symlinks')
    for filename in ('noctalia.toml', 'umbriel.toml', 'active-profile'):
        path = backup/filename
        if not path.exists() and not path.with_suffix('.absent').exists():
            raise ProfileError('Incomplete backup')

    def plan():
        before = (file_bytes(NOCTALIA_FILE), file_bytes(UMBRIEL_FILE))
        current_n = parse(NOCTALIA_FILE); current_u = parse(UMBRIEL_FILE)
        effective = effective_noctalia()
        if effective is None:
            raise ProfileError('Noctalia effective export unavailable; cannot restore appearance while protecting aliases')
        notes = restore_candidates(backup, current_n, current_u, effective, allow_noctalia_propagation)
        validate_candidates(current_n, current_u, effective)
        data = (tomlkit.dumps(current_n), tomlkit.dumps(current_u))
        changes = tuple(before[i] != data[i].encode('utf8') and not (before[i] is None and not data[i]) for i in range(2))
        appearance_path = backup/'noctalia-appearance.toml'
        if not appearance_path.exists():
            appearance_path = backup/'noctalia.toml'
        appearance = appearance_snapshot(parse(appearance_path))
        request = wallpaper_request(appearance, effective, allow_noctalia_propagation)
        if request:
            notes.append('wallpaper IPC: wallpaper-set for all connected monitors after validation and backup')
        elif 'path' in section(appearance, 'wallpaper', 'default') and not section(appearance, 'wallpaper', 'default')['path']:
            notes.append('live wallpaper skipped (empty path has no supported wallpaper-set target)')
        return before, data, changes, notes, effective, request

    if dry:
        _, _, _, notes, _, _ = plan()
        return f'VALID backup {id}: restore approved appearance only; all current plugin settings/installations/placements kept; ' + ('; '.join(notes) or 'compatible appearance')
    with locked():
        before, data, changes, notes, effective, request = plan()
        data, changes = list(data), list(changes)
        recover = STATE_ROOT/'backups'/(time.strftime('%Y%m%d-%H%M%S')+'-'+str(time.time_ns()))
        recover.mkdir(parents=True, mode=0o700)
        backup_file(NOCTALIA_FILE, recover/'noctalia.toml')
        backup_file(UMBRIEL_FILE, recover/'umbriel.toml')
        atomic_write(recover/'noctalia-appearance.toml', tomlkit.dumps(appearance_snapshot(effective)))
        active = STATE_ROOT/'active-profile'
        old_active = file_bytes(active)
        backup_file(active, recover/'active-profile')
        if before != (file_bytes(NOCTALIA_FILE), file_bytes(UMBRIEL_FILE)):
            raise ProfileError('Desktop configuration changed during restoration preparation; retry')
        try:
            for path, changed, content in zip((NOCTALIA_FILE, UMBRIEL_FILE), changes, data):
                if changed:
                    atomic_write(path, content)
            validate()
            failed = reload()
            if failed:
                raise ProfileError('Reload failed: '+','.join(failed))
            if request:
                apply_wallpaper_ipc(request, before, data, changes)
                validate()
            restore_file(backup/'active-profile', active)
        except Exception as error:
            warnings = rollback_configs(recover, before, data, changes)
            restored_marker = file_bytes(backup/'active-profile')
            if file_bytes(active) in (old_active, restored_marker, None):
                restore_file(recover/'active-profile', active)
            recovery_failed = reload()
            if recovery_failed:
                warnings.append('Recovery reload failed: '+','.join(recovery_failed))
            if request:
                warnings.append(WALLPAPER_RECOVERY_NOTICE)
            elif allow_noctalia_propagation:
                warnings.append('External template/hook effects cannot be rolled back by Dotprofile')
            if warnings:
                raise ProfileError(f'{error}; '+'; '.join(warnings)+f'; recovery snapshot: {recover.name}') from error
            raise
        return 'Restored appearance '+id+'; current plugin settings/installations/placements retained' + ('; '+'; '.join(notes) if notes else '')


def portable_wallpaper(source,dest,basename,include):
    if not isinstance(source,str) or not source: return None if source else ''
    if source.startswith('color:#'): return source
    if not include: return None
    p=Path(source).expanduser()
    if p.is_symlink() or not p.is_file() or p.suffix.lower() not in IMAGE_SUFFIXES or p.stat().st_size>30_000_000:
        raise ProfileError('Wallpaper is missing, symlinked, unsupported, or larger than 30MB')
    dst=dest/(basename+p.suffix.lower())
    shutil.copyfile(p,dst)
    return PORTABLE+dst.name


def export_current_appearance(name, root, eff, include_wallpaper):
    n=clean_noctalia(eff)
    current_umbriel=parse(UMBRIEL_FILE)
    u=clean_umbriel(current_umbriel)
    w=extract_workspaces(current_umbriel)
    root.mkdir(parents=True)
    try:
        # Source paths are intentionally stripped from the portable TOML.
        # Access the raw effective config only to copy images when explicitly
        # requested; never write the old home path into profile files.
        for keys, base in ((('wallpaper','default','path'), 'wallpaper'),
                           (('lockscreen','wallpaper'), 'lockscreen')):
            original = section(eff, *keys[:-1]).get(keys[-1])
            if original is None:
                continue
            result = portable_wallpaper(original, root, base, include_wallpaper)
            # Remove any source absolute paths already present in export.
            parent = section(n, *keys[:-1])
            if keys[-1] in parent:
                del parent[keys[-1]]
            if result is not None:
                put(n, keys, result)
        manifest=tomlkit.document(); manifest['id']=name;manifest['name']=name.replace('-',' ').title()
        manifest['description']='Appearance profile including safe 1–5 workspace indicators (no plugins/templates/hooks/app configs/keybindings/hardware)'
        atomic_write(root/'profile.toml',tomlkit.dumps(manifest))
        atomic_write(root/'noctalia.toml',tomlkit.dumps(n.unwrap()))
        atomic_write(root/'umbriel.toml',tomlkit.dumps(u.unwrap()))
        if w: atomic_write(root/'workspace.toml',tomlkit.dumps(w.unwrap()))
        # Validate our own strict import contract before declaring success.
        manifest_for_folder(root, name)
        read_profile_folder(root)
    except Exception:
        shutil.rmtree(root)
        raise
    return bool(w)


def profile_backup(folder, operation):
    stamp = time.strftime('%Y%m%d-%H%M%S')+'-'+str(time.time_ns())
    archive = STATE_ROOT/'profile-backups'/folder.name/stamp
    archive.mkdir(parents=True, mode=0o700)
    shutil.copytree(folder, archive/folder.name, symlinks=False)
    atomic_write(archive/'operation.txt', operation+'\n')
    return archive/folder.name


def require_confirmation(confirmed, operation):
    if not confirmed:
        raise ProfileError(f'{operation} requires explicit confirmation (--confirm); a Personal-profile backup will be saved')


def publish_personal(staged, name, overwrite=False, confirmed=False):
    """Only the Personal namespace can be published/replaced by this path."""
    profile_ref('personal:'+name)
    dest = PROFILE_ROOT/name
    if dest.is_symlink():
        raise ProfileError('Symlinked Personal profile refused')
    if not dest.exists():
        os.replace(staged, dest)
        return None
    if not overwrite:
        raise ProfileError('Personal profile exists; use Save As or --overwrite --confirm')
    require_confirmation(confirmed, 'Overwrite')
    manifest_for_folder(dest, name)
    read_profile_folder(dest)
    archive = profile_backup(dest, 'overwrite')
    holding = dest.parent/('.previous-'+name+'-'+str(time.time_ns()))
    os.replace(dest, holding)
    try:
        os.replace(staged, dest)
    except Exception:
        os.replace(holding, dest)
        raise
    shutil.rmtree(holding)
    return archive


def save(value, include_wallpaper=False, overwrite=False, confirmed=False):
    name = personal_name(value)
    active = STATE_ROOT/'active-profile'
    if active.exists() and active.read_text().strip() == 'default:'+name:
        raise ProfileError('Save As requires a new name after customizing a Default profile')
    if name in OFFICIAL_DEFAULTS and not (PROFILE_ROOT/name).exists():
        raise ProfileError('Save As requires a new Personal name; this name identifies a Default profile')
    with locked():
        dest = PROFILE_ROOT/name
        if dest.exists():
            if not overwrite:
                raise ProfileError('Personal profile exists; use Save As or --overwrite --confirm')
            require_confirmation(confirmed, 'Overwrite')
        eff = effective_noctalia()
        if eff is None:
            raise ProfileError('Noctalia config export unavailable; inspect configuration/CLI errors before saving')
        PROFILE_ROOT.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='.save-', dir=PROFILE_ROOT) as temp:
            staged = Path(temp)/name
            labels = export_current_appearance(name, staged, eff, include_wallpaper)
            archive = publish_personal(staged, name, overwrite, confirmed)
    return 'Saved Personal '+name+' to '+str(dest)+('; 5 workspace labels captured' if labels else '; workspace names NOT captured (requires valid, consistent static five-workspace outputs)')+('; wallpaper files bundled' if include_wallpaper else '; wallpaper images omitted (use --include-wallpaper if licensed)')+('; prior Personal profile backup: '+str(archive) if archive else '')


def install_profile(folder, overwrite=False, confirmed=False):
    raw = Path(folder).expanduser()
    if raw.is_symlink():
        raise ProfileError('Profile source is a symlink')
    source = raw.resolve(strict=True)
    name = source.name
    if not ID.fullmatch(name):
        raise ProfileError('Invalid source directory')
    manifest_for_folder(source, name)
    read_profile_folder(source)
    profile_ref('personal:'+name)
    with locked():
        PROFILE_ROOT.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='.import-', dir=PROFILE_ROOT) as temp:
            staged = Path(temp)/name
            shutil.copytree(source, staged, symlinks=False)
            for file in staged.iterdir():
                file.chmod(0o600)
            manifest_for_folder(staged, name)
            read_profile_folder(staged)
            archive = publish_personal(staged, name, overwrite, confirmed)
    return 'Installed Personal '+name+'; not yet applied'+('; prior Personal profile backup: '+str(archive) if archive else '')


def export_profile(value, directory):
    folder, manifest = ensure_manifest(value)
    read_profile_folder(folder)
    parent = Path(directory).expanduser()
    dest = parent/manifest['id']
    if parent.is_symlink() or dest.exists() or dest.is_symlink():
        raise ProfileError('Export destination exists or is symlinked; choose a new directory')
    # Never export over any managed library location, even via path aliases.
    for base in (DEFAULT_ROOT, PROFILE_ROOT, STATE_ROOT):
        if dest.resolve().is_relative_to(base.resolve()):
            raise ProfileError('Export must target a directory outside managed profile storage')
    parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.export-', dir=parent) as temp:
        staged = Path(temp)/manifest['id']
        shutil.copytree(folder, staged, symlinks=False)
        for file in staged.iterdir():
            file.chmod(0o600)
            if file.suffix == '.toml':
                atomic_write(file, tomlkit.dumps(parse(file).unwrap()))
        manifest_for_folder(staged, manifest['id']); read_profile_folder(staged)
        os.replace(staged, dest)
    return 'Exported '+profile_key(value)+' to '+str(dest)+'; exported copies import as Personal'


def rename_profile(value, new_value, confirmed=False):
    name = personal_name(value)
    new_name = personal_name(new_value)
    require_confirmation(confirmed, 'Rename')
    if name == new_name:
        raise ProfileError('Choose a different Personal name')
    with locked():
        folder, _ = ensure_manifest('personal:'+name)
        read_profile_folder(folder)
        dest = PROFILE_ROOT/new_name
        if dest.exists() or dest.is_symlink():
            raise ProfileError('Rename destination already exists; no profile was changed')
        archive = profile_backup(folder, 'rename')
        original = (folder/'profile.toml').read_text()
        manifest = parse(folder/'profile.toml')
        manifest['id'] = new_name
        manifest['name'] = new_name.replace('-', ' ').title()
        os.replace(folder, dest)
        try:
            atomic_write(dest/'profile.toml', tomlkit.dumps(manifest))
        except Exception:
            os.replace(dest, folder)
            atomic_write(folder/'profile.toml', original)
            raise
        active = STATE_ROOT/'active-profile'
        if active.exists() and active.read_text().strip() in (name, 'personal:'+name):
            atomic_write(active, 'personal:'+new_name+'\n')
    return f'Renamed Personal {name} to {new_name}; backup: {archive}; desktop unchanged'


def delete_profile(value, confirmed=False):
    name = personal_name(value)
    require_confirmation(confirmed, 'Delete')
    with locked():
        folder, _ = ensure_manifest('personal:'+name)
        read_profile_folder(folder)
        archive = profile_backup(folder, 'delete')
        # Remove only a validated Personal package after keeping a full copy.
        shutil.rmtree(folder)
        active = STATE_ROOT/'active-profile'
        if active.exists() and active.read_text().strip() in (name, 'personal:'+name):
            atomic_write(active, 'none\n')
    return f'Deleted Personal {name}; backup: {archive}; desktop unchanged'


def install_defaults(directory):
    """The only Default write path accepts exact release-owned file digests."""
    source = Path(directory).expanduser()
    if source.is_symlink() or not source.is_dir():
        raise ProfileError('Official default source is missing or symlinked')
    for name in OFFICIAL_DEFAULTS:
        verify_default(source/name, name)
        read_profile_folder(source/name)
    if {path.name for path in source.iterdir()} != set(OFFICIAL_DEFAULTS):
        raise ProfileError('Unlisted data in official release source; no defaults installed')
    with locked():
        if DEFAULT_ROOT.is_symlink() or DEFAULT_ROOT.resolve() == PROFILE_ROOT.resolve() or DEFAULT_ROOT.resolve().is_relative_to(PROFILE_ROOT.resolve()):
            raise ProfileError('Default storage must be separate from Personal storage and not symlinked')
        DEFAULT_ROOT.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='.defaults-', dir=DEFAULT_ROOT) as temp:
            staging = Path(temp)
            for name in OFFICIAL_DEFAULTS:
                shutil.copytree(source/name, staging/name, symlinks=False)
                verify_default(staging/name, name)
            replaced = []
            try:
                for name in OFFICIAL_DEFAULTS:
                    dest = DEFAULT_ROOT/name
                    if dest.is_symlink():
                        raise ProfileError('Symlinked Default profile refused')
                    holding = staging/('previous-'+name)
                    if dest.exists():
                        manifest_for_folder(dest, name); read_profile_folder(dest)
                        os.replace(dest, holding)
                    replaced.append((dest, holding))
                    os.replace(staging/name, dest)
                    for file in dest.iterdir():
                        file.chmod(0o444)
            except Exception:
                for dest, holding in reversed(replaced):
                    if dest.exists():
                        shutil.rmtree(dest)
                    if holding.exists():
                        os.replace(holding, dest)
                raise
    return 'Installed trusted Default profiles; Personal profiles and running desktop unchanged'



def cli():
    p=argparse.ArgumentParser(description='Portable TUI desktop appearance profile engine')
    p.add_argument('--version', action='version', version='Dotprofile '+VERSION)
    sub=p.add_subparsers(dest='command',required=True)
    listing=sub.add_parser('list');listing.add_argument('--labels',action='store_true')
    sub.add_parser('status'); sub.add_parser('backups');sub.add_parser('profile-backups')
    a=sub.add_parser('apply');a.add_argument('profile');a.add_argument('--dry-run',action='store_true')
    s=sub.add_parser('save');s.add_argument('profile');s.add_argument('--include-wallpaper',action='store_true');s.add_argument('--overwrite',action='store_true');s.add_argument('--confirm',action='store_true')
    r=sub.add_parser('restore');r.add_argument('backup');r.add_argument('--dry-run',action='store_true')
    i=sub.add_parser('install-profile');i.add_argument('directory');i.add_argument('--overwrite',action='store_true');i.add_argument('--confirm',action='store_true')
    e=sub.add_parser('export');e.add_argument('profile');e.add_argument('directory')
    rename=sub.add_parser('rename');rename.add_argument('profile');rename.add_argument('new_name');rename.add_argument('--confirm',action='store_true')
    delete=sub.add_parser('delete');delete.add_argument('profile');delete.add_argument('--confirm',action='store_true')
    defaults=sub.add_parser('install-defaults');defaults.add_argument('directory')
    for command in (a, r):
        command.add_argument(PROPAGATION_OPTION, action='store_true',
                             help='Opt in for this operation only: Noctalia may run existing hooks and rewrite app configs using existing templates; template/hook settings remain protected, and external effects cannot be rolled back')
    opts=p.parse_args()
    try:
        if opts.command in ('apply', 'restore') and opts.allow_noctalia_propagation and not opts.dry_run:
            print(PROPAGATION_NOTICE, file=sys.stderr)
        if opts.command=='list': print('\n'.join(x['source']+': '+x['id'] if opts.labels else x['key'] for x in profiles()))
        elif opts.command=='backups': print('\n'.join(p.name for p in sorted((STATE_ROOT/'backups').iterdir(),reverse=True) if p.is_dir()) if (STATE_ROOT/'backups').exists() else '')
        elif opts.command=='status':
            f=STATE_ROOT/'active-profile';print(f.read_text().strip() if f.exists() else 'none')
        elif opts.command=='apply': print(apply(opts.profile,opts.dry_run,opts.allow_noctalia_propagation))
        elif opts.command=='save':print(save(opts.profile,opts.include_wallpaper,opts.overwrite,opts.confirm))
        elif opts.command=='restore':print(restore(opts.backup,opts.dry_run,opts.allow_noctalia_propagation))
        elif opts.command=='install-profile':print(install_profile(opts.directory,opts.overwrite,opts.confirm))
        elif opts.command=='export':print(export_profile(opts.profile,opts.directory))
        elif opts.command=='rename':print(rename_profile(opts.profile,opts.new_name,opts.confirm))
        elif opts.command=='delete':print(delete_profile(opts.profile,opts.confirm))
        elif opts.command=='install-defaults':print(install_defaults(opts.directory))
        elif opts.command=='profile-backups':
            base=STATE_ROOT/'profile-backups'
            print('\n'.join(str(path) for path in sorted(base.glob('*/*/*')) if path.is_dir()) if base.exists() else '')
        return 0
    except (ProfileError,OSError,ValueError,TypeError,subprocess.SubprocessError) as e:
        print('ERROR: '+str(e),file=sys.stderr);return 1

if __name__=='__main__':raise SystemExit(cli())

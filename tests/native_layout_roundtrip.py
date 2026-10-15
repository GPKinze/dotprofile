#!/usr/bin/env python3
"""Offline integration against installed validators and synthetic configurations.

Writes exclusively to a TemporaryDirectory; reload is replaced with a no-op.
The running desktop and profile library are never targets of an engine write.
"""
import itertools
import os
import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch

from test_layout_switching import LayoutTests, fixture, p, MAIN


def run():
    for command in ('noctalia', 'umbriel'):
        if not shutil.which(command):
            raise SystemExit(f'{command} is required for native offline integration')
    check = LayoutTests()
    operations = 0
    with tempfile.TemporaryDirectory(prefix='dotprofile-layout-native-') as name:
        temp = Path(name)
        config, state = temp/'config', temp/'desktop-state'
        (config/'noctalia').mkdir(parents=True)
        (state/'noctalia').mkdir(parents=True)
        udir = temp/'umbriel'
        udir.mkdir()
        nfile, ufile = state/'noctalia/settings.toml', udir/'config.toml'
        nfile.write_text(MAIN+'\n[wallpaper.default]\npath=""\n')
        ufile.write_text('[appearance]\nborder_width=2\n')
        library = temp/'profiles'
        library.mkdir()
        environment = {'NOCTALIA_CONFIG_HOME': str(config), 'NOCTALIA_STATE_HOME': str(state),
                       'NDP_NOCTALIA_EXPORT_FILE': ''}
        with patch.dict(os.environ, environment), patch.multiple(
                p, PROFILE_ROOT=library, DEFAULT_ROOT=temp/'defaults', STATE_ROOT=temp/'manager-state',
                NOCTALIA_FILE=nfile, UMBRIEL_FILE=ufile), patch.object(p, 'reload', return_value=[]), patch.object(p, 'wallpaper_set', side_effect=AssertionError('Live wallpaper IPC prohibited during offline layout tests')):
            effective = p.effective_noctalia()
            if effective is None:
                raise AssertionError('isolated native export unavailable')
            protected = check.plugins(effective)
            u_before = ufile.read_bytes()
            for profile in ('layout-a','layout-b'):
                folder = library/profile
                folder.mkdir()
                (folder/'profile.toml').write_text(f'id="{profile}"\nname="{profile}"\n')
                (folder/'noctalia.toml').write_text(p.tomlkit.dumps(fixture(profile)))
            snapshots = []
            for profile in ('layout-a','layout-b','layout-a','layout-b'):
                message = p.apply(profile, dry=True)
                if 'layout transition skipped' in message:
                    raise AssertionError(message)
                old_backups = set((p.STATE_ROOT/'backups').iterdir()) if (p.STATE_ROOT/'backups').exists() else set()
                message = p.apply(profile)
                snapshots.append((set((p.STATE_ROOT/'backups').iterdir()) - old_backups).pop())
                if 'layout transition skipped' in message:
                    raise AssertionError(message)
                actual = p.effective_noctalia()
                check.assert_native_layout(actual, fixture(profile))
                check.assert_native_layout(p.parse(nfile), fixture(profile))
                check.assertEqual(check.plugins(actual), protected)
                check.assertEqual(ufile.read_bytes(), u_before)
                operations += 1
            # Restore both explicit and automatic radii through actual native
            # validation/export. IPC remains prohibited throughout the runner.
            for snapshot, profile in ((snapshots[3], 'layout-a'), (snapshots[2], 'layout-b'),
                                      (snapshots[1], 'layout-a'), (snapshots[2], 'layout-b')):
                message = p.restore(snapshot.name)
                if 'layout transition skipped' in message:
                    raise AssertionError(message)
                actual = p.effective_noctalia()
                check.assert_native_layout(actual, fixture(profile))
                check.assert_native_layout(p.parse(nfile), fixture(profile))
                check.assertEqual(check.plugins(actual), protected)
                check.assertEqual(ufile.read_bytes(), u_before)
                operations += 1
            # Save and recover each starting position. Every pair exercises a
            # different native group ID/membership, dimensions, and styling.
            for source, target in itertools.permutations(('top','bottom','left','right'), 2):
                current = p.parse(nfile)
                current['bar']['Main']['position'] = source
                nfile.write_text(p.tomlkit.dumps(current))
                saved = f'source-{source}-{target}'
                p.save(saved)
                desired = fixture('layout-b')
                bar = desired['bar']['Main']
                desired['widget']['clock']['vertical_format'] = '%H\n%M'
                bar.update({'position': target, 'thickness': 48, 'margin_ends': 80,
                            'margin_edge': 8, 'margin_opposite_edge': 12, 'padding': 10,
                            'widget_spacing': 4, 'background_opacity': 0.75,
                            'border_width': 2.0, 'capsule_thickness': 0.8, 'concave_edge_corners': False})
                bar['capsule_group'][0]['id'] = 'v' if target in ('left','right') else 'h'
                bar['center'] = ['group:'+bar['capsule_group'][0]['id']]
                folder = library/f'target-{source}-{target}'
                folder.mkdir()
                (folder/'profile.toml').write_text(f'id="{folder.name}"\nname="offline test"\n')
                (folder/'noctalia.toml').write_text(p.tomlkit.dumps(desired))
                message = p.apply(folder.name)
                if 'layout transition skipped' in message:
                    raise AssertionError(message)
                actual = p.effective_noctalia()
                check.assert_native_layout(actual, desired)
                check.assertEqual(check.plugins(actual), protected)
                operations += 1
                expected = p.prepare_profile(saved)[0]
                message = p.apply(saved)
                if 'layout transition skipped' in message:
                    raise AssertionError(message)
                actual = p.effective_noctalia()
                check.assert_native_layout(actual, expected)
                check.assertEqual(check.plugins(actual), protected)
                operations += 1
            # Restoration uses the same transition planner and native validation.
            p.save('restore-baseline')
            expected = p.prepare_profile('restore-baseline')[0]
            old_backups = set((p.STATE_ROOT/'backups').iterdir())
            p.apply('layout-b')
            backup = (set((p.STATE_ROOT/'backups').iterdir()) - old_backups).pop()
            p.restore(backup.name)
            check.assert_native_layout(p.effective_noctalia(), expected)
            check.assertEqual(check.plugins(p.effective_noctalia()), protected)
            check.assertEqual(ufile.read_bytes(), u_before)
            operations += 2
            # Real-schema mixed capsule rows keep their original source text
            # while normalized effective exports drive native group changes.
            local = p.parse(nfile)
            rows = local['bar']['Main']['capsule_group']
            rows.append(p.tomlkit.parse('[[capsule_group]]\nid="private" # preserve source row\nmembers=["status","bar","recorder_2"]\n')['capsule_group'][0])
            local['bar']['Main']['end'] = [v for v in local['bar']['Main']['end'] if v not in ('status','bar','recorder_2')]
            local['bar']['Main']['center'].append('group:private')
            nfile.write_text(p.tomlkit.dumps(local))
            raw_group = rows[-1].as_string()
            mixed_protected = check.plugins(p.effective_noctalia())
            for profile in ('layout-b','layout-a'):
                message = p.apply(profile)
                if 'layout transition skipped' in message:
                    raise AssertionError(message)
                check.assert_native_layout(p.effective_noctalia(), fixture(profile))
                check.assertEqual(check.plugins(p.effective_noctalia()), mixed_protected)
                check.assertEqual(p.group_index(p.parse(nfile)['bar']['Main'])['private'].as_string(), raw_group)
                operations += 1
    print(f'PASS: {operations} isolated native apply/restore operations; 12 position pairs; desktop reload suppressed; synthetic temporary configs only')


if __name__ == '__main__':
    run()

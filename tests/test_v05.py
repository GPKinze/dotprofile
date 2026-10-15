import copy
import os
import shutil
import subprocess
import tomllib
import unittest
from unittest.mock import patch
import test_profilectl as legacy
UMBRIEL, p, ROOT = legacy.UMBRIEL, legacy.p, legacy.ROOT

MAIN = (ROOT/'tests/fixtures/main-bar.toml').read_text()


class V05Tests(unittest.TestCase):
    setUp = legacy.ProfileTests.setUp
    make = legacy.ProfileTests.make
    def main(self, source=MAIN):
        self.nfile.write_text(source)
        p.effective_noctalia.return_value = p.tomlkit.parse(source)
        return p.effective_noctalia.return_value

    def exported(self, source=MAIN):
        return p.clean_noctalia(p.tomlkit.parse(source))

    def test_synthetic_main_export_and_aot_valid_roundtrip(self):
        source = self.main()
        p.save('layout-a')
        profile, _, workspace = p.prepare_profile('layout-a')
        raw = (self.root/'layout-a/noctalia.toml').read_text()
        plain = tomllib.loads(raw)
        self.assertIn('[bar.Main]', raw)
        self.assertIn('[[bar.Main.capsule_group]]', raw)
        self.assertEqual(plain['bar']['Main']['center'], ['group:g1'])
        self.assertEqual(plain['bar']['Main']['end'], ['bracket_open', 'volume', 'notifications', 'tray', 'bracket_close'])
        self.assertEqual(plain['bar']['Main']['start'], ['bracket_open', 'launcher', 'workspaces', 'bracket_close'])
        group = plain['bar']['Main']['capsule_group'][0]
        self.assertEqual(group['id'], 'g1')
        self.assertEqual(group['members'], ['clock', 'audio_visualizer', 'weather'])
        self.assertEqual(group['border_width'], 1.5)
        for wid in ('workspaces', 'bracket_open', 'bracket_close', 'launcher', 'volume', 'notifications', 'tray', 'weather'):
            self.assertIn(f'[widget.{wid}]', raw)
        self.assertEqual(list(workspace['workspace_indicator']['labels']), ['一','二','三','四','五'])
        for bad in ('plugin_settings', '[plugins]', 'fixture-vendor/', 'screen_recorder', 'status', 'recorder_2', '[widget.bar]'):
            self.assertNotIn(bad, raw)
        self.assertEqual(p.clean_noctalia(profile, True).unwrap(), profile.unwrap())
        before = copy.deepcopy(source)
        candidate = copy.deepcopy(source)
        self.assertFalse(p.patch_noctalia(candidate, profile, source))
        self.assertEqual(candidate.unwrap(), before.unwrap())
        p.apply('layout-a')
        applied = p.parse(self.nfile)
        self.assertEqual(applied['bar']['Main'].unwrap(), before['bar']['Main'].unwrap())
        self.assertEqual(applied['plugins'].unwrap(), before['plugins'].unwrap())
        self.assertEqual(applied['plugin_settings'].unwrap(), before['plugin_settings'].unwrap())
        self.assertEqual(p.parse(self.ufile)['keybinds'].unwrap(), p.tomlkit.parse(UMBRIEL)['keybinds'].unwrap())

    def test_duplicate_text_refs_reorder_plugin_absolute_positions(self):
        live = self.main()
        profile = self.exported()
        profile['bar']['Main']['end'] = ['bracket_close', 'tray', 'volume', 'notifications', 'bracket_open']
        original = list(live['bar']['Main']['end'])
        p.patch_noctalia(live, profile, copy.deepcopy(live))
        after = list(live['bar']['Main']['end'])
        for wid in ('status', 'bar', 'recorder_2'):
            self.assertEqual(after.index(wid), original.index(wid))
        self.assertEqual(after, ['bracket_close', 'status', 'bar', 'tray', 'recorder_2', 'volume', 'notifications', 'bracket_open'])
        self.assertEqual(list(live['bar']['Main']['start']), ['bracket_open','launcher','workspaces','bracket_close'])

    def test_native_name_alias_resolves_unknown_plugin(self):
        source = MAIN + '\n[widget.clock]\ntype="unknown/vendor:plugin"\nsecret="private"\n'
        profile = self.exported(source)
        text = p.tomlkit.dumps(profile)
        self.assertNotIn('group:g1', text)
        self.assertNotIn('capsule_group', text)
        self.assertNotIn('unknown/vendor', text)
        live = self.main(source)
        before = copy.deepcopy(live['bar']['Main']['capsule_group'])
        clean = self.exported()
        notes = p.patch_noctalia(live, clean, copy.deepcopy(live))
        self.assertTrue(any('protected membership' in n for n in notes))
        self.assertEqual(live['bar']['Main']['capsule_group'], before)
        self.assertEqual(live['widget']['clock']['secret'], 'private')

    def test_plugin_alias_impersonating_launcher_excluded(self):
        source = MAIN.replace('glyph = "app-window"', 'type="new/plugin:evil"\nprivate="dont-export"')
        doc = self.exported(source)
        self.assertNotIn('launcher', p.tomlkit.dumps(doc))
        live = self.main(source)
        snapshot = copy.deepcopy(live)
        notes = p.patch_noctalia(live, self.exported(), snapshot)
        self.assertTrue(any('skipped' in n for n in notes))
        self.assertEqual(live['bar']['Main']['start'], snapshot['bar']['Main']['start'])
        self.assertEqual(live['widget']['launcher'], snapshot['widget']['launcher'])

    def test_group_with_plugin_membership_never_exported_or_modified(self):
        source = MAIN.replace('"clock", "audio_visualizer", "weather"', '"clock", "status", "weather"')
        live = self.main(source)
        before = copy.deepcopy(live)
        doc = self.exported(source)
        self.assertEqual(list(doc['bar']['Main']['center']), [])
        self.assertNotIn('capsule_group', doc['bar']['Main'])
        p.patch_noctalia(live, doc, before)
        self.assertEqual(live['bar']['Main']['center'], before['bar']['Main']['center'])
        self.assertEqual(live['bar']['Main']['capsule_group'], before['bar']['Main']['capsule_group'])

    def test_safe_group_reorder_style_preserves_unknown_properties(self):
        source = MAIN.replace('radius = 5.0', 'radius = 5.0\nfuture_setting = "keep"')
        live = self.main(source)
        doc = self.exported(source)
        group = doc['bar']['Main']['capsule_group'][0]
        group['members'] = ['weather', 'clock', 'audio_visualizer']
        group['radius'] = 9.0
        p.patch_noctalia(live, doc, copy.deepcopy(live))
        result = live['bar']['Main']['capsule_group'][0]
        self.assertEqual(list(result['members']), ['weather','clock','audio_visualizer'])
        self.assertEqual(result['radius'], 9.0)
        self.assertEqual(result['future_setting'], 'keep')

    def test_missing_native_capsule_and_placement_created_safely(self):
        source = MAIN.replace('center = ["group:g1"]', 'center = ["clock"]')
        a = source.index('[[bar.Main.capsule_group]]')
        b = source.index('[theme]', a)
        source = source[:a] + source[b:]
        source = source.replace('"launcher", ', '')
        live = self.main(source)
        before = copy.deepcopy(live)
        notes = p.patch_noctalia(live, self.exported(), before)
        self.assertFalse(notes)
        self.assertEqual(list(live['bar']['Main']['center']), ['group:g1'])
        self.assertIn('launcher', live['bar']['Main']['start'])
        self.assertEqual(list(live['bar']['Main']['capsule_group'][0]['members']),
                         ['clock','audio_visualizer','weather'])
        self.assertEqual(live['widget'], before['widget'])

    def test_unique_bar_name_mapping_and_multibar_ambiguity(self):
        live = self.main(MAIN.replace('Main', 'Panel'))
        notes = p.patch_noctalia(live, self.exported(), copy.deepcopy(live))
        self.assertTrue(any('mapped to existing bar.Panel' in n for n in notes))
        self.assertNotIn('Main', live['bar'])
        live['bar']['Second'] = p.tomlkit.table()
        before = copy.deepcopy(live)
        notes = p.patch_noctalia(live, self.exported(), before)
        self.assertTrue(any('no unambiguous' in n for n in notes))
        self.assertEqual(live['bar'], before['bar'])

    def test_discovery_order_case_and_legacy_unlisted_bars(self):
        source = '[bar]\norder=["Z", "Main"]\n[bar.Main]\nradius=3\n[bar.Z]\nradius=4\n[bar.extra]\nradius=5\n'
        doc = self.exported(source)
        self.assertEqual(list(doc['bar']), ['Z','Main','extra'])
        self.assertNotIn('order', doc['bar'])

    def test_capsule_malformed_and_action_injection_rejected(self):
        for bad in ('id="g1"\nmembers=["clock"]\ncommand="exec bad"',
                    'id="g1"\nmembers=["status"]', 'id="g1"\nmembers=["group:g1"]'):
            source = '[bar.Main]\ncenter=["group:g1"]\n[[bar.Main.capsule_group]]\n'+bad+'\n'
            with self.assertRaises(p.ProfileError):
                p.clean_noctalia(p.tomlkit.parse(source), True)
        source = '[bar.Main.capsule_group.g1]\nmembers=["clock"]'
        with self.assertRaises(p.ProfileError):
            self.exported(source)

    def test_cross_lane_movement_and_duplicate_removal_preserve_plugins(self):
        protected = {'status','bar','recorder_2'}
        for change in ('cross', 'duplicate'):
            with self.subTest(change=change):
                live = self.main()
                doc = self.exported()
                if change == 'cross':
                    doc['bar']['Main']['start'] = ['bracket_open','launcher','bracket_close']
                    doc['bar']['Main']['end'].append('workspaces')
                else:
                    doc['bar']['Main']['end'] = ['volume','notifications','tray','bracket_close']
                old = copy.deepcopy(live)
                notes = p.patch_noctalia(live, doc, old)
                self.assertFalse(notes)
                for lane in p.BAR_SECTIONS:
                    self.assertEqual([v for v in live['bar']['Main'][lane] if v not in protected],
                                     list(doc['bar']['Main'][lane]))
                    self.assertEqual([v for v in live['bar']['Main'][lane] if v in protected],
                                     [v for v in old['bar']['Main'][lane] if v in protected])
                for wid in protected:
                    self.assertEqual(live['widget'][wid], old['widget'][wid])

    def test_built_in_alias_appearance_and_no_action_exports(self):
        source = MAIN.replace('"volume",', '"loudness",') + '\n[widget.loudness]\ntype="volume"\nfont_scale=1.2\n[widget.loudness.actions]\nleft="exec secret"\n'
        doc = self.exported(source)
        self.assertEqual(doc['widget']['loudness']['type'], 'volume')
        self.assertEqual(doc['widget']['loudness']['font_scale'], 1.2)
        self.assertNotIn('actions', doc['widget']['loudness'])
        live = self.main(source)
        doc['widget']['loudness']['font_scale'] = 1.4
        p.patch_noctalia(live, doc, copy.deepcopy(live))
        self.assertEqual(live['widget']['loudness']['font_scale'], 1.4)
        self.assertEqual(live['widget']['loudness']['actions']['left'], 'exec secret')

    def test_staged_validator_failure_has_no_live_writes(self):
        self.make()
        before = self.nfile.read_bytes(), self.ufile.read_bytes()
        with patch.object(p, 'validate', side_effect=p.ProfileError('invalid candidate')):
            with self.assertRaises(p.ProfileError):
                p.apply('test')
        self.assertEqual(before, (self.nfile.read_bytes(), self.ufile.read_bytes()))
        self.assertFalse((self.state/'backups').exists())
        p.reload.assert_not_called()

    def test_post_write_validation_failure_rolls_back_and_keeps_active(self):
        self.make()
        self.state.mkdir()
        (self.state/'active-profile').write_text('previous\n')
        before = self.nfile.read_bytes(), self.ufile.read_bytes()
        with patch.object(p, 'validate', side_effect=[None, p.ProfileError('post-write failed')]):
            with self.assertRaises(p.ProfileError):
                p.apply('test')
        self.assertEqual(before, (self.nfile.read_bytes(), self.ufile.read_bytes()))
        self.assertEqual((self.state/'active-profile').read_text(), 'previous\n')
        self.assertEqual(len(list((self.state/'backups').iterdir())), 1)

    def test_second_write_failure_rolls_back_both_configs(self):
        self.make()
        original = p.atomic_write
        before = self.nfile.read_bytes(), self.ufile.read_bytes()
        count = 0
        def fail_once(path, data):
            nonlocal count
            if path in (self.nfile, self.ufile):
                count += 1
            if count == 2 and path in (self.nfile, self.ufile):
                raise OSError('simulated storage error')
            return original(path, data)
        with patch.object(p, 'atomic_write', side_effect=fail_once):
            with self.assertRaises(OSError):
                p.apply('test')
        self.assertEqual(before, (self.nfile.read_bytes(), self.ufile.read_bytes()))

    def test_no_effective_export_refuses_import_without_alias_resolution(self):
        self.make()
        p.effective_noctalia.return_value = None
        before = self.nfile.read_bytes()
        with self.assertRaises(p.ProfileError):
            p.apply('test')
        self.assertEqual(before, self.nfile.read_bytes())

    def test_gui_edit_during_validation_aborts_without_overwriting(self):
        self.make()
        def edit(*args):
            self.nfile.write_text(self.nfile.read_text()+'\n# concurrent GUI change\n')
        p.validate.side_effect = edit
        with self.assertRaises(p.ProfileError):
            p.apply('test')
        self.assertIn('concurrent GUI change', self.nfile.read_text())
        p.reload.assert_not_called()

    def test_theme_templates_hooks_guard_preserves_app_automation(self):
        live = self.main(MAIN+'\n[theme.templates]\nbuiltin_ids=["kitty"]\n')
        doc = self.exported()
        doc['theme']['mode'] = 'light'
        before = copy.deepcopy(live)
        notes = p.patch_noctalia(live, doc, before)
        self.assertEqual(live['theme'], before['theme'])
        self.assertTrue(any('theme skipped' in n for n in notes))
        self.assertNotIn('templates', doc['theme'])

    def test_invalid_and_conflicting_workspace_names_not_exported(self):
        live = p.tomlkit.parse(UMBRIEL)
        live['output']['Other'] = {'workspaces': ['a','b','c','d','e']}
        self.assertFalse(p.extract_workspaces(live))
        live = p.tomlkit.parse(UMBRIEL.replace('"二"', '"一"'))
        self.assertFalse(p.extract_workspaces(live))
        before = copy.deepcopy(live)
        notes = p.patch_workspace_names(live, p.tomlkit.parse('[workspace_indicator]\nlabels=["1","2","3","4","5"]'))
        self.assertTrue(notes)
        self.assertEqual(live, before)

    def test_unknown_colors_and_nonfinite_scalar_rejected(self):
        for text in ('[colors]\nprivate="#112233"', '[colors.border]\ncommand="#112233"'):
            with self.assertRaises(p.ProfileError):
                p.clean_umbriel(p.tomlkit.parse(text), True)
        with self.assertRaises(p.ProfileError):
            p.clean_noctalia(p.tomlkit.parse('[bar.Main]\nradius=nan'), True)

    def test_validate_uses_installed_umbriel_command(self):
        self.validate.stop()
        with patch.object(p.shutil, 'which', return_value='/usr/bin/program'), patch.object(p.subprocess, 'run') as run:
            run.return_value.returncode = 0
            p.validate()
            self.assertEqual(run.call_args_list[1].args[0], ['umbriel','config','validate','-c',str(self.ufile)])
        self.validate.start()

    def test_export_defaults_and_user_asset_paths_both_retained(self):
        self.pc.stop()
        merged = '[wallpaper.default]\npath="/some/wall.png"\n'
        full = '[shell.animation]\nenabled=true\nspeed=1.0\n'
        with patch.object(p.shutil, 'which', return_value='/usr/bin/noctalia'), patch.object(p.subprocess, 'run') as run:
            run.side_effect = [subprocess.CompletedProcess([],0,merged), subprocess.CompletedProcess([],0,full)]
            result = p.effective_noctalia()
        self.assertEqual(result['wallpaper']['default']['path'], '/some/wall.png')
        self.assertTrue(result['shell']['animation']['enabled'])
        self.pc.start()

    def test_lower_layer_plugin_layout_and_capsules_not_relocated(self):
        effective = self.main()
        gui = p.tomlkit.parse('[theme]\nmode="dark"\n')
        doc = self.exported()
        doc['bar']['Main']['end'] = ['bracket_close','volume','notifications','tray','bracket_open']
        doc['bar']['Main']['capsule_group'][0]['radius'] = 8
        notes = p.patch_noctalia(gui, doc, effective)
        self.assertNotIn('end', gui['bar']['Main'])
        self.assertNotIn('capsule_group', gui['bar']['Main'])
        self.assertTrue(any('widget slots skipped' in n for n in notes))
        self.assertTrue(any('lower-layer' in n for n in notes))

    def test_monitor_layout_overrides_and_disabled_plugin_bar_skipped(self):
        source = MAIN+'\n[bar.Main.monitor.TEST-OUTPUT-1]\nend=["status","clock"]\n'
        live = self.main(source)
        doc = self.exported()
        doc['bar']['Main']['end'] = ['bracket_close','volume','notifications','tray','bracket_open']
        doc['bar']['Main']['enabled'] = False
        before = copy.deepcopy(live)
        notes = p.patch_noctalia(live, doc, before)
        self.assertEqual(live['bar']['Main']['end'], before['bar']['Main']['end'])
        self.assertEqual(live['bar']['Main']['monitor'], before['bar']['Main']['monitor'])
        self.assertNotIn('enabled', live['bar']['Main'])
        self.assertTrue(any('enabled skipped' in n for n in notes))

    def test_minimum_workspaces_over_five_incompatible(self):
        live = p.tomlkit.parse(UMBRIEL)
        live['output']['TEST-OUTPUT-1']['min_workspaces'] = 7
        self.assertFalse(p.extract_workspaces(live))
        before = copy.deepcopy(live)
        labels = p.tomlkit.parse('[workspace_indicator]\nlabels=["1","2","3","4","5"]')
        self.assertTrue(p.patch_workspace_names(live, labels))
        self.assertEqual(live, before)

    def test_root_symlink_profile_source_rejected(self):
        source = self.make()
        shortcut = self.base/'alias'
        shortcut.symlink_to(source, target_is_directory=True)
        with self.assertRaises(p.ProfileError):
            p.install_profile(shortcut)

    def test_malformed_section_shapes_clear_error(self):
        for text in ('shell=3', 'wallpaper="bad"', 'bar=[]', 'widget=[]'):
            with self.assertRaises(p.ProfileError):
                p.clean_noctalia(p.tomlkit.parse(text), True)
        for text in ('appearance=3', 'animation=[]', 'layout="bad"'):
            with self.assertRaises(p.ProfileError):
                p.clean_umbriel(p.tomlkit.parse(text), True)


    def test_restoration_keeps_new_unknown_plugin_settings_and_placements(self):
        self.main()
        p.save('test')
        (self.root/'test/noctalia.toml').write_text((self.root/'test/noctalia.toml').read_text().replace('radius = 16', 'radius = 14'))
        p.apply('test')
        backup = next((self.state/'backups').iterdir())
        current = p.parse(self.nfile)
        current['plugins']['enabled'].append('future/vendor')
        current['plugin_settings']['future/vendor'] = {'credential': 'keep-current'}
        current['widget']['launcher']['type'] = 'future/vendor:launcher'
        current['widget']['launcher']['secret'] = 'keep-alias'
        current['bar']['Main']['start'] = ['bracket_open','workspaces','launcher','bracket_close']
        current['bar']['Main']['capsule_group'][0]['members'] = ['weather','launcher','clock']
        current['widget']['status']['future_setting'] = 'new-value'
        current['plugin_settings']['fixture-vendor/operation']['battery_display'] = 'new-format'
        self.nfile.write_text(p.tomlkit.dumps(current))
        p.effective_noctalia.return_value = copy.deepcopy(current)
        before = copy.deepcopy(current)
        old_u = p.parse(self.ufile)
        old_u['keybinds']['Mod+1'] = 'keep-new-keybinding'
        self.ufile.write_text(p.tomlkit.dumps(old_u))
        report = p.restore(backup.name, True)
        self.assertIn('all current plugin', report)
        self.assertEqual(self.nfile.read_text(), p.tomlkit.dumps(before))
        report = p.restore(backup.name)
        self.assertIn('retained', report)
        after = p.parse(self.nfile)
        self.assertEqual(after['plugins'], before['plugins'])
        self.assertEqual(after['plugin_settings'], before['plugin_settings'])
        for wid in ('launcher', 'bar', 'status', 'recorder_2'):
            self.assertEqual(after['widget'][wid], before['widget'][wid])
        self.assertEqual(after['bar']['Main']['start'], before['bar']['Main']['start'])
        self.assertEqual(after['bar']['Main']['capsule_group'], before['bar']['Main']['capsule_group'])
        self.assertEqual(after['bar']['Main']['radius'], 16)
        self.assertEqual(p.parse(self.ufile)['keybinds']['Mod+1'], 'keep-new-keybinding')

    def test_restoration_never_reinstalls_removed_plugin(self):
        self.main()
        p.save('test')
        (self.root/'test/noctalia.toml').write_text((self.root/'test/noctalia.toml').read_text().replace('radius = 16', 'radius = 14'))
        p.apply('test')
        backup = next((self.state/'backups').iterdir())
        current = p.parse(self.nfile)
        del current['widget']['status']
        del current['plugin_settings']['fixture-vendor/operation']
        current['plugins']['enabled'] = ['fixture-vendor/recording']
        current['bar']['Main']['end'] = [w for w in current['bar']['Main']['end'] if w != 'status']
        self.nfile.write_text(p.tomlkit.dumps(current))
        p.effective_noctalia.return_value = copy.deepcopy(current)
        p.restore(backup.name)
        after = p.parse(self.nfile)
        self.assertNotIn('status', after['widget'])
        self.assertNotIn('status', after['bar']['Main']['end'])
        self.assertNotIn('fixture-vendor/operation', after['plugin_settings'])
        self.assertEqual(list(after['plugins']['enabled']), ['fixture-vendor/recording'])

    def test_legacy_snapshot_restores_appearance_only_and_keeps_plugins(self):
        self.make()
        p.apply('test')
        backup = next((self.state/'backups').iterdir())
        (backup/'noctalia-appearance.toml').unlink()
        current = p.parse(self.nfile)
        current['widget']['phone']['my_secret_setting'] = 'current-value'
        self.nfile.write_text(p.tomlkit.dumps(current))
        p.effective_noctalia.return_value = copy.deepcopy(current)
        output = p.restore(backup.name)
        self.assertIn('legacy snapshot', output)
        after = p.parse(self.nfile)
        self.assertEqual(after['widget']['phone']['my_secret_setting'], 'current-value')
        self.assertEqual(after['bar']['main']['thickness'], 34)

    def test_rollback_never_overwrites_concurrent_plugin_edit(self):
        self.make()
        calls = 0
        def validate(*args):
            nonlocal calls
            calls += 1
            if calls == 2:
                current = p.parse(self.nfile)
                current['widget']['phone']['my_secret_setting'] = 'changed-during-apply'
                self.nfile.write_text(p.tomlkit.dumps(current))
                raise p.ProfileError('post-write failure')
        p.validate.side_effect = validate
        with self.assertRaisesRegex(p.ProfileError, 'rollback skipped'):
            p.apply('test')
        self.assertEqual(p.parse(self.nfile)['widget']['phone']['my_secret_setting'], 'changed-during-apply')
        self.assertEqual(self.ufile.read_text(), UMBRIEL)

    def test_reload_failure_restores_previous_appearance(self):
        self.make()
        before = self.nfile.read_bytes(), self.ufile.read_bytes()
        p.reload.side_effect = [['noctalia'], []]
        with self.assertRaisesRegex(p.ProfileError, 'Reload failed'):
            p.apply('test')
        self.assertEqual(before, (self.nfile.read_bytes(), self.ufile.read_bytes()))

    def test_compositor_only_profile_does_not_create_unrelated_config(self):
        self.make(n='')
        self.nfile.unlink()
        p.apply('test')
        self.assertFalse(self.nfile.exists())


    def test_plugin_sidecar_file_not_imported(self):
        folder = self.make()
        (folder/'plugin-settings.toml').write_text('token="private"\n')
        target = self.base/'new-library'
        with patch.object(p, 'PROFILE_ROOT', target):
            with self.assertRaisesRegex(p.ProfileError, 'no plugin configs'):
                p.install_profile(folder)
        self.assertFalse(target.exists())


class InstallerTests(unittest.TestCase):
    def setUp(self):
        import tempfile
        from pathlib import Path
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.home = self.base/'install-home'
        self.root = self.home/'.local/share/dotprofile'
        self.bin = self.home/'.local/bin'
        self.tools = self.base/'tools'
        self.tools.mkdir()
        for name in ('gum', 'pacman', 'sudo'):
            file = self.tools/name
            file.write_text('#!/bin/sh\necho "Unexpected dependency/menu invocation" >&2\nexit 91\n')
            file.chmod(0o755)
        self.env = dict(os.environ, DOTPROFILE_INSTALL_HOME=str(self.home), PATH=str(self.tools)+os.pathsep+os.environ['PATH'])
        self.root.joinpath('engine').mkdir(parents=True)
        self.bin.mkdir(parents=True)
        self.root.joinpath('engine/profilectl.py').write_text('print("OLD ENGINE")\n')
        self.bin.joinpath('dotprofile').write_text('#!/bin/sh\necho OLD TUI\n')
        self.root.joinpath('profiles/keep').mkdir(parents=True)
        self.root.joinpath('profiles/keep/profile.toml').write_text('id="keep"\n')

    def run_install(self, option):
        return subprocess.run(['bash', str(ROOT/'install.sh'), option], env=self.env, capture_output=True, text=True)

    def test_upgrade_preserves_profiles_and_backs_up_both_manager_files(self):
        result = self.run_install('--upgrade')
        self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
        self.assertEqual(self.root.joinpath('profiles/keep/profile.toml').read_text(), 'id="keep"\n')
        backup = next(self.root.joinpath('upgrade-backups').iterdir())
        self.assertEqual((backup/'engine').read_text(), 'print("OLD ENGINE")\n')
        self.assertEqual((backup/'tui').read_text(), '#!/bin/sh\necho OLD TUI\n')
        installed = self.root/'engine/profilectl.py'
        self.assertEqual(installed.read_bytes(), (ROOT/'engine/profilectl.py').read_bytes())
        self.assertEqual((self.bin/'dotprofile').read_bytes(), (ROOT/'tui/dotprofile').read_bytes())
        checked = subprocess.run(['python3', str(installed), '--version'], capture_output=True, text=True)
        self.assertEqual(checked.returncode, 0)
        self.assertIn(p.VERSION, checked.stdout)

    def test_check_installer_readonly(self):
        before = {str(f.relative_to(self.home)): f.read_bytes() for f in self.home.rglob('*') if f.is_file()}
        result = self.run_install('--check')
        self.assertEqual(result.returncode, 0, result.stderr)
        after = {str(f.relative_to(self.home)): f.read_bytes() for f in self.home.rglob('*') if f.is_file()}
        self.assertEqual(before, after)

    def test_symlinked_manager_refused_without_changes(self):
        engine = self.root/'engine/profilectl.py'
        outside = self.base/'outside.py'
        outside.write_bytes(engine.read_bytes())
        engine.unlink()
        engine.symlink_to(outside)
        result = self.run_install('--upgrade')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Symlinked', result.stderr)
        self.assertTrue(engine.is_symlink())
        self.assertEqual(outside.read_text(), 'print("OLD ENGINE")\n')

    def test_failed_second_manager_replacement_restores_both_files(self):
        move = self.tools/'mv'
        move.write_text('#!/bin/sh\ncase "$3" in */.local/bin/dotprofile) exit 7;; esac\nexec /usr/bin/mv "$@"\n')
        move.chmod(0o755)
        result = self.run_install('--upgrade')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('previous manager restored', result.stderr)
        self.assertEqual(self.root.joinpath('engine/profilectl.py').read_text(), 'print("OLD ENGINE")\n')
        self.assertEqual(self.bin.joinpath('dotprofile').read_text(), '#!/bin/sh\necho OLD TUI\n')
        self.assertEqual(self.root.joinpath('profiles/keep/profile.toml').read_text(), 'id="keep"\n')

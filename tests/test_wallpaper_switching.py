"""Wallpaper IPC is simulated throughout: tests never send live desktop IPC."""
import copy
import os
import shutil
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import test_profilectl as legacy
from test_v06 import AUTOMATION, protected

p, ROOT = legacy.p, legacy.ROOT
REAL_WALLPAPER_SET = p.wallpaper_set

MONITORS = '''
[wallpaper.last]
path="color:#111111"
[wallpaper.monitors.DP-2]
path="color:#222222"
directory="/recipient/dp-wallpapers"
fill_mode="fit"
[wallpaper.monitors.eDP-1]
path="color:#333333"
fill_mode="crop"
[wallpaper.monitors.USB-C-9]
path="color:#444444"
[wallpaper.automation]
enabled=true
interval_seconds=300
'''


class WallpaperTests(unittest.TestCase):
    setUp = legacy.ProfileTests.setUp
    make = legacy.ProfileTests.make

    def recipient(self, automation=False):
        doc = p.tomlkit.parse(legacy.NOCTALIA + MONITORS + (AUTOMATION if automation else ''))
        self.nfile.write_text(p.tomlkit.dumps(doc))
        p.effective_noctalia.return_value = copy.deepcopy(doc)
        return doc

    def profile(self, color=False):
        folder = self.make(n='[wallpaper.default]\npath="'+('color:#abcdef' if color else '@profile/wallpaper.png')+'"\n', u='')
        (folder/'wallpaper.png').write_bytes(b'fake image: native decoding is tested by Noctalia, not this IPC stub')
        return 'color:#abcdef' if color else str(folder/'wallpaper.png')

    def persist(self, path, *, normalize=False, partial=False):
        doc = p.parse(self.nfile)
        p.put(doc, ('wallpaper','default','path'), path)
        p.put(doc, ('wallpaper','last','path'), path)
        for name in ('DP-2','eDP-1','USB-C-9','New-Display-3'):
            p.put(doc, ('wallpaper','monitors',name,'path'), path)
            if partial:
                break
        self.nfile.write_text(p.tomlkit.dumps(doc.unwrap() if normalize else doc))

    def test_bundled_image_ipc_after_backup_validation_and_reload_preserves_settings(self):
        old = self.recipient(True)
        target = self.profile()
        before = self.nfile.read_bytes(), self.ufile.read_bytes()
        def ipc(path):
            self.assertEqual(path, target)
            backups = list((self.state/'backups').iterdir())
            self.assertEqual(len(backups), 1)
            self.assertEqual((backups[0]/'noctalia.toml').read_bytes(), before[0])
            self.assertEqual(p.validate.call_count, 2)
            p.reload.assert_called_once()
            self.assertFalse((self.state/'active-profile').exists())
            self.persist(path, normalize=True)
        p.wallpaper_set.side_effect = ipc
        message = p.apply('test', allow_noctalia_propagation=True)
        self.assertIn('all connected monitors', message)
        self.assertIn('cannot undo those external effects', message)
        after = p.parse(self.nfile)
        for monitor in ('DP-2','eDP-1','USB-C-9','New-Display-3'):
            self.assertEqual(after['wallpaper']['monitors'][monitor]['path'], target)
        self.assertEqual(after['wallpaper']['monitors']['DP-2']['directory'], '/recipient/dp-wallpapers')
        self.assertEqual(after['wallpaper']['monitors']['DP-2']['fill_mode'], 'fit')
        self.assertEqual(after['wallpaper']['automation'], old['wallpaper']['automation'])
        self.assertEqual(after['plugins'], old['plugins'])
        self.assertEqual(after['widget'], old['widget'])
        self.assertEqual(after['bar'], old['bar'])
        self.assertEqual(after['theme']['templates'].unwrap(), old['theme']['templates'].unwrap())
        self.assertEqual(after['hooks'].unwrap(), old['hooks'].unwrap())
        self.assertEqual(after['application_themes'].unwrap(), old['application_themes'].unwrap())
        self.assertEqual(self.ufile.read_bytes(), before[1])
        self.assertEqual(p.validate.call_count, 3)
        self.assertEqual((self.state/'active-profile').read_text().strip(), 'personal:test')

    def test_reapply_matching_default_still_corrects_stale_monitors(self):
        self.recipient()
        target = self.profile(color=True)
        doc = p.parse(self.nfile)
        doc['wallpaper']['default']['path'] = target
        self.nfile.write_text(p.tomlkit.dumps(doc))
        p.effective_noctalia.return_value = copy.deepcopy(doc)
        before = self.nfile.read_bytes()
        p.wallpaper_set.side_effect = self.persist
        self.assertIn('Applied', p.apply('test'))
        p.wallpaper_set.assert_called_once_with(target)
        backup = next((self.state/'backups').iterdir())
        self.assertEqual((backup/'noctalia.toml').read_bytes(), before)
        self.assertEqual(p.parse(self.nfile)['wallpaper']['monitors']['DP-2']['path'], target)

    def test_matching_default_cannot_bypass_propagation_guard(self):
        self.recipient(True)
        target = self.profile(color=True)
        doc = p.parse(self.nfile)
        doc['wallpaper']['default']['path'] = target
        self.nfile.write_text(p.tomlkit.dumps(doc))
        p.effective_noctalia.return_value = copy.deepcopy(doc)
        before = self.nfile.read_bytes()
        output = p.apply('test')
        self.assertIn('Noctalia propagation blocked', output)
        self.assertEqual(self.nfile.read_bytes(), before)
        p.wallpaper_set.assert_not_called()
        self.assertFalse((self.state/'backups').exists())

    def test_propagation_guard_uses_lower_layer_templates(self):
        self.recipient()
        p.effective_noctalia.return_value = p.tomlkit.parse(self.nfile.read_text()+AUTOMATION)
        self.profile()
        before = self.nfile.read_bytes()
        self.assertIn('wallpaper skipped', p.apply('test'))
        self.assertEqual(self.nfile.read_bytes(), before)
        p.wallpaper_set.assert_not_called()

    def test_opted_and_safe_dry_runs_never_use_ipc_reload_or_state(self):
        self.recipient(True)
        self.profile()
        before = self.nfile.read_bytes(), self.ufile.read_bytes()
        safe = p.apply('test', dry=True)
        self.assertIn('wallpaper skipped', safe)
        accepted = p.apply('test', dry=True, allow_noctalia_propagation=True)
        self.assertIn('wallpaper-set for all connected monitors', accepted)
        self.assertEqual(before, (self.nfile.read_bytes(), self.ufile.read_bytes()))
        p.wallpaper_set.assert_not_called()
        p.reload.assert_not_called()
        self.assertFalse(self.state.exists())

    def test_dry_run_matching_config_still_describes_live_ipc(self):
        self.recipient()
        target = self.profile(color=True)
        doc = p.parse(self.nfile)
        doc['wallpaper']['default']['path'] = target
        self.nfile.write_text(p.tomlkit.dumps(doc))
        p.effective_noctalia.return_value = copy.deepcopy(doc)
        output = p.apply('test', dry=True)
        self.assertIn('no file changes', output)
        self.assertIn('wallpaper-set for all connected monitors', output)
        self.assertFalse(self.state.exists())
        p.wallpaper_set.assert_not_called()

    def test_wallpaper_styling_without_explicit_path_does_not_send_ipc(self):
        self.recipient()
        self.make(n='[wallpaper]\nfill_mode="fit"\n', u='')
        p.apply('test')
        p.wallpaper_set.assert_not_called()

    def test_missing_asset_rejected_before_backup_or_ipc(self):
        self.recipient()
        self.profile()
        (self.root/'test/wallpaper.png').unlink()
        before = self.nfile.read_bytes()
        with self.assertRaises(p.ProfileError):
            p.apply('test', allow_noctalia_propagation=True)
        self.assertEqual(self.nfile.read_bytes(), before)
        self.assertFalse((self.state/'backups').exists())
        p.wallpaper_set.assert_not_called()

    def test_validation_and_reload_failures_never_reach_wallpaper_ipc(self):
        self.recipient()
        self.profile()
        before = self.nfile.read_bytes(), self.ufile.read_bytes()
        with patch.object(p,'validate',side_effect=p.ProfileError('invalid candidate')):
            with self.assertRaisesRegex(p.ProfileError, 'invalid candidate'):
                p.apply('test')
        self.assertFalse((self.state/'backups').exists())
        p.reload.side_effect = [['noctalia'], []]
        with self.assertRaisesRegex(p.ProfileError, 'Reload failed'):
            p.apply('test')
        p.wallpaper_set.assert_not_called()
        self.assertEqual(before, (self.nfile.read_bytes(),self.ufile.read_bytes()))

    def test_partial_ipc_failure_rolls_back_known_shell_writes_and_marker(self):
        self.recipient(True)
        target = self.profile()
        self.state.mkdir()
        (self.state/'active-profile').write_text('personal:previous\n')
        before = self.nfile.read_bytes(), self.ufile.read_bytes()
        def fail(path):
            self.assertEqual(path, target)
            self.persist(path, partial=True)
            raise p.ProfileError('Wallpaper IPC failed: simulated disconnected session')
        p.wallpaper_set.side_effect = fail
        with self.assertRaises(p.ProfileError) as error:
            p.apply('test', allow_noctalia_propagation=True)
        self.assertIn('Wallpaper IPC failed', str(error.exception))
        self.assertIn('External template/hook effects cannot be rolled back', str(error.exception))
        self.assertIn('displayed monitor images', str(error.exception))
        self.assertIn('recovery snapshot:', str(error.exception))
        self.assertEqual(before, (self.nfile.read_bytes(),self.ufile.read_bytes()))
        self.assertEqual((self.state/'active-profile').read_text(), 'personal:previous\n')

    def test_timeout_after_partial_persistence_recovers_config(self):
        self.recipient()
        target = self.profile()
        before = self.nfile.read_bytes()
        def timeout(command, **kwargs):
            self.assertEqual(command, ['noctalia','msg','wallpaper-set',target])
            self.persist(target, partial=True)
            raise subprocess.TimeoutExpired(command, kwargs['timeout'])
        with patch.object(p,'wallpaper_set',side_effect=REAL_WALLPAPER_SET), patch.object(p.subprocess,'run',side_effect=timeout):
            with self.assertRaisesRegex(p.ProfileError, 'timed out') as error:
                p.apply('test')
        self.assertIn('Live wallpapers may have changed', str(error.exception))
        self.assertEqual(self.nfile.read_bytes(), before)
        self.assertFalse((self.state/'active-profile').exists())

    def test_normal_ipc_persistence_keeps_protected_source_text(self):
        before = self.recipient(True)
        self.profile()
        p.wallpaper_set.side_effect = self.persist
        p.apply('test', allow_noctalia_propagation=True)
        self.assertEqual(protected(p.parse(self.nfile)), protected(before))

    def test_failed_config_recovery_preserves_original_ipc_error_and_snapshot(self):
        self.recipient()
        self.profile()
        real_restore = p.restore_file
        def recovery(source, target):
            if target == self.nfile:
                raise PermissionError('simulated recovery write failure')
            return real_restore(source, target)
        p.wallpaper_set.side_effect = p.ProfileError('Wallpaper IPC failed: unavailable')
        p.reload.side_effect = [[], ['noctalia']]
        with patch.object(p,'restore_file',side_effect=recovery):
            with self.assertRaises(p.ProfileError) as failure:
                p.apply('test')
        message = str(failure.exception)
        for expected in ('Wallpaper IPC failed: unavailable', 'rollback failed', 'Recovery reload failed: noctalia', 'recovery snapshot:', 'External template/hook effects cannot be rolled back'):
            self.assertIn(expected, message)
        self.assertFalse((self.state/'active-profile').exists())
        self.assertTrue(any((self.state/'backups').iterdir()))

    def test_ipc_failure_when_config_already_matched_still_rolls_back_monitor_writes(self):
        self.recipient()
        target = self.profile(color=True)
        doc = p.parse(self.nfile)
        doc['wallpaper']['default']['path'] = target
        self.nfile.write_text(p.tomlkit.dumps(doc))
        p.effective_noctalia.return_value = copy.deepcopy(doc)
        before = self.nfile.read_bytes()
        def fail(path):
            self.persist(path, partial=True)
            raise p.ProfileError('Wallpaper IPC failed: partial')
        p.wallpaper_set.side_effect = fail
        with self.assertRaisesRegex(p.ProfileError, 'Wallpaper IPC failed'):
            p.apply('test')
        self.assertEqual(self.nfile.read_bytes(), before)

    def test_post_ipc_validation_failure_recovers_config(self):
        self.recipient()
        self.profile()
        before = self.nfile.read_bytes()
        p.wallpaper_set.side_effect = self.persist
        p.validate.side_effect = [None, None, p.ProfileError('post-IPC validation failed')]
        with self.assertRaisesRegex(p.ProfileError, 'post-IPC validation failed'):
            p.apply('test')
        self.assertEqual(self.nfile.read_bytes(), before)
        self.assertFalse((self.state/'active-profile').exists())

    def test_concurrent_plugin_template_and_hardware_edits_survive_ipc_failure(self):
        self.recipient(True)
        self.profile()
        def fail(path):
            self.persist(path, partial=True)
            doc = p.parse(self.nfile)
            doc['widget']['phone']['my_secret_setting'] = 'changed-concurrently'
            doc['theme']['templates']['enable_builtin_templates'] = False
            self.nfile.write_text(p.tomlkit.dumps(doc))
            compositor = p.parse(self.ufile)
            compositor['output']['TEST-OUTPUT-1']['mode'] = '1280x720@60'
            self.ufile.write_text(p.tomlkit.dumps(compositor))
            raise p.ProfileError('Wallpaper IPC failed: concurrent edit')
        p.wallpaper_set.side_effect = fail
        with self.assertRaisesRegex(p.ProfileError, 'rollback skipped'):
            p.apply('test', allow_noctalia_propagation=True)
        after = p.parse(self.nfile)
        self.assertEqual(after['widget']['phone']['my_secret_setting'], 'changed-concurrently')
        self.assertFalse(after['theme']['templates']['enable_builtin_templates'])
        self.assertEqual(p.parse(self.ufile)['output']['TEST-OUTPUT-1']['mode'], '1280x720@60')
        self.assertFalse((self.state/'active-profile').exists())

    def test_concurrent_edit_before_ipc_aborts_without_sending_it(self):
        self.recipient()
        self.profile()
        def reload():
            doc = p.parse(self.nfile)
            doc['widget']['phone']['my_secret_setting'] = 'edited-before-ipc'
            self.nfile.write_text(p.tomlkit.dumps(doc))
            return []
        p.reload.side_effect = reload
        with self.assertRaisesRegex(p.ProfileError, 'no command sent'):
            p.apply('test')
        p.wallpaper_set.assert_not_called()
        self.assertEqual(p.parse(self.nfile)['widget']['phone']['my_secret_setting'], 'edited-before-ipc')

    def test_empty_path_has_clear_warning_and_no_unsupported_ipc(self):
        self.recipient()
        self.make(n='[wallpaper.default]\npath=""\n', u='')
        self.assertIn('empty path', p.apply('test'))
        p.wallpaper_set.assert_not_called()

    def test_wallpaper_only_apply_does_not_require_or_create_compositor_config(self):
        self.recipient()
        self.profile(color=True)
        self.ufile.unlink()
        p.wallpaper_set.side_effect = self.persist
        p.apply('test')
        p.wallpaper_set.assert_called_once()
        self.assertFalse(self.ufile.exists())

    def test_restore_dry_run_consent_and_ipc_recovery(self):
        self.recipient(True)
        current = p.parse(self.nfile)
        current['wallpaper']['default']['path'] = 'color:#111111'
        self.nfile.write_text(p.tomlkit.dumps(current))
        p.effective_noctalia.return_value = copy.deepcopy(current)
        target = self.profile(color=True)
        p.wallpaper_set.side_effect = self.persist
        p.apply('test', allow_noctalia_propagation=True)
        backup = next((self.state/'backups').iterdir())
        p.effective_noctalia.return_value = p.parse(self.nfile)
        p.wallpaper_set.reset_mock()
        before = self.nfile.read_bytes()
        self.assertIn('wallpaper skipped', p.restore(backup.name, dry=True))
        p.restore(backup.name)
        p.wallpaper_set.assert_not_called()
        self.assertEqual(self.nfile.read_bytes(), before)
        self.assertIn('wallpaper-set', p.restore(backup.name, dry=True, allow_noctalia_propagation=True))
        p.wallpaper_set.assert_not_called()
        def fail(path):
            self.assertEqual(path, 'color:#111111')
            self.persist(path, partial=True)
            raise p.ProfileError('Wallpaper IPC failed: restore')
        p.wallpaper_set.side_effect = fail
        with self.assertRaisesRegex(p.ProfileError, 'Wallpaper IPC failed: restore'):
            p.restore(backup.name, allow_noctalia_propagation=True)
        self.assertEqual(self.nfile.read_bytes(), before)
        self.assertEqual(p.parse(self.nfile)['wallpaper']['default']['path'], target)
        p.wallpaper_set.side_effect = self.persist
        p.restore(backup.name, allow_noctalia_propagation=True)
        self.assertEqual(p.parse(self.nfile)['wallpaper']['monitors']['DP-2']['path'], 'color:#111111')

    def test_relative_snapshot_image_cannot_be_misread_as_monitor_selector(self):
        doc = p.tomlkit.parse('[wallpaper.default]\npath="VERSION"\n')
        with self.assertRaisesRegex(p.ProfileError, 'must be absolute'):
            p.wallpaper_request(doc, p.tomlkit.document(), True)
        p.wallpaper_set.assert_not_called()

    def test_real_ipc_argument_vector_and_failure_details_no_shell(self):
        target = str(self.base/'wallpaper with spaces.png')
        with patch.object(p.subprocess,'run', return_value=subprocess.CompletedProcess([],0,'ok','')) as run:
            REAL_WALLPAPER_SET(target)
        run.assert_called_once_with(['noctalia','msg','wallpaper-set',target],capture_output=True,text=True,timeout=20,check=False)
        with patch.object(p.subprocess,'run', return_value=subprocess.CompletedProcess([],1,'','session unavailable')):
            with self.assertRaisesRegex(p.ProfileError, 'session unavailable'):
                REAL_WALLPAPER_SET(target)
        for error in (FileNotFoundError('no executable'), subprocess.TimeoutExpired(['noctalia'],20)):
            with patch.object(p.subprocess,'run', side_effect=error):
                with self.assertRaisesRegex(p.ProfileError, 'Wallpaper IPC failed'):
                    REAL_WALLPAPER_SET(target)

    def test_ipc_write_recognition_rejects_unrelated_changes_and_malformed_toml(self):
        before = self.recipient()
        new = copy.deepcopy(before)
        path = 'color:#abcdef'
        p.put(new,('wallpaper','monitors','Dynamic-9','path'),path)
        self.assertTrue(p.wallpaper_ipc_write(p.tomlkit.dumps(before),p.tomlkit.dumps(new.unwrap()),path))
        new['wallpaper']['monitors']['Dynamic-9']['path'] = 'color:#999999'
        self.assertFalse(p.wallpaper_ipc_write(p.tomlkit.dumps(before),p.tomlkit.dumps(new),path))
        self.assertFalse(p.wallpaper_ipc_write(p.tomlkit.dumps(before),'not toml [',path))
        new = copy.deepcopy(before)
        new['wallpaper']['automation']['enabled'] = False
        self.assertFalse(p.wallpaper_ipc_write(p.tomlkit.dumps(before),p.tomlkit.dumps(new),path))

    @unittest.skipUnless(shutil.which('noctalia') and shutil.which('umbriel'), 'installed native validators required')
    def test_native_cli_wallpaper_apply_reapply_dry_run_and_failure_recovery_isolated(self):
        import json
        # CLI process has no mocks: forward only config commands to installed
        # validators/exports, and handle EVERY msg in the isolated test adapter.
        config = self.base/'config'
        state_home = self.base/'desktop-state'
        config.joinpath('noctalia').mkdir(parents=True)
        state_home.joinpath('noctalia').mkdir(parents=True)
        nfile = state_home/'noctalia/settings.toml'
        nfile.write_text((ROOT/'tests/fixtures/main-bar.toml').read_text() + '''
[wallpaper.default]
path="color:#101010"
[wallpaper.monitors.DP-7]
path="color:#202020"
fill_mode="fit"
[wallpaper.monitors.eDP-2]
path="color:#303030"
''')
        self.ufile.write_text('[appearance]\nborder_width=2\n')
        self.profile()
        # Use a real tiny PNG so native candidates refer to an actual image.
        import struct
        import zlib
        target = self.root/'test/wallpaper.png'
        def png_chunk(kind, data):
            return struct.pack('>I', len(data))+kind+data+struct.pack('>I', zlib.crc32(kind+data))
        target.write_bytes(b'\x89PNG\r\n\x1a\n'+
                          png_chunk(b'IHDR', struct.pack('>IIBBBBB',1,1,8,2,0,0,0))+
                          png_chunk(b'IDAT', zlib.compress(b'\x00\x80\x80\x80'))+png_chunk(b'IEND', b''))
        bins = self.base/'bin'
        bins.mkdir()
        adapter = ROOT/'tests/fixtures/wallpaper-ipc-shim.py'
        env = dict(os.environ, NDP_PROFILE_ROOT=str(self.root), NDP_DEFAULT_ROOT=str(self.base/'defaults'),
                   NDP_STATE_ROOT=str(self.state), NDP_NOCTALIA_FILE=str(nfile), NDP_UMBRIEL_FILE=str(self.ufile),
                   NOCTALIA_CONFIG_HOME=str(config), NOCTALIA_STATE_HOME=str(state_home), NDP_NOCTALIA_EXPORT_FILE='',
                   DOTPROFILE_TEST_ROOT=str(self.base), DOTPROFILE_TEST_REAL_NOCTALIA=shutil.which('noctalia'),
                   DOTPROFILE_TEST_REAL_UMBRIEL=shutil.which('umbriel'), PATH=str(bins)+os.pathsep+os.environ['PATH'])
        for program in ('noctalia','umbriel'):
            launcher = bins/program
            launcher.write_text('#!'+sys.executable+'\nimport runpy,sys\nsys.argv='+repr([str(adapter), program])+'+sys.argv[1:]\nrunpy.run_path('+repr(str(adapter))+',run_name="__main__")\n')
            launcher.chmod(0o700)
        log = self.base/'ipc-log.jsonl'
        def command(*args, success=True, extra_env=None):
            result = subprocess.run([sys.executable,str(ROOT/'engine/profilectl.py'),*args],env=dict(env,**(extra_env or {})),capture_output=True,text=True,timeout=40)
            self.assertEqual(result.returncode == 0, success, result.stderr+result.stdout)
            return result
        before = nfile.read_bytes()
        result = command('apply','test','--dry-run')
        self.assertIn('wallpaper-set for all connected monitors', result.stdout)
        self.assertEqual(nfile.read_bytes(), before)
        self.assertFalse(log.exists())
        self.assertFalse(self.state.exists())
        command('apply','test')
        doc = p.parse(nfile)
        old = p.tomlkit.parse(before.decode())
        for connector in ('DP-7','eDP-2','New-Output-4'):
            self.assertEqual(doc['wallpaper']['monitors'][connector]['path'], str(target))
        self.assertEqual(doc['wallpaper']['monitors']['DP-7']['fill_mode'], 'fit')
        self.assertEqual(doc['plugins'], old['plugins'])
        self.assertEqual(doc['plugin_settings'], old['plugin_settings'])
        self.assertEqual(doc['widget'], old['widget'])
        # Same config still issues the all-monitor IPC request again.
        command('apply','test')
        sent = [json.loads(line) for line in log.read_text().splitlines()]
        self.assertEqual([c for c in sent if c[2]=='wallpaper-set'], [['noctalia','msg','wallpaper-set',str(target)]]*2)
        baseline = nfile.read_bytes()
        active = (self.state/'active-profile').read_bytes()
        self.make('second', n='[wallpaper.default]\npath="color:#fafafa"\n',u='')
        result = command('apply','second',success=False,extra_env={'DOTPROFILE_TEST_IPC_MODE':'partial-failure'})
        self.assertIn('Wallpaper IPC failed',result.stderr)
        self.assertIn('External template/hook effects cannot be rolled back', result.stderr)
        self.assertEqual(nfile.read_bytes(),baseline)
        self.assertEqual((self.state/'active-profile').read_bytes(),active)

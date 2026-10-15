import copy
import hashlib
import io
import shutil
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
import test_profilectl as legacy

p, ROOT = legacy.p, legacy.ROOT
DEFAULT_ID = 'example-minimal'


def files(folder):
    return {str(f.relative_to(folder)): f.read_bytes() for f in folder.rglob('*') if f.is_file()}


class DefaultProfileTests(unittest.TestCase):
    setUp = legacy.ProfileTests.setUp
    make = legacy.ProfileTests.make

    def defaults(self):
        before = self.nfile.read_bytes(), self.ufile.read_bytes(), files(self.root)
        report = p.install_defaults(ROOT/'defaults')
        self.assertIn('Personal profiles and running desktop unchanged', report)
        self.assertEqual(before, (self.nfile.read_bytes(), self.ufile.read_bytes(), files(self.root)))
        return p.DEFAULT_ROOT/DEFAULT_ID

    def test_installed_defaults_have_release_digests_and_readonly_files(self):
        folder = self.defaults()
        p.verify_default(folder, DEFAULT_ID)
        self.assertEqual({f.name: hashlib.sha256(f.read_bytes()).hexdigest() for f in folder.iterdir()}, p.OFFICIAL_DEFAULTS[DEFAULT_ID])
        self.assertTrue(all(f.stat().st_mode & 0o222 == 0 for f in folder.iterdir()))
        self.assertEqual(p.profiles()[0]['source'], 'Default')
        self.assertEqual(p.profiles()[0]['key'], 'default:'+DEFAULT_ID)

    def test_engine_blocks_every_default_mutation(self):
        folder = self.defaults()
        before = files(folder)
        for operation in (lambda: p.save('default:'+DEFAULT_ID),
                          lambda: p.save('default:'+DEFAULT_ID, overwrite=True, confirmed=True),
                          lambda: p.save(DEFAULT_ID, overwrite=True, confirmed=True),
                          lambda: p.rename_profile('default:'+DEFAULT_ID, 'changed', True),
                          lambda: p.delete_profile('default:'+DEFAULT_ID, True)):
            with self.assertRaisesRegex(p.ProfileError, 'immutable|Save As'):
                operation()
            self.assertEqual(files(folder), before)
        self.assertFalse((self.state/'profile-backups').exists())

    def test_defaults_apply_export_and_remain_original(self):
        folder = self.defaults()
        baseline = files(folder)
        before_widgets = p.parse(self.nfile)['widget'].unwrap()
        self.assertIn('VALID', p.apply('default:'+DEFAULT_ID, True))
        p.apply('default:'+DEFAULT_ID)
        self.assertEqual((self.state/'active-profile').read_text().strip(), 'default:'+DEFAULT_ID)
        self.assertEqual(p.parse(self.nfile)['widget'].unwrap(), before_widgets)
        self.assertEqual(files(folder), baseline)
        export_base = self.base/'out'
        self.assertIn('import as Personal', p.export_profile('default:'+DEFAULT_ID, export_base))
        self.assertEqual(files(export_base/DEFAULT_ID), baseline)
        self.assertEqual(files(folder), baseline)

    def test_customized_desktop_from_default_requires_save_as_new_name(self):
        folder = self.defaults()
        baseline = files(folder)
        p.apply('default:'+DEFAULT_ID)
        live = p.parse(self.nfile)
        live['theme']['mode'] = 'light'
        self.nfile.write_text(p.tomlkit.dumps(live))
        p.effective_noctalia.return_value = copy.deepcopy(live)
        with self.assertRaises(p.ProfileError):
            p.save(DEFAULT_ID)
        p.save('my-custom-default')
        self.assertEqual(p.parse(self.root/'my-custom-default/noctalia.toml')['theme']['mode'], 'light')
        self.assertEqual(files(folder), baseline)
        self.assertEqual(p.parse(self.nfile)['theme']['mode'], 'light')
        p.apply('default:'+DEFAULT_ID)
        self.assertEqual(p.parse(self.nfile)['theme']['builtin'], 'Gruvbox')
        self.assertEqual(files(folder), baseline)

    def test_imported_official_copy_is_personal_and_can_share_default_name(self):
        folder = self.defaults()
        p.install_profile(folder)
        self.assertEqual({x['source'] for x in p.profiles()}, {'Default','Personal'})
        self.assertEqual({x['key'] for x in p.profiles()}, {'default:'+DEFAULT_ID,'personal:'+DEFAULT_ID})
        self.assertEqual(p.profile_ref(DEFAULT_ID), ('personal', DEFAULT_ID))
        self.assertEqual(p.profile_ref('default:'+DEFAULT_ID), ('default',DEFAULT_ID))
        self.assertEqual(p.ensure_manifest(DEFAULT_ID)[0], self.root/DEFAULT_ID)

    def test_official_update_never_overwrites_personal_collision(self):
        folder = self.defaults()
        p.install_profile(folder)
        personal = self.root/DEFAULT_ID/'noctalia.toml'
        personal.write_text('[theme]\nmode="light"\n')
        before = files(self.root), self.nfile.read_bytes(), self.ufile.read_bytes()
        p.install_defaults(ROOT/'defaults')
        self.assertEqual(before, (files(self.root), self.nfile.read_bytes(), self.ufile.read_bytes()))
        self.assertEqual(p.parse(personal)['theme']['mode'], 'light')
        self.assertEqual(p.parse(folder/'noctalia.toml')['theme']['builtin'], 'Gruvbox')

    def test_arbitrary_metadata_cannot_grant_default_status(self):
        for field in ('source="Default"', 'official=true', 'immutable=true', 'origin="dotprofile"'):
            if (self.root/'test').exists(): shutil.rmtree(self.root/'test')
            folder = self.make()
            with open(folder/'profile.toml','a') as out: out.write(field+'\n')
            with patch.object(p,'PROFILE_ROOT',self.base/'other'):
                with self.assertRaisesRegex(p.ProfileError,'metadata'):
                    p.install_profile(folder)
        self.assertFalse(p.DEFAULT_ROOT.exists())

    def test_unknown_folder_in_default_storage_is_not_an_official_profile(self):
        self.make(name='untrusted')
        p.DEFAULT_ROOT.mkdir()
        shutil.copytree(self.root/'untrusted', p.DEFAULT_ROOT/'untrusted')
        with self.assertRaisesRegex(p.ProfileError,'Not an official'):
            p.ensure_manifest('default:untrusted')
        self.assertFalse(any(x['key']=='default:untrusted' for x in p.profiles()))

    def test_default_tampering_and_fake_catalogue_are_rejected(self):
        source = self.base/'forged-release'
        shutil.copytree(ROOT/'defaults',source)
        (source/DEFAULT_ID/'noctalia.toml').write_text('[theme]\nmode="light"\n')
        (source/'catalog.toml').write_text('trust_everything=true\n')
        with self.assertRaisesRegex(p.ProfileError,'official release'):
            p.install_defaults(source)
        self.assertFalse(p.DEFAULT_ROOT.exists())

    def test_external_default_edit_does_not_become_personal_or_trusted(self):
        folder = self.defaults()
        file = folder/'noctalia.toml'
        file.chmod(0o600)
        file.write_text('[theme]\nmode="light"\n')
        with self.assertRaisesRegex(p.ProfileError,'official release'):
            p.apply('default:'+DEFAULT_ID,True)
        self.assertFalse(p.profiles())

    def test_personal_overwrite_requires_confirmation_and_retains_backup(self):
        self.make()
        original = files(self.root/'test')
        for overwrite, confirm in ((False,False),(True,False)):
            with self.assertRaises(p.ProfileError): p.save('test',overwrite=overwrite,confirmed=confirm)
            self.assertEqual(files(self.root/'test'),original)
        report = p.save('personal:test',overwrite=True,confirmed=True)
        self.assertIn('prior Personal profile backup', report)
        archive = next((self.state/'profile-backups/test').glob('*/test'))
        self.assertEqual(files(archive),original)
        self.assertNotEqual(files(self.root/'test'),original)
        self.assertEqual(self.nfile.read_text(),legacy.NOCTALIA)

    def test_personal_import_overwrite_requires_confirmation_and_backup(self):
        self.make()
        source = self.base/'import-source/test'
        shutil.copytree(self.root/'test',source)
        (source/'noctalia.toml').write_text('[theme]\nmode="light"\n')
        original = files(self.root/'test')
        with self.assertRaises(p.ProfileError): p.install_profile(source,overwrite=True)
        self.assertEqual(files(self.root/'test'),original)
        p.install_profile(source,overwrite=True,confirmed=True)
        archive = next((self.state/'profile-backups/test').glob('*/test'))
        self.assertEqual(files(archive),original)
        self.assertEqual(p.parse(self.root/'test/noctalia.toml')['theme']['mode'],'light')

    def test_rename_personal_confirmed_backed_up_and_desktop_unchanged(self):
        self.make()
        original = files(self.root/'test')
        desktop = self.nfile.read_bytes(), self.ufile.read_bytes()
        with self.assertRaises(p.ProfileError): p.rename_profile('test','renamed')
        p.rename_profile('personal:test','personal:renamed',True)
        self.assertFalse((self.root/'test').exists())
        self.assertEqual(p.parse(self.root/'renamed/profile.toml')['id'],'renamed')
        self.assertEqual(p.parse(self.root/'renamed/profile.toml')['name'],'Renamed')
        archive = next((self.state/'profile-backups/test').glob('*/test'))
        self.assertEqual(files(archive),original)
        self.assertEqual(desktop,(self.nfile.read_bytes(), self.ufile.read_bytes()))

    def test_delete_personal_confirmed_backed_up_and_desktop_unchanged(self):
        self.make()
        original = files(self.root/'test')
        desktop = self.nfile.read_bytes(), self.ufile.read_bytes()
        with self.assertRaises(p.ProfileError): p.delete_profile('test')
        p.delete_profile('personal:test',True)
        self.assertFalse((self.root/'test').exists())
        archive = next((self.state/'profile-backups/test').glob('*/test'))
        self.assertEqual(files(archive),original)
        self.assertEqual(desktop,(self.nfile.read_bytes(), self.ufile.read_bytes()))
        self.assertIn('Installed Personal',p.install_profile(archive))
        self.assertEqual(files(self.root/'test'),original)

    def test_personal_collision_deletion_never_removes_default(self):
        default = self.defaults()
        original = files(default)
        p.install_profile(default)
        p.delete_profile('personal:'+DEFAULT_ID,True)
        self.assertEqual(files(default),original)
        self.assertEqual(p.profile_ref(DEFAULT_ID),('default',DEFAULT_ID))
        self.assertEqual(p.profiles()[0]['source'],'Default')

    def test_export_refuses_any_managed_storage_target(self):
        folder = self.defaults()
        original = files(folder)
        for destination in (p.DEFAULT_ROOT,self.root,self.state/'profile-backups'):
            with self.assertRaises(p.ProfileError): p.export_profile('default:'+DEFAULT_ID,destination)
        self.assertEqual(files(folder),original)

    def test_default_and_personal_storage_overlap_is_refused(self):
        self.defaults()
        for path in (self.root,self.root/'nested',self.root.parent):
            with patch.object(p,'DEFAULT_ROOT',path):
                with self.assertRaisesRegex(p.ProfileError,'separate'):
                    p.profile_ref('personal:test')

    def test_failed_personal_overwrite_restores_original(self):
        self.make()
        original = files(self.root/'test')
        replace = p.os.replace
        def fail_publish(src,dest):
            if Path(dest)==self.root/'test' and '.save-' in str(src):
                raise OSError('simulated publication failure')
            return replace(src,dest)
        with patch.object(p.os,'replace',side_effect=fail_publish):
            with self.assertRaises(OSError): p.save('test',overwrite=True,confirmed=True)
        self.assertEqual(files(self.root/'test'),original)
        archive = next((self.state/'profile-backups/test').glob('*/test'))
        self.assertEqual(files(archive),original)

    def test_failed_rename_manifest_write_restores_original(self):
        self.make()
        original = files(self.root/'test')
        original_write = p.atomic_write
        def fail_manifest(file,data):
            if Path(file)==self.root/'renamed/profile.toml': raise OSError('simulated rename failure')
            return original_write(file,data)
        with patch.object(p,'atomic_write',side_effect=fail_manifest):
            with self.assertRaises(OSError): p.rename_profile('test','renamed',True)
        self.assertEqual(files(self.root/'test'),original)
        self.assertFalse((self.root/'renamed').exists())

    def test_cli_default_protection_and_labels(self):
        folder = self.defaults()
        original = files(folder)
        for args in (['save','default:'+DEFAULT_ID,'--overwrite','--confirm'],
                     ['rename','default:'+DEFAULT_ID,'renamed','--confirm'],
                     ['delete','default:'+DEFAULT_ID,'--confirm']):
            with patch.object(sys,'argv',['profilectl',*args]), patch('sys.stderr',new=io.StringIO()):
                self.assertEqual(p.cli(),1)
        with patch.object(sys,'argv',['profilectl','list','--labels']), patch('sys.stdout',new=io.StringIO()) as output:
            self.assertEqual(p.cli(),0)
            self.assertIn('Default: '+DEFAULT_ID,output.getvalue())
        self.assertEqual(files(folder),original)

    def test_install_extra_template_sidecar_in_defaults_root_is_refused(self):
        source = self.base/'release-extra'
        shutil.copytree(ROOT/'defaults',source)
        (source/'theme-templates.toml').write_text('[theme.templates]\nbuiltin_ids=["kitty"]')
        with self.assertRaises(p.ProfileError): p.install_defaults(source)
        self.assertFalse(p.DEFAULT_ROOT.exists())

    def test_import_cannot_use_overlapping_storage_to_modify_default(self):
        source = self.make()
        original = files(self.root)
        with patch.object(p,'DEFAULT_ROOT',self.root):
            with self.assertRaisesRegex(p.ProfileError,'separate'):
                p.install_profile(source,overwrite=True,confirmed=True)
        self.assertEqual(files(self.root),original)

    def test_export_personal_copy_strips_private_template_comments(self):
        folder=self.make(n='[theme]\nmode="dark" # private template post_hook detail\n')
        p.export_profile('personal:test',self.base/'export')
        self.assertNotIn('private template', (self.base/'export/test/noctalia.toml').read_text())
        self.assertIn('private template', (folder/'noctalia.toml').read_text())


class DefaultTUITests(unittest.TestCase):
    def scenario(self, action, source):
        import tempfile, os, subprocess, json
        with tempfile.TemporaryDirectory() as directory:
            base=Path(directory)
            engine=base/'engine.py'
            engine.write_text('''import os,sys,json
with open(os.environ['TEST_LOG'],'a') as file: file.write(json.dumps(sys.argv[1:])+'\\n')
if sys.argv[1]=='list': print('Default: example-minimal\\nPersonal: my-profile')
else: print('VALID simulated')
''')
            gum=base/'gum'
            gum.write_text('''#!/usr/bin/env python3
import os,sys
from pathlib import Path
base=Path(os.environ['TEST_DIR'])
args=sys.argv[1:]
if args[0]=='choose':
    header=args[args.index('--header')+1]
    if header.startswith('Dotprofile'):
        marker=base/'menu'
        if marker.exists(): print('Quit')
        else:
            marker.touch()
            print(os.environ['TEST_ACTION'])
    else:
        choices=sys.stdin.read()
        (base/'labels').write_text(choices)
        print('Default: example-minimal' if os.environ['TEST_SOURCE']=='default' else 'Personal: my-profile')
elif args[0]=='style': print(args[1])
else: print('')
''')
            gum.chmod(0o755)
            env=dict(os.environ,DOTPROFILE_ENGINE=str(engine),PATH=str(base)+os.pathsep+os.environ['PATH'],
                     TEST_DIR=str(base),TEST_LOG=str(base/'log'),TEST_ACTION=action,TEST_SOURCE=source)
            result=subprocess.run(['bash',str(ROOT/'tui/dotprofile')],env=env,capture_output=True,text=True,timeout=15)
            self.assertEqual(result.returncode,0,result.stderr)
            calls=[json.loads(line) for line in (base/'log').read_text().splitlines()]
            labels=(base/'labels').read_text()
            return calls,labels,result.stdout

    def test_tui_shows_both_labels_and_switches_back_to_default(self):
        calls, labels, _=self.scenario('Switch Profile','default')
        self.assertIn('Default: example-minimal',labels)
        self.assertIn('Personal: my-profile',labels)
        self.assertIn(['apply','default:example-minimal','--dry-run'],calls)
        self.assertIn(['apply','default:example-minimal'],calls)

    def test_tui_personal_selection_preserves_namespace(self):
        calls, _, _=self.scenario('Switch Profile','personal')
        self.assertIn(['apply','personal:my-profile'],calls)

    def test_tui_management_explicitly_refuses_default_mutation(self):
        calls, _, output=self.scenario('Manage profiles','default')
        self.assertFalse(any(args[0] in ('rename','delete','save') for args in calls))
        self.assertIn('Default originals cannot be renamed, deleted, or overwritten',output)

"""v0.6: recipient-owned templates/hooks never become profile-owned settings."""
import copy
import io
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import test_profilectl as legacy

p, ROOT = legacy.p, legacy.ROOT
AUTOMATION = '''
# Recipient owns every setting below; even comments/order must survive.
[theme.templates]
enable_builtin_templates = true # keep this flag
enable_community_templates = true
builtin_ids = ["kitty", "gtk3"]
community_ids = ["editor"]
[theme.templates.user.my_app]
enabled = true
input_path = "templates/my-app.css"
output_path = "~/.config/my-app/theme.css"
pre_hook = "recipient-prepare"
post_hook = "recipient-reload"
[hooks]
colors_changed = ["recipient-colors"] # do not replace
wallpaper_changed = "recipient-wallpaper"
theme_mode_changed = ["recipient-mode"]
[application_themes]
private_config = "never-package-this"
'''


def protected(doc):
    return tuple(p.tomlkit.dumps(value) for value in
                 (doc['theme']['templates'], doc['hooks'], doc.get('application_themes', {})))


class V06Tests(unittest.TestCase):
    setUp = legacy.ProfileTests.setUp
    make = legacy.ProfileTests.make

    def recipient(self, automation=AUTOMATION):
        source = legacy.NOCTALIA + automation
        self.nfile.write_text(source)
        p.effective_noctalia.return_value = p.tomlkit.parse(source)
        return p.tomlkit.parse(source)

    def appearance(self):
        return p.tomlkit.parse('[theme]\nmode="light"\n[wallpaper.default]\npath="color:#112233"\n[shell]\nfont_family="sans-serif"\n')

    def test_save_packages_exclude_template_hook_and_application_config(self):
        self.recipient()
        p.save('public')
        directory = self.root/'public'
        for file in directory.iterdir():
            if file.suffix == '.toml':
                text = file.read_text()
                for forbidden in ('theme.templates', '[hooks]', 'builtin_ids', 'community_ids',
                                  'input_path', 'output_path', 'pre_hook', 'post_hook',
                                  'application_themes', 'never-package-this', 'recipient-reload'):
                    self.assertNotIn(forbidden, text)
        self.assertEqual(set(directory.iterdir()), {directory/n for n in
                         ('profile.toml','noctalia.toml','umbriel.toml','workspace.toml')})

    def test_export_comments_cannot_leak_associated_template_details(self):
        source = legacy.NOCTALIA.replace('mode = "dark"', 'mode = "dark" # post_hook = "PRIVATE_TEMPLATE_DETAIL"')
        self.nfile.write_text(source)
        p.effective_noctalia.return_value = p.tomlkit.parse(source)
        self.ufile.write_text(legacy.UMBRIEL.replace('border_width = 8', 'border_width = 8 # private template file'))
        p.save('public')
        self.assertNotIn('PRIVATE_TEMPLATE_DETAIL', (self.root/'public/noctalia.toml').read_text())
        self.assertNotIn('private template file', (self.root/'public/umbriel.toml').read_text())

    def test_default_skip_preserves_protected_config_exactly(self):
        live = self.recipient()
        baseline = protected(live)
        original_theme = copy.deepcopy(live['theme'])
        original_wallpaper = copy.deepcopy(live['wallpaper'])
        notes = p.patch_noctalia(live, self.appearance(), copy.deepcopy(live))
        self.assertEqual(live['theme'], original_theme)
        self.assertEqual(live['wallpaper'], original_wallpaper)
        self.assertEqual(live['shell']['font_family'], 'sans-serif')
        self.assertEqual(protected(live), baseline)
        self.assertTrue(any('theme skipped' in n for n in notes))
        self.assertTrue(any('wallpaper skipped' in n for n in notes))
        self.assertTrue(any('--allow-noctalia-propagation' in n for n in notes))

    def test_opt_in_changes_appearance_but_not_template_hook_settings(self):
        live = self.recipient()
        baseline = protected(live)
        notes = p.patch_noctalia(live, self.appearance(), copy.deepcopy(live), True)
        self.assertEqual(live['theme']['mode'], 'light')
        self.assertEqual(live['wallpaper']['default']['path'], 'color:#112233')
        self.assertEqual(protected(live), baseline)
        self.assertIn('existing hooks may execute commands', '; '.join(notes))
        self.assertIn('cannot undo those external effects', '; '.join(notes))

    def test_import_denies_templates_and_hooks_even_with_opt_in(self):
        for content in ('[theme.templates]\nenable_builtin_templates=false',
                        '[theme.templates.user.new_app]\noutput_path="~/.config/new_app/theme"\npost_hook="profile-command"',
                        '[hooks]\ncolors_changed="profile-command"',
                        '[application_themes]\nkitty="theme"',
                        '[theme]\npost_hook="profile-command"'):
            with self.subTest(content=content):
                if (self.root/'test').exists():
                    import shutil
                    shutil.rmtree(self.root/'test')
                self.make(n=content)
                before = self.nfile.read_bytes(), self.ufile.read_bytes()
                with self.assertRaises(p.ProfileError):
                    p.apply('test', allow_noctalia_propagation=True)
                self.assertEqual(before, (self.nfile.read_bytes(),self.ufile.read_bytes()))
        self.assertFalse((self.state/'backups').exists())
        self.assertFalse((self.state/'active-profile').exists())
        p.reload.assert_not_called()

    def test_merge_boundary_denies_profile_automation_even_with_opt_in(self):
        for text in ('[theme.templates]\nbuiltin_ids=["kitty"]', '[hooks]\ncolors_changed="bad"'):
            live = self.recipient()
            with self.assertRaises(p.ProfileError):
                p.patch_noctalia(live, p.tomlkit.parse(text), copy.deepcopy(live), True)
            self.assertEqual(live, p.effective_noctalia())

    def test_install_profile_rejects_template_files_and_nested_directories(self):
        for name in ('templates.toml', 'kitty.conf', 'hooks.sh', 'templates', 'hooks'):
            with self.subTest(name=name):
                if (self.root/'test').exists():
                    import shutil
                    shutil.rmtree(self.root/'test')
                folder = self.make()
                entry = folder/name
                if name in ('templates','hooks'):
                    entry.mkdir()
                    (entry/'private').write_text('private')
                else:
                    entry.write_text('private')
                target = self.base/'new-library'
                with patch.object(p, 'PROFILE_ROOT', target):
                    with self.assertRaises(p.ProfileError):
                        p.install_profile(folder)
                self.assertFalse(target.exists())

    def test_no_automation_palette_and_wallpaper_remain_supported(self):
        live = p.tomlkit.parse(legacy.NOCTALIA)
        notes = p.patch_noctalia(live, self.appearance(), copy.deepcopy(live))
        self.assertFalse(notes)
        self.assertEqual(live['theme']['mode'], 'light')
        self.assertEqual(live['wallpaper']['default']['path'], 'color:#112233')

    def test_catalog_flags_and_user_template_enablement_are_respected(self):
        inactive = '''[theme.templates]
builtin_ids=["kitty"]
community_ids=["editor"]
enable_builtin_templates=false
enable_community_templates=false
[theme.templates.user.app]
enabled=false
output_path="~/.config/app/theme"
'''
        live = self.recipient(inactive)
        baseline = p.tomlkit.dumps(live['theme']['templates'])
        self.assertFalse(p.noctalia_propagation_sources(live))
        p.patch_noctalia(live, self.appearance(), copy.deepcopy(live))
        self.assertEqual(live['theme']['mode'], 'light')
        self.assertEqual(p.tomlkit.dumps(live['theme']['templates']), baseline)
        live['theme']['templates']['user']['app']['enabled'] = True
        self.assertIn('enabled user templates', p.noctalia_propagation_sources(live))

    def test_each_hook_and_unknown_future_automation_triggers_safe_skip(self):
        cases = ['[hooks]\n'+name+'="recipient-command"' for name in
                 ('colors_changed','theme_mode_changed','wallpaper_changed','future_palette_event')]
        cases += ['[theme.templates.future_catalog]\nselected=["something"]',
                  '[theme.templates.user.app]\noutput_path="~/.config/app/theme"']
        for config in cases:
            with self.subTest(config=config):
                live = self.recipient(config)
                notes = p.patch_noctalia(live, self.appearance(), copy.deepcopy(live))
                self.assertEqual(live['theme']['mode'], 'dark')
                self.assertTrue(any('Noctalia propagation blocked' in n for n in notes))

    def test_exact_default_dry_run_and_apply_preserve_template_hooks(self):
        live = self.recipient()
        baseline = protected(live)
        self.make(n=p.tomlkit.dumps(self.appearance()))
        before = self.nfile.read_bytes(), self.ufile.read_bytes()
        message = p.apply('test', True)
        self.assertIn('Noctalia propagation blocked', message)
        self.assertEqual(before, (self.nfile.read_bytes(), self.ufile.read_bytes()))
        self.assertFalse(self.state.exists())
        message = p.apply('test')
        self.assertIn('theme skipped', message)
        result = p.parse(self.nfile)
        self.assertEqual(result['theme']['mode'], 'dark')
        self.assertEqual(protected(result), baseline)

    def test_explicit_opt_in_dry_run_and_apply_then_next_operation_defaults_safe(self):
        baseline = protected(self.recipient())
        self.make(n=p.tomlkit.dumps(self.appearance()))
        before = self.nfile.read_bytes()
        notice = p.apply('test', True, True)
        self.assertIn('explicitly allowed', notice)
        self.assertEqual(before, self.nfile.read_bytes())
        notice = p.apply('test', allow_noctalia_propagation=True)
        self.assertIn('explicitly allowed', notice)
        current = p.parse(self.nfile)
        self.assertEqual(current['theme']['mode'], 'light')
        self.assertEqual(protected(current), baseline)
        p.effective_noctalia.return_value = copy.deepcopy(current)
        (self.root/'test/noctalia.toml').write_text('[theme]\nmode="dark"\n')
        self.assertIn('theme skipped', p.apply('test', True))
        self.assertEqual(p.parse(self.nfile)['theme']['mode'], 'light')

    def test_restore_preserves_current_template_hooks_and_requires_new_opt_in(self):
        self.recipient()
        self.make(n=p.tomlkit.dumps(self.appearance()))
        p.apply('test', allow_noctalia_propagation=True)
        backup = next((self.state/'backups').iterdir())
        current = p.parse(self.nfile)
        current['theme']['templates']['builtin_ids'] = ['new-recipient-template']
        current['theme']['templates']['user']['my_app']['post_hook'] = 'current-reload'
        current['hooks']['colors_changed'] = 'current-colors'
        current['application_themes']['private_config'] = 'current-app-value'
        self.nfile.write_text(p.tomlkit.dumps(current))
        p.effective_noctalia.return_value = copy.deepcopy(current)
        baseline = protected(current)
        self.assertIn('theme skipped', p.restore(backup.name, True))
        p.restore(backup.name)
        self.assertEqual(p.parse(self.nfile)['theme']['mode'], 'light')
        self.assertEqual(protected(p.parse(self.nfile)), baseline)
        p.effective_noctalia.return_value = p.parse(self.nfile)
        self.assertIn('explicitly allowed', p.restore(backup.name, True, True))
        p.restore(backup.name, allow_noctalia_propagation=True)
        restored = p.parse(self.nfile)
        self.assertEqual(restored['theme']['mode'], 'dark')
        self.assertEqual(protected(restored), baseline)
        snapshot = p.parse(backup/'noctalia-appearance.toml')
        self.assertNotIn('templates', snapshot['theme'])
        self.assertNotIn('hooks', snapshot)

    def test_failure_rollback_never_replaces_concurrent_template_or_hook_edits(self):
        self.recipient()
        self.make(n=p.tomlkit.dumps(self.appearance()))
        count = 0
        def validate(*args):
            nonlocal count
            count += 1
            if count == 2:
                current = p.parse(self.nfile)
                current['theme']['templates']['enable_builtin_templates'] = False
                current['hooks']['colors_changed'] = 'edited-during-apply'
                self.nfile.write_text(p.tomlkit.dumps(current))
                raise p.ProfileError('validation failed')
        p.validate.side_effect = validate
        with self.assertRaisesRegex(p.ProfileError, 'rollback skipped'):
            p.apply('test', allow_noctalia_propagation=True)
        current = p.parse(self.nfile)
        self.assertFalse(current['theme']['templates']['enable_builtin_templates'])
        self.assertEqual(current['hooks']['colors_changed'], 'edited-during-apply')

    def test_cli_opt_in_parsed_for_apply_and_restore_only(self):
        for command in ('apply','restore'):
            with patch.object(sys,'argv',['profilectl',command,'example','--dry-run','--allow-noctalia-propagation']), patch.object(p,command,return_value='VALID') as operation, patch('sys.stdout',new=io.StringIO()):
                self.assertEqual(p.cli(),0)
                operation.assert_called_once_with('example', True, True)
            with patch.object(sys,'argv',['profilectl',command,'example','--dry-run']), patch.object(p,command,return_value='VALID') as operation, patch('sys.stdout',new=io.StringIO()):
                self.assertEqual(p.cli(),0)
                operation.assert_called_once_with('example', True, False)
        with patch.object(sys,'argv',['profilectl','save','example','--allow-noctalia-propagation']), patch('sys.stderr',new=io.StringIO()):
            with self.assertRaises(SystemExit):
                p.cli()

    def test_package_cannot_embed_propagation_consent(self):
        self.make(n='allow_noctalia_propagation=true\n[theme]\nmode="light"\n')
        with self.assertRaises(p.ProfileError):
            p.apply('test')


class TUIPropagationTests(unittest.TestCase):
    def exercise(self, consent, operation='apply'):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            engine = base/'engine.py'
            engine.write_text('''import json,os,sys
from pathlib import Path
args=sys.argv[1:]
with open(os.environ['TEST_ENGINE_LOG'],'a') as output: output.write(json.dumps(args)+'\\n')
if args[0]=='list': print('first\\nsecond')
elif args[0]=='backups': print('snapshot')
elif '--dry-run' in args:
    print('VALID: explicitly allowed' if '--allow-noctalia-propagation' in args else 'VALID: Noctalia propagation blocked')
else: print('SIMULATED; no configs changed')
''')
            gum = base/'gum'
            gum.write_text('''#!/usr/bin/env python3
import os,sys
from pathlib import Path
root=Path(os.environ['TEST_GUM_STATE'])
args=sys.argv[1:]
def next_count(name):
    file=root/name
    n=int(file.read_text()) if file.exists() else 0
    file.write_text(str(n+1))
    return n
if args[0]=='choose':
    header=args[args.index('--header')+1]
    if header.startswith('Dotprofile'):
        n=next_count('menu')
        if n>=int(os.environ['TEST_OPERATIONS']): print('Quit')
        else: print('Switch desktop appearance' if os.environ['TEST_OPERATION']=='apply' else 'Restore from a backup')
    else:
        options=sys.stdin.read().splitlines()
        menu=int((root/'menu').read_text())
        print(options[min(menu-1,len(options)-1)])
elif args[0]=='confirm' and args[1].startswith('Allow Noctalia propagation'):
    assert '--default=false' in args
    assert 'rewrite app configs' in args[1] and 'hooks may run commands' in args[1]
    n=next_count('consent')
    sys.exit(0 if os.environ['TEST_CONSENT'].split(',')[n]=='yes' else 1)
else: print('')
''')
            gum.chmod(0o755)
            env=dict(os.environ, DOTPROFILE_ENGINE=str(engine), PATH=str(base)+os.pathsep+os.environ['PATH'],
                     TEST_ENGINE_LOG=str(base/'calls'), TEST_GUM_STATE=str(base), TEST_CONSENT=consent,
                     TEST_OPERATIONS=str(len(consent.split(','))), TEST_OPERATION=operation)
            result=subprocess.run(['bash',str(ROOT/'tui/dotprofile')], env=env, capture_output=True,text=True,timeout=15)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            import json
            return [json.loads(line) for line in (base/'calls').read_text().splitlines()]

    def test_declining_opt_in_applies_only_safe_plan(self):
        calls=self.exercise('no')
        applies=[args for args in calls if args[0]=='apply']
        self.assertEqual(applies,[['apply','first','--dry-run'],['apply','first']])

    def test_tui_opt_in_applies_selected_plan_and_does_not_persist(self):
        calls=self.exercise('yes,no')
        applies=[args for args in calls if args[0]=='apply']
        self.assertEqual(applies,[['apply','first','--dry-run'],
                                  ['apply','first','--dry-run','--allow-noctalia-propagation'],
                                  ['apply','first','--allow-noctalia-propagation'],
                                  ['apply','second','--dry-run'],['apply','second']])

    def test_restoration_opt_in_uses_same_informed_default_off_choice(self):
        calls=self.exercise('yes','restore')
        restores=[args for args in calls if args[0]=='restore']
        self.assertEqual(restores,[['restore','snapshot','--dry-run'],
                                    ['restore','snapshot','--dry-run','--allow-noctalia-propagation'],
                                    ['restore','snapshot','--allow-noctalia-propagation']])

import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('profilectl',ROOT/'engine/profilectl.py')
p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)

NOCTALIA='''
[plugins]
enabled = ["fixture-vendor/operation", "fixture-vendor/recording"]
[widget.phone]
type = "fixture-vendor/operation:phone"
my_secret_setting = "private"
[widget.leftbracket]
type = "text"
text = "【"
[widget.workspaces]
type = "workspaces"
show_labels = true
[widget.rightbracket]
type = "text"
text = "】"
[widget.clock]
type = "clock"
[widget.network]
type = "network"
[widget.volume]
type = "volume"
[bar.main]
position = "bottom"
thickness = 34
start = ["leftbracket", "workspaces", "rightbracket", "phone", "network"]
center = ["clock"]
end = ["volume"]
[bar.main.dead_zone.actions]
left = "exec phone-operate"
[theme]
mode = "dark"
source = "wallpaper"
[wallpaper.default]
path = ""
[lockscreen]
enabled = true
grace_period_seconds = 0
blur_intensity = 0.2
[shell.animation]
enabled = true
speed = 1.2
'''
UMBRIEL='''
[output.TEST-OUTPUT-1]
mode = "1024x768@60"
workspaces = ["一", "二", "三", "四", "五"]
[keybinds]
"Mod+1" = "workspace:1"
[general]
autostart = ["noctalia"]
[appearance]
border_width = 8
[appearance.blur]
enabled = false
[animation]
enabled = true
[animation.windows_in]
style = "fade"
'''

class ProfileTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.base=Path(self.tmp.name)
        self.root=self.base/'profiles';self.root.mkdir()
        self.state=self.base/'state'
        self.nfile=self.base/'noctalia/settings.toml';self.nfile.parent.mkdir()
        self.ufile=self.base/'umbriel/config.toml';self.ufile.parent.mkdir()
        self.nfile.write_text(NOCTALIA)
        self.ufile.write_text(UMBRIEL)
        self.patch=patch.multiple(p,PROFILE_ROOT=self.root,DEFAULT_ROOT=self.base/'defaults',STATE_ROOT=self.state,NOCTALIA_FILE=self.nfile,UMBRIEL_FILE=self.ufile)
        self.patch.start();self.addCleanup(self.patch.stop)
        self.pc=patch.object(p,'effective_noctalia',return_value=p.tomlkit.parse(NOCTALIA))
        self.pc.start();self.addCleanup(lambda: self.pc.stop())
        self.validate=patch.object(p,'validate',return_value=None)
        self.validate.start();self.addCleanup(self.validate.stop)
        self.reload=patch.object(p,'reload',return_value=[])
        self.reload.start();self.addCleanup(self.reload.stop)
        self.wallpaper_patch=patch.object(p,'wallpaper_set',return_value=None)
        self.wallpaper_patch.start();self.addCleanup(self.wallpaper_patch.stop)

    def make(self, name='test', n='[bar.main]\nthickness=42\nstart=["network"]\ncenter=["clock"]\nend=["volume"]\n[lockscreen]\nblur_intensity=0.7\n',
             u='[appearance]\nborder_width=3\n[animation.windows_in]\nstyle="popin"\n'):
        f=self.root/name;f.mkdir()
        (f/'profile.toml').write_text(f'id="{name}"\nname="Test"\n')
        (f/'noctalia.toml').write_text(n)
        (f/'umbriel.toml').write_text(u)
        return f

    def test_apply_preserves_all_protected_data(self):
        self.make();message=p.apply('test');self.assertIn('Applied',message)
        n=p.parse(self.nfile);u=p.parse(self.ufile)
        self.assertEqual(n['bar']['main']['position'],'bottom')
        self.assertEqual(n['bar']['main']['thickness'],42)
        self.assertEqual(list(n['bar']['main']['start']),['network','phone'])
        self.assertEqual(list(n['bar']['main']['center']),['clock'])
        self.assertEqual(list(n['bar']['main']['end']),['volume'])
        self.assertEqual(n['widget']['phone']['my_secret_setting'],'private')
        self.assertEqual(n['plugins']['enabled'][0],'fixture-vendor/operation')
        self.assertEqual(n['widget']['workspaces']['show_labels'],True)
        self.assertEqual(n['bar']['main']['dead_zone']['actions']['left'],'exec phone-operate')
        self.assertEqual(n['lockscreen']['enabled'],True)
        self.assertEqual(n['lockscreen']['grace_period_seconds'],0)
        self.assertEqual(n['lockscreen']['blur_intensity'],0.7)
        self.assertEqual(list(u['output']['TEST-OUTPUT-1']['workspaces']),['一','二','三','四','五'])
        self.assertEqual(u['output']['TEST-OUTPUT-1']['mode'],'1024x768@60')
        self.assertEqual(u['keybinds']['Mod+1'],'workspace:1')
        self.assertEqual(list(u['general']['autostart']),['noctalia'])
        self.assertEqual(u['appearance']['border_width'],3)
        self.assertEqual(u['animation']['windows_in']['style'],'popin')

    def test_reject_plugin_widget_in_layout(self):
        self.make(n='[bar.main]\nstart=["phone"]\ncenter=[]\nend=[]\n')
        before=self.nfile.read_text()
        with self.assertRaises(p.ProfileError): p.apply('test')
        self.assertEqual(self.nfile.read_text(),before)

    def test_workspace_widget_moves_with_changed_native_counts(self):
        self.make(n='[bar.main]\nstart=["workspaces"]\ncenter=[]\nend=[]\n')
        msg=p.apply('test')
        self.assertNotIn('layout transition skipped', msg)
        bar=p.parse(self.nfile)['bar']['main']
        self.assertEqual(list(bar['start']), ['workspaces','phone'])
        self.assertEqual(list(bar['center']), [])
        self.assertEqual(list(bar['end']), [])

    def test_reject_deadzone_exec(self):
        self.make(n='[bar.main.dead_zone.actions]\nleft="exec rm -rf ~/"\n')
        with self.assertRaises(p.ProfileError):p.apply('test')

    def test_reject_lock_security_bypass(self):
        self.make(n='[lockscreen]\nallow_empty_password = true\n')
        with self.assertRaises(p.ProfileError):p.apply('test')

    def test_reject_umbriel_output_and_keybinds(self):
        self.make(u='[output.TEST-OUTPUT-1]\nmode="1280x720@60"\n')
        with self.assertRaises(p.ProfileError):p.apply('test')
        (self.root/'test'/'umbriel.toml').write_text('[keybinds]\n"Mod+1"="bad"\n')
        with self.assertRaises(p.ProfileError):p.apply('test')

    def test_reject_shader(self):
        self.make(u='[animation.windows_in]\nshader="danger.glsl"\n')
        with self.assertRaises(p.ProfileError):p.apply('test')

    def test_dry_run_no_side_effects(self):
        self.make();old=(self.nfile.read_bytes(),self.ufile.read_bytes())
        self.assertIn('VALID',p.apply('test',True))
        self.assertEqual(old,(self.nfile.read_bytes(),self.ufile.read_bytes()))
        self.assertFalse(self.state.exists())

    def test_native_cross_lane_transition_preserves_plugin(self):
        self.make(n='[bar.main]\nstart=["clock","network"]\ncenter=[]\nend=["volume"]\n')
        output=p.apply('test')
        self.assertNotIn('layout transition skipped',output)
        n=p.parse(self.nfile)
        self.assertEqual(list(n['bar']['main']['center']),[])
        self.assertEqual(list(n['bar']['main']['start']),['clock','network','phone'])

    def test_native_removal_preserves_plugin_lane_and_order(self):
        live=NOCTALIA.replace('"phone", "network"','"phone", "network", "volume"').replace('end = ["volume"]','end = []')
        self.nfile.write_text(live)
        p.effective_noctalia.return_value=p.tomlkit.parse(live)
        self.make(n='[bar.main]\nstart=["volume","network"]\ncenter=["clock"]\nend=[]\n')
        p.apply('test')
        n=p.parse(self.nfile)
        self.assertEqual(list(n['bar']['main']['start']),['volume','network','phone'])
        self.assertEqual(n['widget']['phone'], p.tomlkit.parse(live)['widget']['phone'])

    def test_validation_failure_rollback(self):
        self.make();old=(self.nfile.read_text(),self.ufile.read_text())
        with patch.object(p,'validate',side_effect=p.ProfileError('validation failed')):
            with self.assertRaises(p.ProfileError):p.apply('test')
        self.assertEqual(old,(self.nfile.read_text(),self.ufile.read_text()))

    def test_restore_previous_snapshot(self):
        self.make();p.apply('test')
        self.assertNotEqual(self.nfile.read_text(),NOCTALIA)
        backup=next((self.state/'backups').iterdir())
        p.effective_noctalia.return_value=p.parse(self.nfile)
        self.assertIn('Restored',p.restore(backup.name))
        restored=p.parse(self.nfile)
        original=p.tomlkit.parse(NOCTALIA)
        for lane in p.BAR_SECTIONS:
            self.assertEqual([v for v in restored['bar']['main'][lane] if v != 'phone'],
                             [v for v in original['bar']['main'][lane] if v != 'phone'])
        self.assertIn('phone', restored['bar']['main']['start'])
        self.assertEqual(restored['widget'], original['widget'])
        self.assertEqual(restored['plugins'], original['plugins'])
        self.assertEqual(restored['bar']['main']['thickness'], 34)
        self.assertEqual(self.ufile.read_text(),UMBRIEL)
        self.assertFalse((self.state/'active-profile').exists())

    def test_export_filters_widgets_password_and_monitor(self):
        src=p.tomlkit.parse(NOCTALIA)
        doc=p.clean_noctalia(src)
        result=p.tomlkit.dumps(doc)
        self.assertNotIn('[plugins]',result)
        self.assertIn('[widget.workspaces]',result)
        self.assertIn('[widget.leftbracket]',result)
        self.assertIn('[widget.rightbracket]',result)
        self.assertNotIn('phone',result)
        self.assertIn('workspaces',result)
        self.assertIn('leftbracket',result)
        self.assertNotIn('my_secret_setting',result)
        self.assertNotIn('grace_period_seconds',result)
        self.assertIn('start = ["leftbracket", "workspaces", "rightbracket", "network"]',result)
        umb=p.tomlkit.dumps(p.clean_umbriel(p.tomlkit.parse(UMBRIEL)))
        self.assertNotIn('[output.',umb);self.assertNotIn('keybinds',umb)
        self.assertIn('border_width',umb)

    def test_export_bundle_and_portable_paths(self):
        image=self.base/'mywall.png';image.write_bytes(b'PNGTEST')
        n=NOCTALIA.replace('path = ""',f'path = "{image}"')
        self.pc.stop();self.pc=patch.object(p,'effective_noctalia',return_value=p.tomlkit.parse(n));self.pc.start()
        msg=p.save('layout-a',True)
        self.assertIn('wallpaper files bundled',msg)
        text=(self.root/'layout-a'/'noctalia.toml').read_text()
        self.assertIn('@profile/wallpaper.png',text)
        self.assertNotIn(str(self.base),text)
        self.assertTrue((self.root/'layout-a'/'wallpaper.png').exists())
        self.assertIn(str(self.root/'layout-a'/'wallpaper.png'),p.tomlkit.dumps(p.prepare_profile('layout-a')[0]))
        self.assertNotIn('phone',text)
        self.assertIn('[widget.workspaces]',text)
        self.assertTrue((self.root/'layout-a'/'workspace.toml').exists())
        self.assertIn('一', (self.root/'layout-a'/'workspace.toml').read_text())

    def test_export_does_not_leak_wallpaper_path_by_default(self):
        image=self.base/'private-wall.png';image.write_bytes(b'PNGTEST')
        n=NOCTALIA.replace('path = ""',f'path = "{image}"')
        self.pc.stop();self.pc=patch.object(p,'effective_noctalia',return_value=p.tomlkit.parse(n));self.pc.start()
        p.save('safest')
        self.assertNotIn(str(image),(self.root/'safest'/'noctalia.toml').read_text())
        self.assertFalse((self.root/'safest'/'wallpaper.png').exists())

    def test_install_rejects_untrusted_content(self):
        f=self.make(n='[widget.phone]\ntype="fixture-vendor/operation:phone"\n')
        dest=self.base/'another'; dest.mkdir()
        self.root=dest
        with patch.object(p,'PROFILE_ROOT',dest):
            with self.assertRaises(p.ProfileError):p.install_profile(f)

    def test_import_workspace_indicator_styles_and_five_names(self):
        folder=self.make(n='''[bar.main]
start=["leftbracket", "workspaces", "rightbracket", "network"]
center=["clock"]
end=["volume"]
[widget.workspaces]
type="workspaces"
style="minimal"
show_labels=true
label_source="name"
font_scale=1.35
focused_color="on_surface"
[widget.leftbracket]
type="text"
text="【"
[widget.rightbracket]
type="text"
text="】"
''')
        (folder/'workspace.toml').write_text('''[workspace_indicator]
labels=["1", "2", "3", "4", "5"]
''')
        result=p.apply('test')
        self.assertIn('Applied',result)
        n=p.parse(self.nfile);u=p.parse(self.ufile)
        self.assertEqual(n['widget']['workspaces']['style'],'minimal')
        self.assertEqual(n['widget']['workspaces']['label_source'],'name')
        self.assertEqual(n['widget']['workspaces']['font_scale'],1.35)
        self.assertEqual(list(n['bar']['main']['start']),['leftbracket','workspaces','rightbracket','phone','network'])
        self.assertEqual(n['plugins']['enabled'][0],'fixture-vendor/operation')
        self.assertEqual(list(u['output']['TEST-OUTPUT-1']['workspaces']),['1','2','3','4','5'])
        self.assertEqual(u['output']['TEST-OUTPUT-1']['mode'],'1024x768@60')
        self.assertEqual(u['keybinds']['Mod+1'],'workspace:1')

    def test_five_labels_skip_dynamic_or_different_count(self):
        folder=self.make()
        (folder/'workspace.toml').write_text('[workspace_indicator]\nlabels=["一","二","三","四","五"]\n')
        old=UMBRIEL.replace('workspaces = ["一", "二", "三", "四", "五"]','min_workspaces = 7')
        self.ufile.write_text(old)
        result=p.apply('test')
        self.assertIn('workspace labels skipped',result)
        self.assertEqual(p.parse(self.ufile)['output']['TEST-OUTPUT-1']['min_workspaces'],7)
        self.assertEqual(p.parse(self.ufile)['output']['TEST-OUTPUT-1']['mode'],'1024x768@60')

    def test_import_rejects_invalid_workspace_inventory(self):
        folder=self.make()
        (folder/'workspace.toml').write_text('[workspace_indicator]\nlabels=["一","二","三","四","五","六"]\n')
        with self.assertRaises(p.ProfileError):p.apply('test')
        (folder/'workspace.toml').write_text('[workspace_indicator]\nlabels=["一","二","三","四","五"]\n[output.TEST-OUTPUT-1]\nmode="123x123"\n')
        with self.assertRaises(p.ProfileError):p.apply('test')

    def test_unrelated_text_not_exported(self):
        source=NOCTALIA.replace('[widget.phone]', '[widget.private_note]\ntype="text"\ntext="MY_PRIVATE_INFO"\n[widget.phone]')
        source=source.replace('"phone", "network"', '"phone", "private_note", "network"')
        filtered=p.tomlkit.dumps(p.clean_noctalia(p.tomlkit.parse(source)))
        self.assertNotIn('MY_PRIVATE_INFO', filtered)
        self.assertNotIn('private_note', filtered)
        self.assertNotIn('phone', filtered)

    def test_reject_fake_workspace_widget_plugin(self):
        folder=self.make(n='''[bar.main]
start=["workspaces"]
center=[]
end=[]
[widget.workspaces]
type="bad/remote:plugin"
''')
        with self.assertRaises(p.ProfileError):p.apply('test')

    def test_reject_disallowed_text_or_bracket_nonadjacent(self):
        folder=self.make(n='''[bar.main]
start=["leftbracket","clock","workspaces"]
center=[]
end=[]
[widget.leftbracket]
type="text"
text="CUSTOM PRIVATE CONTENT"
''')
        with self.assertRaises(p.ProfileError):p.apply('test')

    def test_profile_save_workspace_labels_and_styles(self):
        output=p.save('layout-a')
        self.assertIn('5 workspace labels captured',output)
        path=self.root/'layout-a'
        labels=p.parse(path/'workspace.toml')['workspace_indicator']['labels']
        self.assertEqual(list(labels),['一','二','三','四','五'])
        n=p.parse(path/'noctalia.toml')
        self.assertEqual(n['widget']['workspaces']['show_labels'],True)
        self.assertEqual(n['widget']['leftbracket']['text'],'【')
        self.assertNotIn('phone', (path/'noctalia.toml').read_text())

if __name__=='__main__':unittest.main()

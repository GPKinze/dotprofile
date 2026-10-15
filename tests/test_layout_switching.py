"""v0.6.1: native layout transitions, with recipient-owned plugin invariants."""
import copy
import itertools
import unittest
from collections import Counter

import test_profilectl as legacy

p, ROOT = legacy.p, legacy.ROOT
MAIN = (ROOT/'tests/fixtures/main-bar.toml').read_text()


def fixture(name):
    return p.parse(ROOT/'tests/fixtures'/f'{name}-layout.toml')


class LayoutTests(unittest.TestCase):
    setUp = legacy.ProfileTests.setUp
    make = legacy.ProfileTests.make

    def current(self, source=MAIN):
        doc = p.tomlkit.parse(source) if isinstance(source, str) else copy.deepcopy(source)
        self.nfile.write_text(p.tomlkit.dumps(doc))
        p.effective_noctalia.return_value = doc
        return doc

    def plugins(self, doc):
        widgets = p.section(doc, 'widget')
        ids = {wid for wid in widgets if p.approved_widget(wid, widgets) is None}
        return {
            'definitions': {wid: widgets[wid].as_string() for wid in ids},
            'installation': doc.get('plugins', p.tomlkit.table()).unwrap(),
            'settings': doc.get('plugin_settings', p.tomlkit.table()).unwrap(),
            'lanes': {name: {lane: [v for v in bar.get(lane, []) if v in ids or
                                   v.startswith('group:') and not p.safe_group(p.group_index(bar).get(v[6:], {}), widgets)]
                             for lane in p.BAR_SECTIONS}
                      for name, bar in p.section(doc, 'bar').items() if p.table(bar)},
            'capsules': {name: {gid: group.as_string() for gid, group in p.group_index(bar).items()
                               if not p.safe_group(group, widgets)}
                         for name, bar in p.section(doc, 'bar').items() if p.table(bar)},
        }

    def assert_native_layout(self, actual, requested):
        widgets = p.section(actual, 'widget')
        for name, bar in requested['bar'].items():
            result = actual['bar'][name]
            groups = p.group_index(result)
            for lane in p.BAR_SECTIONS:
                native = [v for v in result[lane] if (
                    v.startswith('group:') and p.safe_group(groups.get(v[6:], {}), widgets)) or (
                    not v.startswith('group:') and p.approved_widget(v, widgets))]
                self.assertEqual(native, list(bar[lane]))
            for key in p.BAR_KEYS & set(bar):
                self.assertEqual(result[key], bar[key], key)
            for gid, group in p.group_index(bar).items():
                for key, value in group.items():
                    self.assertEqual(groups[gid][key], value, (gid, key))
        for wid, props in requested['widget'].items():
            for key, value in props.items():
                self.assertEqual(p.widget_type(wid, widgets) if key == 'type' else widgets[wid][key], value)

    def transition(self, live, profile):
        before = copy.deepcopy(live)
        protected = self.plugins(before)
        notes = p.patch_noctalia(live, profile, before)
        self.assertFalse(notes, notes)
        self.assertEqual(self.plugins(live), protected)
        self.assert_native_layout(live, profile)
        return live

    def test_layout_a_layout_b_layout_a_apply_roundtrip(self):
        live = self.current()
        original = self.plugins(live)
        for name in ('layout-a', 'layout-b'):
            self.make(name, n=p.tomlkit.dumps(fixture(name)), u='')
        for name in ('layout-a', 'layout-b', 'layout-a'):
            with self.subTest(profile=name):
                p.effective_noctalia.return_value = p.parse(self.nfile)
                message = p.apply(name)
                self.assertNotIn('layout transition skipped', message)
                live = p.parse(self.nfile)
                self.assert_native_layout(live, fixture(name))
                self.assertEqual(self.plugins(live), original)
        refs = [v for lane in p.BAR_SECTIONS for v in live['bar']['Main'][lane]]
        self.assertEqual(Counter(refs)['bracket_open'], 2)
        self.assertEqual(Counter(refs)['bracket_close'], 2)
        self.assertEqual(p.parse(self.ufile)['keybinds'], p.tomlkit.parse(legacy.UMBRIEL)['keybinds'])

    def test_cold_layout_b_adds_missing_brackets_and_capsule_members(self):
        live = fixture('layout-b')
        live['widget']['future'] = {'type': 'future/vendor:new-plugin', 'private': 'keep'}
        live['bar']['Main']['end'].insert(1, 'future')
        self.transition(live, fixture('layout-a'))
        for wid in ('bracket_open','bracket_close'):
            self.assertEqual(live['widget'][wid]['type'], 'text')
        self.assertEqual(p.widget_type('audio_visualizer', live['widget']), 'audio_visualizer')

    def test_missing_native_alias_inside_new_group_is_created(self):
        live = self.current()
        profile = fixture('layout-b')
        profile['bar']['Main']['capsule_group'][0]['members'].append('new-volume')
        profile['widget']['new-volume'] = {'type': 'volume', 'font_scale': 1.2}
        self.transition(live, profile)
        self.assertEqual(live['widget']['new-volume']['type'], 'volume')

    def test_duplicate_native_and_protected_references_keep_multiplicity(self):
        live = self.current()
        live['bar']['Main']['end'].extend(['status','bar','status'])
        profile = fixture('layout-b')
        profile['bar']['Main']['start'] = ['clock','clock','weather']
        profile['bar']['Main']['end'].extend(['volume','volume'])
        self.transition(live, profile)
        self.transition(live, fixture('layout-a'))

    def test_reused_mixed_group_id_skips_entire_layout_and_shared_styles(self):
        live = self.current(MAIN.replace('"clock", "audio_visualizer", "weather"', '"clock", "status", "weather"'))
        profile = fixture('layout-b')
        profile['widget']['clock']['font_scale'] = 2.0
        before = copy.deepcopy(live)
        notes = p.patch_noctalia(live, profile, before)
        self.assertTrue(any('protected capsule' in n or 'protected membership' in n for n in notes))
        for lane in p.BAR_SECTIONS:
            self.assertEqual(live['bar']['Main'][lane], before['bar']['Main'][lane])
        self.assertEqual(self.plugins(live), self.plugins(before))
        self.assertEqual(p.section(live,'widget','clock'), p.section(before,'widget','clock'))

    def test_separate_plugin_capsule_preserved_beside_new_native_capsule(self):
        live = self.current()
        row = p.tomlkit.table()
        row.update({'id': 'private', 'members': ['status','bar','recorder_2'], 'radius': 19, 'future_private': 'keep'})
        live['bar']['Main']['capsule_group'].append(row)
        live['bar']['Main']['end'] = ['volume']
        live['bar']['Main']['center'].insert(0, 'group:private')
        self.transition(live, fixture('layout-b'))
        self.transition(live, fixture('layout-a'))

    def test_normalized_effective_export_does_not_rewrite_protected_source_rows(self):
        live = self.current()
        raw = p.tomlkit.parse('[[capsule_group]]\nid="private" # keep this comment\nmembers=["status", "bar"]\nfuture_private="keep"\n')['capsule_group'][0]
        live['bar']['Main']['capsule_group'].append(raw)
        live['bar']['Main']['end'] = ['volume', 'recorder_2']
        live['bar']['Main']['center'].append('group:private')
        protected = self.plugins(live)
        effective = copy.deepcopy(live)
        effective['bar']['Main']['capsule_group'][1]['accordion'] = False
        effective['bar']['Main']['capsule_group'][1]['padding'] = 6.0
        notes = p.patch_noctalia(live, fixture('layout-b'), effective)
        self.assertFalse(notes)
        self.assertEqual(self.plugins(live), protected)
        self.assert_native_layout(live, fixture('layout-b'))

    def test_native_definition_shared_with_other_bar_mixed_capsule_is_frozen(self):
        live = self.current()
        live['bar']['Other'] = {'start': [], 'center': ['group:mixed'], 'end': [],
                                'capsule_group': [{'id':'mixed', 'members':['status','workspaces']}]}
        before = copy.deepcopy(live)
        notes = p.patch_noctalia(live, fixture('layout-b'), before)
        self.assertTrue(any('protected capsule' in n for n in notes))
        self.assertEqual(live['widget']['workspaces'], before['widget']['workspaces'])
        self.assertEqual(live['bar']['Other'], before['bar']['Other'])
        self.assertEqual(self.plugins(live), self.plugins(before))

    def test_native_looking_plugin_alias_prevents_retargeting(self):
        live = self.current()
        live['widget']['clock'] = {'type':'new/unknown:clock', 'private':'keep'}
        before = copy.deepcopy(live)
        notes = p.patch_noctalia(live, fixture('layout-b'), before)
        self.assertTrue(any('layout transition skipped' in n for n in notes))
        self.assertEqual(live['widget']['clock'], before['widget']['clock'])
        self.assertEqual(self.plugins(live), self.plugins(before))

    def test_existing_native_alias_conflicting_type_skips_creation(self):
        live = self.current()
        live['widget']['new-volume'] = {'type':'clock', 'format':'HH'}
        profile = fixture('layout-b')
        profile['bar']['Main']['end'].append('new-volume')
        profile['widget']['new-volume'] = {'type':'volume'}
        before = copy.deepcopy(live)
        notes = p.patch_noctalia(live, profile, before)
        self.assertTrue(any('conflicting resolved type' in n for n in notes))
        self.assertEqual(live['bar']['Main']['end'], before['bar']['Main']['end'])
        self.assertEqual(live['widget']['new-volume'], before['widget']['new-volume'])

    def test_unresolved_widget_id_is_not_claimed_by_profile(self):
        live = self.current()
        live['bar']['Main']['end'].append('future-instance')
        profile = fixture('layout-b')
        profile['bar']['Main']['end'].append('future-instance')
        profile['widget']['future-instance'] = {'type':'volume'}
        before = copy.deepcopy(live)
        notes = p.patch_noctalia(live, profile, before)
        self.assertTrue(any('protected' in n for n in notes))
        self.assertNotIn('future-instance', live['widget'])
        self.assertEqual(live['bar']['Main']['end'], before['bar']['Main']['end'])

    def test_dangling_group_is_preserved_but_cannot_be_claimed(self):
        live = self.current()
        live['bar']['Main']['center'].append('group:future')
        before = copy.deepcopy(live)
        notes = p.patch_noctalia(live, fixture('layout-b'), before)
        self.assertFalse(notes)
        self.assertEqual(list(live['bar']['Main']['center']), ['group:g1','group:future'])
        profile = fixture('layout-b')
        profile['bar']['Main']['capsule_group'][0]['id'] = 'future'
        profile['bar']['Main']['center'] = ['group:future']
        before = copy.deepcopy(live)
        notes = p.patch_noctalia(live, profile, before)
        self.assertTrue(any('reused ID' in n for n in notes))
        self.assertEqual(live['bar']['Main']['capsule_group'], before['bar']['Main']['capsule_group'])

    def test_removed_placements_retain_private_builtin_settings(self):
        live = self.current()
        live['widget']['bracket_open']['actions'] = {'left':'exec private-command'}
        live['bar']['Main']['capsule_group'][0]['future_setting'] = 'private'
        before = copy.deepcopy(live['widget']['bracket_open'])
        self.transition(live, fixture('layout-b'))
        self.assertEqual(live['widget']['bracket_open'], before)
        self.transition(live, fixture('layout-a'))
        self.assertEqual(live['bar']['Main']['capsule_group'][0]['future_setting'], 'private')

    def test_new_native_group_id_keeps_old_recipient_rows(self):
        live = self.current()
        profile = fixture('layout-b')
        profile['bar']['Main']['capsule_group'][0]['id'] = 'g2'
        profile['bar']['Main']['center'] = ['group:g2']
        old = copy.deepcopy(live['bar']['Main']['capsule_group'][0])
        self.transition(live, profile)
        self.assertEqual(live['bar']['Main']['capsule_group'][0], old)
        self.transition(live, fixture('layout-a'))

    def test_incomplete_lane_transaction_skips_without_creating_instances(self):
        live = self.current()
        profile = p.tomlkit.parse('[bar.Main]\nstart=["new-volume"]\n[widget.new-volume]\ntype="volume"\n')
        before = copy.deepcopy(live)
        notes = p.patch_noctalia(live, profile, before)
        self.assertTrue(any('all three lanes' in n for n in notes))
        self.assertEqual(live['bar']['Main']['start'], before['bar']['Main']['start'])
        self.assertNotIn('new-volume', live['widget'])

    def test_malformed_existing_groups_skip_with_warning(self):
        live = self.current()
        live['bar']['Main']['capsule_group'].append(copy.deepcopy(live['bar']['Main']['capsule_group'][0]))
        before = copy.deepcopy(live)
        notes = p.patch_noctalia(live, fixture('layout-b'), before)
        self.assertTrue(any('unsafe existing layout' in n for n in notes))
        self.assertEqual(live, before)

    def test_all_position_pairs_save_apply_geometry_styles_and_native_layout(self):
        # Noctalia derives orientation from position. Thickness is cross-axis;
        # margin_ends/padding are main-axis for both horizontal and vertical bars.
        for source, target in itertools.permutations(('top','bottom','left','right'), 2):
            with self.subTest(source=source, target=target):
                live = self.current()
                live['bar']['Main']['position'] = source
                original = self.plugins(live)
                self.current(live)
                p.save(f'source-{source}-{target}')
                profile = fixture('layout-b')
                bar = profile['bar']['Main']
                profile['widget']['clock']['vertical_format'] = '%H\n%M'
                bar.update({'position': target, 'thickness': 48, 'margin_ends': 80,
                            'margin_edge': 8, 'margin_opposite_edge': 12, 'padding': 10,
                            'widget_spacing': 4, 'background_opacity': 0.75, 'border_width': 2.0,
                            'radius': 20, 'capsule_thickness': 0.8, 'concave_edge_corners': False})
                group = bar['capsule_group'][0]
                group['id'] = 'vertical' if target in ('left','right') else 'horizontal'
                bar['center'] = ['group:'+group['id']]
                self.make(f'target-{source}-{target}', n=p.tomlkit.dumps(profile), u='')
                p.apply(f'target-{source}-{target}')
                applied = p.parse(self.nfile)
                self.assert_native_layout(applied, profile)
                self.assertEqual(self.plugins(applied), original)
                p.effective_noctalia.return_value = applied
                p.save(f'captured-{source}-{target}')
                saved, _, _ = p.prepare_profile(f'captured-{source}-{target}')
                self.assert_native_layout(applied, saved)
                p.apply(f'source-{source}-{target}')
                restored = p.parse(self.nfile)
                expected, _, _ = p.prepare_profile(f'source-{source}-{target}')
                self.assert_native_layout(restored, expected)
                self.assertEqual(restored['bar']['Main']['position'], source)
                self.assertEqual(self.plugins(restored), original)

    def test_unsafe_group_layout_can_still_move_containing_bar(self):
        live = self.current(MAIN.replace('"clock", "audio_visualizer", "weather"', '"status", "bar"'))
        profile = fixture('layout-b')
        profile['bar']['Main']['position'] = 'left'
        before = copy.deepcopy(live)
        notes = p.patch_noctalia(live, profile, before)
        self.assertTrue(any('layout transition skipped' in n for n in notes))
        self.assertEqual(live['bar']['Main']['position'], 'left')
        self.assertEqual(self.plugins(live), self.plugins(before))
        for lane in p.BAR_SECTIONS:
            self.assertEqual(live['bar']['Main'][lane], before['bar']['Main'][lane])

    def test_all_approved_native_types_can_create_aliases_without_plugin_names(self):
        live = self.current()
        profile = fixture('layout-b')
        aliases = ['fresh-'+kind for kind in sorted(p.NATIVE_WIDGET_TYPES | {'workspaces'})]
        profile['bar']['Main']['start'] = aliases
        for wid, kind in zip(aliases, sorted(p.NATIVE_WIDGET_TYPES | {'workspaces'})):
            profile['widget'][wid] = {'type':kind, 'font_scale':1.1}
        profile = p.clean_noctalia(profile)
        p.clean_noctalia(profile, True)
        self.transition(live, profile)
        for wid in aliases:
            self.assertEqual(live['widget'][wid]['type'], profile['widget'][wid]['type'])

    def test_monitor_only_plugin_prevents_bar_enablement_change(self):
        live = fixture('layout-b')
        live['widget']['future'] = {'type':'future/vendor:plugin'}
        live['bar']['Main']['monitor'] = {'DP-1': {'start':['future'], 'center':[], 'end':[]}}
        before = copy.deepcopy(live)
        profile = fixture('layout-b')
        profile['bar']['Main']['enabled'] = False
        notes = p.patch_noctalia(live, profile, before)
        self.assertTrue(any('enabled skipped' in n for n in notes))
        self.assertTrue(any('per-monitor layout' in n for n in notes))
        self.assertTrue(live['bar']['Main']['enabled'])
        self.assertEqual(live['bar']['Main']['monitor'], before['bar']['Main']['monitor'])

    def test_monitor_geometry_preserved_with_informative_warning(self):
        live = self.current()
        live['bar']['Main']['monitor'] = {'DP-1': {'position':'bottom', 'thickness':34}}
        before = copy.deepcopy(live)
        profile = fixture('layout-b')
        profile['bar']['Main']['position'] = 'left'
        profile['bar']['Main']['thickness'] = 48
        notes = p.patch_noctalia(live, profile, before)
        self.assertTrue(any('monitor overrides retained' in n and 'position' in n and 'thickness' in n for n in notes))
        self.assertEqual(live['bar']['Main']['monitor'], before['bar']['Main']['monitor'])
        self.assertEqual(live['bar']['Main']['position'], 'left')
        self.assertEqual(self.plugins(live), self.plugins(before))

    def test_multiline_clock_formats_export_import_without_relaxing_other_fields(self):
        profile = fixture('layout-b')
        for key in ('format','vertical_format','tooltip_format'):
            profile['widget']['clock'][key] = '%H\n%M'
        clean = p.clean_noctalia(profile, True)
        self.assertEqual(clean['widget']['clock']['vertical_format'], '%H\n%M')
        for bad in ('%H\n$(exec bad)', '%H\n/home/private', '%H\n${SECRET}', '%H\n`command`'):
            profile['widget']['clock']['vertical_format'] = bad
            with self.assertRaises(p.ProfileError):
                p.clean_noctalia(profile, True)
        profile = fixture('layout-b')
        profile['widget']['launcher']['glyph'] = 'app\nwindow'
        with self.assertRaises(p.ProfileError):
            p.clean_noctalia(profile, True)
        self.assertFalse(p.config_name('name\nother'))

    def test_restore_uses_current_plugins_and_original_native_layout(self):
        self.current()
        self.make('layout-b', n=p.tomlkit.dumps(fixture('layout-b')), u='')
        p.apply('layout-b')
        snapshot = next((self.state/'backups').iterdir())
        current = p.parse(self.nfile)
        current['widget']['future'] = {'type':'unseen/vendor:plugin', 'custom':'new'}
        current['bar']['Main']['end'].insert(1, 'future')
        self.current(current)
        protected = self.plugins(current)
        result = p.restore(snapshot.name)
        self.assertIn('Restored', result)
        restored = p.parse(self.nfile)
        self.assertEqual(self.plugins(restored), protected)
        self.assert_native_layout(restored, p.clean_noctalia(p.tomlkit.parse(MAIN)))

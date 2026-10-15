#!/usr/bin/env python3
"""Check the published RDR package through a real CLI import into a temp library.

No native desktop commands are needed. Any attempted external command is
trapped, and all library/config/state paths are redirected into a temp folder.
"""
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('rdr_profilectl', ROOT/'engine/profilectl.py')
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)


def run():
    source = ROOT/'profiles/rdr'
    assert {file.name for file in source.iterdir()} == {
        'profile.toml', 'noctalia.toml', 'umbriel.toml', 'workspace.toml', 'README.md'}
    p.manifest_for_folder(source, 'rdr')
    appearance, _, workspace = p.read_profile_folder(source)
    assert 'wallpaper' not in appearance
    assert 'wallpaper' not in p.section(appearance, 'lockscreen')
    assert '@profile/' not in p.tomlkit.dumps(appearance)
    group = p.group_index(appearance['bar']['Main'])['g1']
    assert list(group['members']) == ['launcher', 'workspaces']
    assert 'radius' not in group
    assert list(appearance['bar']['Main']['center']) == ['group:g1']
    assert list(workspace['workspace_indicator']['labels']) == ['Ⅰ', 'Ⅱ', 'Ⅲ', 'Ⅳ', 'Ⅴ']
    assert 'rdr' not in p.OFFICIAL_DEFAULTS
    with tempfile.TemporaryDirectory(prefix='dotprofile-rdr-import-') as name:
        temp = Path(name)
        library, defaults, state = temp/'profiles', temp/'defaults', temp/'manager-state'
        nfile, ufile = temp/'noctalia.toml', temp/'umbriel.toml'
        nfile.write_text('[wallpaper.default]\npath="color:#123456"\n[hooks]\nwallpaper_changed="keep"\n')
        ufile.write_text('[keybinds]\n"Mod+1"="workspace:1"\n')
        before = nfile.read_bytes(), ufile.read_bytes()
        bins = temp/'bin'
        bins.mkdir()
        log = temp/'unexpected-command'
        for program in ('noctalia', 'umbriel'):
            executable = bins/program
            executable.write_text('#!'+sys.executable+'\nfrom pathlib import Path\n'
                                  'Path('+repr(str(log))+').write_text("unexpected desktop command")\nraise SystemExit(99)\n')
            executable.chmod(0o700)
        env = dict(os.environ, NDP_PROFILE_ROOT=str(library), NDP_DEFAULT_ROOT=str(defaults),
                   NDP_STATE_ROOT=str(state), NDP_NOCTALIA_FILE=str(nfile), NDP_UMBRIEL_FILE=str(ufile),
                   NDP_NOCTALIA_EXPORT_FILE='', PATH=str(bins)+os.pathsep+os.environ['PATH'])
        def command(*args):
            return subprocess.run([sys.executable, str(ROOT/'engine/profilectl.py'), *args],
                                  env=env, capture_output=True, text=True, timeout=30)
        result = command('install-profile', str(source))
        assert result.returncode == 0, result.stderr+result.stdout
        assert 'Installed Personal rdr; not yet applied' in result.stdout
        installed = library/'rdr'
        for file in source.iterdir():
            assert (installed/file.name).read_bytes() == file.read_bytes(), file.name
        listed = command('list')
        assert listed.returncode == 0 and listed.stdout.splitlines() == ['personal:rdr'], listed.stdout+listed.stderr
        labels = command('list', '--labels')
        assert labels.returncode == 0 and labels.stdout.splitlines() == ['Personal: rdr'], labels.stdout+labels.stderr
        replacement = command('install-profile', str(source))
        assert replacement.returncode != 0 and 'Personal profile exists' in replacement.stderr
        for file in source.iterdir():
            assert (installed/file.name).read_bytes() == file.read_bytes(), file.name
        assert (nfile.read_bytes(), ufile.read_bytes()) == before
        assert not defaults.exists()
        assert not (state/'active-profile').exists() and not (state/'backups').exists()
        assert not (state/'profile-backups').exists() and not log.exists()
    print('PASS: wallpaper-free RDR CLI import, Personal classification, automatic g1 radius, '
          'collision refusal, unchanged configs; temporary library only; no desktop commands')


if __name__ == '__main__':
    run()

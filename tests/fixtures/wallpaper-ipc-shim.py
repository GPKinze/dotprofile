"""Test-only CLI adapter: real offline validators/exports, simulated IPC only.

The caller creates executable wrappers named noctalia and umbriel around this
file, with a private DOTPROFILE_TEST_ROOT. No msg command is ever forwarded.
"""
import json
import os
from pathlib import Path
import sys
import tomlkit

root = Path(os.environ['DOTPROFILE_TEST_ROOT']).resolve()
program, *args = sys.argv[1:]
if args[:1] == ['config']:
    real = os.environ['DOTPROFILE_TEST_REAL_'+program.upper()]
    os.execv(real, [real, *args])
if args[:1] != ['msg']:
    raise SystemExit('test adapter refuses commands outside config/msg')
with (root/'ipc-log.jsonl').open('a') as log:
    log.write(json.dumps([program, *args])+'\n')
if args[1:] == ['config-reload']:
    raise SystemExit(0)
if program != 'noctalia' or args[1:2] != ['wallpaper-set'] or len(args) != 3:
    raise SystemExit('unsupported simulated IPC command')
settings = Path(os.environ['NDP_NOCTALIA_FILE']).resolve()
assert settings.is_relative_to(root), 'test adapter refuses non-isolated writes'
path = args[2]
if not path.startswith('color:') and not Path(path).is_file():
    raise SystemExit('wallpaper image missing')
doc = tomlkit.parse(settings.read_text())
wallpaper = doc.setdefault('wallpaper', {})
for field in ('default','last'):
    wallpaper.setdefault(field, {})['path'] = path
monitors = wallpaper.setdefault('monitors', {})
mode = os.environ.get('DOTPROFILE_TEST_IPC_MODE', 'success')
for connector in ('DP-7','eDP-2','New-Output-4'):
    monitors.setdefault(connector, {})['path'] = path
    if mode == 'partial-failure':
        break
# Model Noctalia's own serialization without changing unrelated field values.
settings.write_text(tomlkit.dumps(doc.unwrap()))
if mode == 'partial-failure':
    print('simulated session failure after one output', file=sys.stderr)
    raise SystemExit(1)
print('simulated wallpaper applied')

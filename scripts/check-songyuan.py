#!/usr/bin/env python3
"""Validate board identity, production boot arguments and measured input geometry."""
from pathlib import Path
import json
import re
import tomllib
ROOT = Path(__file__).resolve().parents[1]
board = tomllib.loads((ROOT/'board.toml').read_text(encoding='utf-8'))
hardware = json.loads((ROOT/'scripts/data/songyuan-hardware.json').read_text(encoding='utf-8'))
args = board['payload']['kernel_args']
if board['board']['name'] != 'songyuan' or board['board']['description'] != 'Redmi K100 Pro Max':
    raise SystemExit('Wrong board identity')
required = {'myron-touch=5','myron-gpu=11','myron-gpu-metal=1','sheng-touch-hid=1','myron-clear-sigp=1','myron-ipi-clearpend=1'}
if not required <= set(args):
    raise SystemExit('Missing production driver argument or paired IPI fix')
if any(arg.startswith(('boot-progress=', 'boot-diag-', 'pandora_reboot_after=', 'armcpu-diagnostics=')) or '-probe=' in arg for arg in args):
    raise SystemExit('A diagnostic/probe/timed-reset argument entered the production profile')
if board['payload'].get('panic_screen'):
    raise SystemExit('Entry/panic-screen patching is enabled')
if 'first_lba' in board['userdata'] or 'last_lba' in board['userdata']:
    raise SystemExit('An inherited absolute storage write window is present')
header = (ROOT/'package/MyronTouchBoard.h').read_text(encoding='utf-8')
for key, actual in [('MT_GPIO_AVDD',hardware['touch']['avdd_gpio']),('MT_GPIO_RESET',hardware['touch']['reset_gpio']),('MT_GPIO_IRQ',hardware['touch']['irq_gpio']),('MT_PANEL_W',hardware['touch']['width']),('MT_PANEL_H',hardware['touch']['height'])]:
    found = re.search(r'^#define\s+'+key+r'\s+(\d+)\b',header,re.M)
    if not found or int(found[1]) != actual:
        raise SystemExit('Touch constant differs from captured songyuan hardware: '+key)
print('PASS: songyuan identity, captured touch geometry, production touch/A840/SMP arguments, no probes or inherited disk offsets')

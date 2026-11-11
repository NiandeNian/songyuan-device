#!/usr/bin/env python3
"""Build shared driver state without a boot diagnostic page."""
from pathlib import Path
import json
import subprocess
ROOT = Path(__file__).resolve().parents[1]
record = json.loads((ROOT/'build/xnu/ios-obj/DEVELOPMENT_ARM64_BCM2837/osfmk/DEVELOPMENT/startup.o.json').read_text().strip().rstrip(','))
out = ROOT/'build/songyuan-runtime-state'; out.mkdir(parents=True, exist_ok=True)
args = record['arguments']; cmd = []; i = 0
while i < len(args):
    value = args[i]
    if value == record['file']: cmd.append(str(ROOT/'kits/songyuan/SongyuanRuntimeState.c'))
    elif value == '-o': cmd += ['-o', str(out/'state.o')]; i += 1
    elif value in ('-MF','-MT','-MJ'): i += 1
    elif value not in ('-MD','-MP'): cmd.append(value)
    i += 1
subprocess.run(cmd, cwd=record['directory'], check=True)
subprocess.run(['xcrun','ar','rcs',str(out/'libSongyuanRuntimeState.a'),str(out/'state.o')],check=True)

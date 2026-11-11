#!/usr/bin/env python3
"""Pack only the production plugin, Turnip and publish marker for the existing NGPUADD2 loader."""
import argparse
from pathlib import Path
import struct
import zlib

ROOT = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('output', type=Path)
a = p.parse_args()
bundle = ROOT / 'build/adreno-metal-plugin/NativeAdrenoMetal.bundle'
if not (bundle / 'NativeAdrenoMetal').is_file() or not (bundle / 'libvulkan_freedreno.dylib').is_file():
    raise SystemExit('Build the production plugin first')
if a.output.exists():
    raise SystemExit('Refuse to overwrite '+str(a.output))
files = [('addons/NativeAdrenoMetal.publish', 0o644, b'1\n')]
for path in sorted(p for p in bundle.rglob('*') if p.is_file()):
    if path.is_symlink():
        raise SystemExit('No symlinks in the bundle')
    name = 'addons/NativeAdrenoMetal.bundle/'+path.relative_to(bundle).as_posix()
    mode = 0o755 if path.name in ('NativeAdrenoMetal', 'libvulkan_freedreno.dylib') else 0o644
    files.append((name, mode, path.read_bytes()))
pad = lambda data: data + bytes(-len(data) % 8)
body = b''
for name, mode, data in files:
    encoded = name.encode() + b'\0'
    if len(encoded) > 160 or '..' in name.split('/'):
        raise SystemExit('Bad addon path: '+name)
    packed = zlib.compress(data, 9)
    body += struct.pack('<IIQQ', len(encoded), mode, len(data), len(packed)) + pad(encoded) + pad(packed)
a.output.parent.mkdir(parents=True, exist_ok=True)
a.output.write_bytes(b'NGPUADD2'+struct.pack('<IIQ', len(files), 0, 24+len(body))+body)
print(f'Packed {len(files)} production files into {a.output}; no daemon or launchd override')

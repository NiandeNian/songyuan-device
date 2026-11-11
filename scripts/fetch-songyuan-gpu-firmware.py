#!/usr/bin/env python3
"""Fetch the exact A840 firmware expected by the inherited SM8850 driver."""
from pathlib import Path
import hashlib
import urllib.request
ROOT = Path(__file__).resolve().parents[1]
BASE = 'https://raw.githubusercontent.com/Evolution-X-Devices/vendor_xiaomi_sm8850-common/e683a6ce2fc1c422617eb54c858d4be8baa170af/'
FILES = [('gen80200_gmu.bin', 'proprietary/vendor/firmware/gen80200_gmu.bin', 112142, '4069397c9d214bdac9a55902603c5bea1cfd2e5882a4963fb60ec26a2490978b'), ('gen80200_sqe.fw', 'proprietary/vendor/firmware/gen80200_sqe.fw', 119156, 'e2d4e74282f50e40788b83b9ba4a5f5894c7975ed356c03a0161372d78f12932'), ('gen80200_aqe.fw', 'proprietary/vendor/firmware/gen80200_aqe.fw', 25880, 'ed7916ca84e663d63fa94b0d40cc8c222e362e6cff860c539a8cca30d3721b68'), ('gen80200_zap.mbn', 'proprietary/odm/firmware/gen80200_zap.mbn', 12088, '48e50309e02c6c37a4c1e4a68a5371cb3d839029e7fbdb075ed4ae4e5712519c')]
directory = ROOT / '.cache/firmware/myron-gpu'
directory.mkdir(parents=True, exist_ok=True)
for name, remote, size, digest in FILES:
    path = directory / name
    data = path.read_bytes() if path.exists() else urllib.request.urlopen(BASE + remote, timeout=60).read()
    if len(data) != size or hashlib.sha256(data).hexdigest() != digest:
        raise SystemExit('A840 firmware mismatch: ' + name)
    path.write_bytes(data)
    print('Verified A840 firmware:', name)

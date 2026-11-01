#!/usr/bin/env python3
"""Read-only PE identity report. Never loads, patches, or authorizes the game."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct

TARGET = {
    'version': '1.9.7.17.J460',
    'size': 9176064,
    'sha256': 'b3c7fdbfce664d2600f1403f290c2a8d0df7a544d1a529295ff664173fd98469',
}


def inspect_pe(data):
    def unpack(fmt, offset):
        if offset < 0 or offset + struct.calcsize(fmt) > len(data):
            raise ValueError('Truncated PE header')
        return struct.unpack_from(fmt, data, offset)

    if data[:2] != b'MZ':
        raise ValueError('Missing DOS header')
    pe, = unpack('<I', 0x3c)
    if pe < 0x40 or data[pe:pe + 4] != b'PE\0\0':
        raise ValueError('Missing PE signature')
    machine, count, timestamp, _, _, optional_size, flags = unpack('<HHIIIHH', pe + 4)
    optional = pe + 24
    magic, = unpack('<H', optional)
    if machine != 0x14c or magic != 0x10b:
        raise ValueError('Expected Intel i386 PE32')
    if not flags & 2 or flags & 0x2000:
        raise ValueError('Expected an executable, not a DLL')
    if not 1 <= count <= 96 or optional_size < 96:
        raise ValueError('Invalid PE header sizes')
    unpack(f'<{optional_size}s', optional)
    entry, = unpack('<I', optional + 16)
    image_base, = unpack('<I', optional + 28)
    sections = []
    for i in range(count):
        name, virtual_size, rva, raw_size, raw_offset, _, _, _, _, characteristics = unpack(
            '<8sIIIIIIHHI', optional + optional_size + i * 40)
        if raw_size and (raw_offset == 0 or raw_offset + raw_size > len(data)):
            raise ValueError('Section extends past file bounds')
        sections.append(dict(name=name.rstrip(b'\0').decode('ascii', errors='replace'),
                             rva=rva, virtual_size=virtual_size, raw_size=raw_size,
                             raw_offset=raw_offset, executable=bool(characteristics & 0x20000000),
                             sha256=hashlib.sha256(data[raw_offset:raw_offset+raw_size]).hexdigest()))
    if not any(s['executable'] and s['rva'] <= entry < s['rva'] + max(s['virtual_size'], s['raw_size']) for s in sections):
        raise ValueError('Entry point outside executable sections')
    return dict(machine='i386', format='PE32', entry_rva=entry, image_base=image_base,
                timestamp=timestamp, sections=sections)


def report(data):
    result = inspect_pe(data)
    result.update(size=len(data), sha256=hashlib.sha256(data).hexdigest(),
                  version_strings=sorted(set(m.decode('ascii') for m in re.findall(rb'1\.9\.7\.\d+\.J\d+', data))))
    result['matches_requested_identity'] = result['size'] == TARGET['size'] and result['sha256'] == TARGET['sha256']
    result['runtime_compatibility'] = 'UNVERIFIED'
    result['safe_to_install'] = False
    result['reason'] = 'Identity and section hashes are diagnostic evidence only; hooks, ABI, layouts and CrossOver runtime remain unvalidated.'
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable', type=Path)
    args = parser.parse_args()
    try:
        result = report(args.executable.read_bytes())
    except (OSError, ValueError) as exc:
        print(json.dumps({'error': str(exc), 'safe_to_install': False}))
        return 1
    print(json.dumps(result, indent=2))
    return 2  # A diagnostic report is never a compatibility approval.


if __name__ == '__main__':
    raise SystemExit(main())

#!/usr/bin/env python3
"""Conservative raw-byte triage, NOT a LibZHL emulator or hook validator."""
import argparse
from collections import Counter
import json
from pathlib import Path
import re
import struct

from preflight import report


TOKEN = re.compile(r'"(?:\\.|[^"\\])*"|/\*.*?\*/|//[^\n]*', re.S)


def uncomment(text):
    return TOKEN.sub(lambda m: m[0] if m[0].startswith('"') else ''.join('\n' if c == '\n' else ' ' for c in m[0]), text)


def pattern(signature):
    cleaned = re.sub(r'[.!()]', '', signature)
    if not cleaned or len(cleaned) % 2 or re.search(r'[^0-9a-fA-F?]', cleaned):
        raise ValueError('Not an explicit byte pattern')
    # LibZHL treats either unknown nibble as a wildcard for the whole byte.
    return [None if '?' in cleaned[i:i+2] else int(cleaned[i:i+2], 16) for i in range(0, len(cleaned), 2)]


def matches(data, signature, limit=64):
    values = pattern(signature)
    runs = list(re.finditer(r'[^?]+', ''.join('?' if v is None else 'x' for v in values)))
    if not runs:
        raise ValueError('No fixed bytes')
    anchor = max(runs, key=lambda m: len(m[0]))
    needle = bytes(values[anchor.start():anchor.end()])
    results = []
    pos = 0
    while True:
        found = data.find(needle, pos)
        if found < 0:
            return results, False
        pos = found + 1
        start = found - anchor.start()
        if start >= 0 and start + len(values) <= len(data) and all(v is None or data[start+i] == v for i, v in enumerate(values)):
            results.append(start)
            if len(results) >= limit:
                return results, True


def inventory(root):
    for path in sorted((root / 'libzhl/functions').glob('*.zhl')):
        text = uncomment(path.read_text())
        # Includes generated ASM registrations as well as function/variable signatures.
        regex = r'asm\s+(\w+)\s+"([^"\n]*)"|"([^"\n]*)"\s*:\s*([^;]+;)'
        for m in re.finditer(regex, text):
            yield dict(source=str(path.relative_to(root)), line=text.count('\n', 0, m.start())+1,
                       kind='asm' if m[1] else 'zhl', name=m[1] or ' '.join(m[4].split()),
                       signature=m[2] if m[1] else m[3])
    # Candidate literals include dynamic helper inputs, not only direct SigScan constructors.
    # These are intentionally distinguished from ZHL registrations; C++ expressions/macros
    # and generated/stateful signatures can require additional manual inventory.
    for path in sorted((root / 'repentogon').rglob('*.cpp')):
        text = uncomment(path.read_text())
        for m in re.finditer(r'"([.!()0-9a-fA-F?]{12,})"', text):
            yield dict(source=str(path.relative_to(root)), line=text.count('\n',0,m.start())+1,
                       kind='cpp_candidate', name='literal candidate; inspect caller', signature=m[1])


def scan(executable, root):
    data = executable.read_bytes()
    identity = report(data)
    pe, = struct.unpack_from('<I', data, 0x3c)
    image_size, headers_size = struct.unpack_from('<II', data, pe+24+56)
    if not 0 < headers_size <= len(data) or not headers_size <= image_size <= 256*1024*1024:
        raise ValueError('Invalid or excessive image size')
    image = bytearray(image_size)
    image[:headers_size] = data[:headers_size]
    for section in identity['sections']:
        start, size = section['rva'], section['raw_size']
        if start < headers_size or start + max(size, section['virtual_size']) > image_size:
            raise ValueError('Section outside image bounds')
        image[start:start+size] = data[section['raw_offset']:section['raw_offset']+size]
    rows = []
    for entry in inventory(root):
        sig = entry['signature']
        try:
            offsets, capped = matches(image, sig)
            entry.update(status='missing' if not offsets else 'single_raw_match' if len(offsets)==1 else 'multiple_raw_matches',
                         rvas=[hex(o) for o in offsets], count_capped=capped,
                         stateful='.' in sig, capture_groups='(' in sig)
        except ValueError as exc:
            entry.update(status='not_scanned', reason=str(exc))
        rows.append(entry)
    return dict(identity=identity, scope='Source-literal static triage at preferred image base. No relocations/import resolution, ordered scan state, return seeking, ABI/layout or patch validation. Raw match is not compatibility.',
                summary={kind: dict(Counter(e['status'] for e in rows if e['kind']==kind)) for kind in ('zhl','asm','cpp_candidate')}, entries=rows)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable', type=Path)
    parser.add_argument('--source', type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    print(json.dumps(scan(args.executable, args.source), indent=2))
    raise SystemExit(2)

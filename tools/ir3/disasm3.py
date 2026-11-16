#!/usr/bin/env python3
"""Disassemble IR3 instructions using Mesa's ISA XML patterns.

The XML in work/ir3/ is the authoritative encoding (same data the official
ir3-disasm is generated from); matching is done by pattern bitset, not by
guessed field offsets.

    python3 work/ir3/disasm3.py work/santoni-xnu/tools/ir3/kind4.bin
"""
import sys
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent


def parse_bitsets(path):
    out = {}
    for bs in ET.parse(path).getroot().iter('bitset'):
        pats = []
        for p in bs.findall('pattern'):
            t = (p.text or '').strip()
            if p.get('pos') is not None:
                lo = hi = int(p.get('pos'))
            else:
                lo, hi = int(p.get('low')), int(p.get('high'))
            pats.append((lo, hi, t))
        out[bs.get('name')] = {'extends': bs.get('extends'), 'pats': pats}
    return out


SETS = {}
for f in ['ir3.xml'] + sorted(p.name for p in ROOT.glob('ir3-cat*.xml')):
    SETS.update(parse_bitsets(ROOT / f))
NAMES = [n for n in SETS if not n.startswith('#')]


def chain(n):
    out = []
    while n and n in SETS:
        out.append(n)
        n = SETS[n]['extends']
    return out


def matches(word, name):
    for n in chain(name):
        for lo, hi, text in SETS[n]['pats']:
            for i, ch in enumerate(text):
                if ch == 'x':
                    continue
                if ((word >> (hi - i)) & 1) != int(ch):
                    return False
    return True


def decode(word):
    best = None
    for n in NAMES:
        if matches(word, n):
            depth = len(chain(n))
            if best is None or depth > best[0]:
                best = (depth, n)
    return best[1] if best else '?'


def main():
    for path in sys.argv[1:]:
        data = Path(path).read_bytes()
        print(f'=== {path}')
        for i in range(0, len(data) - 7, 8):
            lo = int.from_bytes(data[i:i + 4], 'little')
            hi = int.from_bytes(data[i + 4:i + 8], 'little')
            w = (hi << 32) | lo
            if not w:
                continue
            print(f'  [{i // 8:02d}] cat{(w >> 61) & 7}  {decode(w):12s} {w:016x}')


if __name__ == '__main__':
    main()

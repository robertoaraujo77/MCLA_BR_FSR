"""Regenerate the optional Flash-menu translation lookup as UTF-8 C++ literals."""
from pathlib import Path
import json

root = Path(__file__).resolve().parents[1]
table = json.loads((root / 'localization/pt-BR/host-menu-texts.json').read_text(encoding='utf8'))
header = root / 'src/ptbr_menu.h'
source = header.read_text(encoding='ascii')
start = source.index('  static const Pair pairs[] = {')
end = source.index('  };', start) + 4


def literal(text):
    return '"' + ''.join('\\%03o' % byte if byte >= 128 else
                         ('\\' + chr(byte) if chr(byte) in '\\"' else chr(byte))
                         for byte in text.encode('utf8')) + '"'


block = '  static const Pair pairs[] = {\n' + '\n'.join(
    '    {' + literal(en) + ', ' + literal(pt) + '},' for en, pt in table.items()) + '\n  };'
header.write_text(source[:start] + block + source[end:], encoding='ascii')
print(f'Generated {len(table)} UTF-8 menu translations.')

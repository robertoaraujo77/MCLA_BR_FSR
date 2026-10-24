"""Build translated resources locally; never modify the original archive.
English text only; preserve other languages, control tags and subtitle timing.
Source text and game assets are not included in this repository.
"""
from pathlib import Path
import ast
import argparse
import csv
import ctypes
from ctypes import wintypes
import hashlib
import io
import json
import re
import shutil
import struct
import zlib
import uuid

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / 'localization' / 'pt-BR'


def helpers():
    source = ROOT / 'launcher/dev/shaderpack/build_pack.py'
    wanted = {'_aes', 'retail_key', 'decrypted_image'}
    nodes = [n for n in ast.parse(source.read_text(encoding='utf8')).body
             if isinstance(n, ast.FunctionDef) and n.name in wanted]
    scope = dict(ctypes=ctypes, wintypes=wintypes, struct=struct, re=re,
                 _bcrypt=ctypes.WinDLL('bcrypt'))
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(source), 'exec'), scope)
    # BCryptEncrypt has the same buffer contract as BCryptDecrypt. Preserve
    # the retail archive's TOC encryption; the guest's RPF reader expects it.
    encrypt = ast.parse(ast.unparse(next(n for n in nodes if n.name == '_aes'))).body[0]
    encrypt.name = '_encrypt'
    for node in ast.walk(encrypt):
        if isinstance(node, ast.Attribute) and node.attr == 'BCryptDecrypt':
            node.attr = 'BCryptEncrypt'
    exec(compile(ast.fix_missing_locations(ast.Module(body=[encrypt], type_ignores=[])),
                 str(source), 'exec'), scope)
    return scope


def read_index(path, aes, key):
    with path.open('rb') as f:
        header = list(struct.unpack('<4sIIII', f.read(20)))
        assert header[0] == b'RPF3'
        f.seek(0x800)
        toc = f.read(header[1])
    if header[4]:
        for _ in range(16):
            toc = aes(key, toc, 'ChainingModeECB')
    entries = [struct.unpack_from('<4I', toc, i * 16) for i in range(header[2])]
    return header, bytearray(toc), entries


def read_entry(f, entry):
    _, length, offset, packed = entry
    assert not (offset & 0x80000000) and packed >> 30 in (0, 1)
    f.seek(offset)
    data = f.read((packed & 0x3fffffff) if packed >> 30 else length)
    result = zlib.decompress(data, -15) if packed >> 30 else data
    assert len(result) == length
    return result


def rows(data):
    wide = data.startswith(b'\xff\xfe')
    return [r for r in csv.reader(io.StringIO(data.decode('utf-16' if wide else 'cp1252'),
                                            newline=''), delimiter='\t' if wide else ',') if r]


def translate(data, translations):
    source = rows(data)
    assert source[0][:2] == ['Time Code', 'English']
    target = [r.copy() for r in source]
    count = 0
    for original, changed in zip(source[1:], target[1:]):
        text = original[1].strip() if len(original) > 1 else ''
        if text and text.lower() not in ('time correction', 'position', 'size'):
            ident = hashlib.sha256(text.encode()).hexdigest()[:12]
            changed[1] = translations[ident]
            count += 1
        assert changed[:1] == original[:1] and changed[2:] == original[2:]
    output = io.StringIO(newline='')
    wide = data.startswith(b'\xff\xfe')
    csv.writer(output, delimiter='\t' if wide else ',',
               lineterminator='\r\n' if wide else '\r\r\n').writerows(target)
    encoded = output.getvalue().encode('utf-16' if wide else 'cp1252')
    assert rows(encoded) == target
    return encoded, count


def translate_bundle(data, changes):
    """Replace only selected English records in the game's multilingual table."""
    count = struct.unpack_from('<I', data)[0]
    assert count == 11
    offsets = list(struct.unpack_from('<11I', data, 4))
    start, end = offsets[:2]
    pos = start
    records = struct.unpack_from('<I', data, pos)[0]
    pos += 4
    output = bytearray(struct.pack('<I', records))
    updated = []
    for _ in range(records):
        record_start = pos
        ident, flags, font_length = struct.unpack_from('<IHI', data, pos)
        pos += 10 + font_length
        length_pos = pos
        length = struct.unpack_from('<I', data, pos)[0]
        pos += 4
        text_pos = pos
        text = data[pos:pos + length * 2].decode('utf-16le').rstrip('\0')
        pos += length * 2 + 10
        key = f'{ident:08x}'
        if key in changes:
            expected, translated = changes[key]
            assert hashlib.sha256(text.encode('utf8')).hexdigest() == expected, key
            assert re.findall(r'<[^>]+>', text) == re.findall(r'<[^>]+>', translated)
            encoded = (translated + '\0').encode('utf-16le')
            output.extend(data[record_start:length_pos])
            output.extend(struct.pack('<I', len(encoded) // 2))
            output.extend(encoded)
            output.extend(data[text_pos + length * 2:pos])
            updated.append(key)
        else:
            output.extend(data[record_start:pos])
    assert pos == end
    delta = len(output) - (end - start)
    result = bytearray(data[:start] + output + data[end:])
    for index in range(1, count):
        struct.pack_into('<I', result, 4 + index * 4, offsets[index] + delta)
    # Keys, non-English language blocks and unselected records are copied.
    assert result[end + delta:] == data[end:]
    return bytes(result), updated


def main():
    parser = argparse.ArgumentParser(description="Build PT-BR assets locally from your extracted game.")
    parser.add_argument('--game-root', type=Path, default=ROOT / 'game')
    parser.add_argument('--output', type=Path, default=ROOT / 'out/localization/pt-BR/game')
    parser.add_argument('--update', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--compact', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args()
    game = args.output.resolve()
    source_root = args.game_root.resolve()
    if game == source_root:
        raise ValueError('Translation output must differ from original game directory')
    translations = json.loads((WORK / 'dialogue-pt-BR.json').read_text(encoding='utf8'))
    native = json.loads((WORK / 'native-texts.json').read_text(encoding='utf8'))
    files = json.loads((WORK / 'subtitle-files.json').read_text(encoding='utf8')) + native['bundles']
    expected = {item['entry']: item['source_sha256'] for item in files}
    bundles = {item['entry'] for item in native['bundles']}
    changes = {key: (record['source_sha256'], record['translation'])
               for key, record in native['records'].items()}
    original = source_root / 'xarchive_cache.rpf'
    # Inputs include source identity, curated translations and this builder revision.
    inputs = hashlib.sha256(Path(__file__).read_bytes())
    for name in ('dialogue-pt-BR.json', 'native-texts.json', 'subtitle-files.json'):
        inputs.update((WORK / name).read_bytes())
    for path in (original, source_root / 'default.xex'):
        stat = path.stat()
        inputs.update(str((str(path), stat.st_size, stat.st_mtime_ns)).encode())
    fingerprint = inputs.hexdigest()
    marker = game / '.mcla-ptbr.json'
    installed = game / original.name
    if marker.exists() and installed.exists():
        previous = json.loads(marker.read_text(encoding='utf8'))
        if previous.get('fingerprint') == fingerprint:
            print('PT-BR archive already up to date:', installed)
            return
    api = helpers()
    image = api['decrypted_image'](source_root / 'default.xex', ROOT / 'third_party/rexglue-sdk')
    key = image[0x7d8ac4:0x7d8ae4]
    header, toc, entries = read_index(original, api['_aes'], key)
    game.mkdir(parents=True, exist_ok=True)
    destination = game / ('xarchive_cache.build-' + uuid.uuid4().hex[:8] + '.rpf')
    changed_files = []
    selected_keys = set()
    try:
        shutil.copyfile(original, destination)
        with original.open('rb') as source, destination.open('r+b') as output:
            output.seek(0, 2)
            for ident in sorted(expected):
                before = read_entry(source, entries[ident])
                if hashlib.sha256(before).hexdigest() != expected[ident]:
                    raise ValueError(f'Unsupported game resource {ident}; original archive differs from validated Complete Edition')
                if ident in bundles:
                    after, selected = translate_bundle(before, changes)
                    selected_keys.update(selected)
                    count = len(selected)
                else:
                    after, count = translate(before, translations)
                compressor = zlib.compressobj(9, zlib.DEFLATED, -15)
                packed = compressor.compress(after) + compressor.flush()
                output.write(bytes((-output.tell()) % 16))
                offset = output.tell()
                if offset >= 0x80000000:
                    raise ValueError('Archive offset exceeds RPF3 format limit')
                output.write(packed)
                struct.pack_into('<4I', toc, ident * 16, entries[ident][0], len(after),
                                 offset, 0x40000000 | len(packed))
                changed_files.append(dict(entry=ident, lines=count,
                    source_sha256=hashlib.sha256(before).hexdigest(),
                    translated_sha256=hashlib.sha256(after).hexdigest()))
            if selected_keys != set(changes):
                raise ValueError('Not all curated native translations matched the source')
            disk_toc = bytes(toc)
            if header[4]:
                for _ in range(16):
                    disk_toc = api['_encrypt'](key, disk_toc, 'ChainingModeECB')
            output.seek(0x800)
            output.write(disk_toc)
        _, _, verify = read_index(destination, api['_aes'], key)
        assert {i for i in range(len(entries)) if entries[i] != verify[i]} == set(expected)
        with destination.open('rb') as output:
            for item in changed_files:
                assert hashlib.sha256(read_entry(output, verify[item['entry']])).hexdigest() == item['translated_sha256']
        for path in source_root.iterdir():
            if path.is_file() and path.name != original.name:
                linked = game / path.name
                if not linked.exists():
                    try:
                        linked.hardlink_to(path)
                    except OSError:
                        shutil.copy2(path, linked)
        # Publish only a fully verified archive. Existing good output survives errors.
        destination.replace(installed)
        manifest = dict(format=1, language='pt-BR', fingerprint=fingerprint,
                        native_records=len(changes), dialogue_lines=len(translations), files=changed_files)
        temporary_marker = marker.with_suffix('.tmp')
        temporary_marker.write_text(json.dumps(manifest, indent=2), encoding='utf8')
        temporary_marker.replace(marker)
    finally:
        destination.unlink(missing_ok=True)
    print(f'Built PT-BR: {len(files)} resources, {len(changes)} native strings, {len(translations)} dialogue lines.')
    print('Verified original hashes, control tags, other languages and translated resource hashes.')


if __name__ == '__main__':
    main()

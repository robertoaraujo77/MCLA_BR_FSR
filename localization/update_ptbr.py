"""Bring an already translated installation up to this release's PT-BR catalog.

No ISO is needed: only the records that are still the original English (or that
an earlier run of this tool translated) are rewritten, inside the game's own
resource tables. The archive is rewritten as a copy, checked, and swapped in
only when it is whole, so a failure leaves the installed one as it was.
"""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import struct
import sys
import uuid
import zlib

# The embedded Python of the installer does not look in the script's own folder.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_ptbr as bp  # noqa: E402


def digest(data):
    return hashlib.sha256(data).hexdigest()


def update(game, sdk=None, log=print):
    """Returns the number of records changed; raises ValueError if the install isn't as expected."""
    game = Path(game).resolve()
    marker_path = game / '.mcla-ptbr.json'
    installed = game / 'xarchive_cache.rpf'
    if not marker_path.is_file() or not installed.is_file():
        log('Esta instalacao nao tem a traducao PT-BR; nada a atualizar.')
        return 0
    marker = json.loads(marker_path.read_text(encoding='utf8'))
    native = json.loads((bp.WORK / 'native-texts.json').read_text(encoding='utf8'))
    changes = {key: (record['source_sha256'], record['translation'])
               for key, record in native['records'].items()}
    earlier = marker.get('native_applied', {})
    known = {item['entry']: item['translated_sha256'] for item in marker.get('files', [])}

    def replaceable(key, text):
        current = digest(text.encode('utf8'))
        expected, translated = changes[key]
        if current == digest(translated.encode('utf8')):
            return False
        return current == expected or earlier.get(key) == current

    api = bp.helpers()
    image = api['decrypted_image'](game / 'default.xex', sdk or bp.ROOT / 'third_party/rexglue-sdk')
    key = image[0x7d8ac4:0x7d8ae4]
    header, toc, entries = bp.read_index(installed, api['_aes'], key)
    work = []
    done = set()
    with installed.open('rb') as source:
        for item in native['bundles']:
            ident = item['entry']
            before = bp.read_entry(source, entries[ident])
            if digest(before) not in (known.get(ident), item['source_sha256']):
                raise ValueError(f'O recurso {ident} foi alterado por outro programa; nada foi modificado.')
            after, updated = bp.translate_bundle(before, changes, replaceable)
            work.append((ident, before, after))
            done.update(updated)
    changed = [item for item in work if item[1] != item[2]]
    if not changed:
        log('A traducao ja esta atualizada.')
        return 0
    needed = installed.stat().st_size + (64 << 20)
    if shutil.disk_usage(game).free < needed:
        raise ValueError('Espaco livre insuficiente para atualizar a traducao (' + str(needed >> 20) + ' MB).')

    log(f'Atualizando a traducao: {len(done)} textos novos ou revisados.')
    temporary = game / ('xarchive_cache.update-' + uuid.uuid4().hex[:8] + '.rpf')
    try:
        shutil.copyfile(installed, temporary)
        written = {}
        with temporary.open('r+b') as output:
            output.seek(0, 2)
            for ident, _, after in changed:
                where = digest(after)
                if where not in written:
                    compressor = zlib.compressobj(9, zlib.DEFLATED, -15)
                    packed = compressor.compress(after) + compressor.flush()
                    output.write(bytes((-output.tell()) % 16))
                    offset = output.tell()
                    if offset >= 0x80000000:
                        raise ValueError('O arquivo do jogo excede o limite do formato RPF3.')
                    output.write(packed)
                    written[where] = (offset, len(packed))
                offset, length = written[where]
                struct.pack_into('<4I', toc, ident * 16, entries[ident][0], len(after), offset,
                                 0x40000000 | length)
            disk_toc = bytes(toc)
            if header[4]:
                for _ in range(16):
                    disk_toc = api['_encrypt'](key, disk_toc, 'ChainingModeECB')
            output.seek(0x800)
            output.write(disk_toc)
        _, _, verify = bp.read_index(temporary, api['_aes'], key)
        assert {i for i in range(len(entries)) if entries[i] != verify[i]} == {item[0] for item in changed}
        with temporary.open('rb') as check:
            for ident, _, after in changed:
                assert digest(bp.read_entry(check, verify[ident])) == digest(after)
        temporary.replace(installed)
    finally:
        temporary.unlink(missing_ok=True)

    for ident, _, after in changed:
        for item in marker['files']:
            if item['entry'] == ident:
                item['translated_sha256'] = digest(after)
    marker['native_records'] = len(changes)
    marker['native_applied'] = dict(earlier, **{k: digest(changes[k][1].encode('utf8')) for k in done})
    marker.pop('fingerprint', None)
    fresh = marker_path.with_suffix('.tmp')
    fresh.write_text(json.dumps(marker, indent=2), encoding='utf8')
    fresh.replace(marker_path)
    log('Traducao atualizada e verificada.')
    return len(done)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--game', type=Path, required=True, help='the installation\'s game folder')
    args = parser.parse_args()
    update(args.game)


if __name__ == '__main__':
    main()

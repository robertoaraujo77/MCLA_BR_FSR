"""Fetch the exact official AMD headers/providers used by this fork.

No AMD binaries are stored in Git. Downloads are pinned by revision and SHA-256.
The providers keep AMD's license; this script does not relicense them.
"""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import urllib.request
import uuid

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def prepare(sdk, runtime):
    manifest = json.loads((ROOT / 'scripts/amd-fsr-manifest.json').read_text())
    runtime.mkdir(parents=True, exist_ok=True)
    for item in manifest['files']:
        relative = Path(item.get('target', item['path']))
        if relative.is_absolute() or '..' in relative.parts:
            raise ValueError('Invalid AMD manifest path')
        target = (sdk / 'thirdparty/fsr-redstone' / relative if item['destination'] == 'sdk'
                  else runtime / relative.name)
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() and digest(target) == item['sha256']:
            continue
        url = (f"https://raw.githubusercontent.com/{manifest['repository']}/"
               f"{manifest['revision']}/{item['path']}")
        temporary = target.with_name(target.name + '.download-' + uuid.uuid4().hex[:8])
        try:
            print('AMD:', item['path'], flush=True)
            request = urllib.request.Request(url, headers={'User-Agent': 'MCLA-BR-FSR-build'})
            with urllib.request.urlopen(request, timeout=120) as source, temporary.open('wb') as dest:
                shutil.copyfileobj(source, dest)
            if digest(temporary) != item['sha256']:
                raise ValueError(f'AMD download checksum mismatch: {relative}')
            temporary.replace(target)
        finally:
            temporary.unlink(missing_ok=True)
    shutil.copy2(sdk / 'thirdparty/fsr-redstone/LICENSE.md', runtime / 'AMD-FSR-LICENSE.md')
    print('Verified official AMD providers: upscaler 4.1.2; Frame Generation 4.0.2.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sdk', type=Path, default=ROOT / 'third_party/rexglue-sdk')
    parser.add_argument('--runtime-dir', type=Path, default=ROOT / 'out/deps/amd-fsr')
    args = parser.parse_args()
    prepare(args.sdk.resolve(), args.runtime_dir.resolve())

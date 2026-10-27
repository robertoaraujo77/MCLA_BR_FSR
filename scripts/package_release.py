"""Build the release archives: the player package and the complete source archive.

    python scripts/package_release.py --version 1.0.1

Needs the installer built (installer/source/build.ps1) and a clean git tree, so that
the source archive is exactly what the tag holds. Writes into out/releases/v<version>.
The source archive has every tracked file plus the patched SDK (with its dependencies,
without build output) and a manifest of that SDK's files that scripts/prepare_sdk.ps1
verifies, the layout the v1.0.0 archive had.
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SDK = ROOT / 'third_party/rexglue-sdk'
EXE = ROOT / 'installer/dist/Midnight Club L.A. Recompiled.exe'
SDK_SKIPPED_NAMES = {'.git', '.mcla-patched', '.mcla-patches'}
SDK_SKIPPED_FILES = {'thirdparty/FFmpeg/config_ps5_x86_64.h'}  # written by FFmpeg's configure step
CRLF = chr(13) + chr(10)


def sha256(path):
    with open(path, 'rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def git_lines(repository, *arguments):
    return subprocess.run(['git', '-C', str(repository)] + list(arguments), capture_output=True, text=True,
                          check=True).stdout.splitlines()


def sdk_repositories():
    """The SDK and each dependency checked out inside it, as folders."""
    found = [SDK]
    for folder, directories, files in os.walk(SDK):
        relative = Path(folder).relative_to(SDK)
        if str(relative) != '.' and ('.git' in directories or '.git' in files):
            found.append(Path(folder))
        directories[:] = [d for d in directories if d != '.git' and not (str(relative) == '.' and d == 'out')]
    return found


def sdk_state():
    """(placeholders, patched): symbolic links git keeps as a file holding the link's target and
    that still are exactly that, which an archive cannot carry (the v1.0.0 one left them out; the
    expanded ones, libmspack's, are not that and go in), and the files the patches changed or
    added in the SDK itself, which the archive keeps with LF line endings as the v1.0.0 one did
    (the dependencies keep the line endings they have)."""
    placeholders, patched = set(), set()
    for repository in sdk_repositories():
        prefix = repository.relative_to(SDK).as_posix() + '/' if repository != SDK else ''
        links = [line.split(None, 3) for line in git_lines(repository, 'ls-files', '-s') if line.startswith('120000')]
        for _, blob, _, path in links:
            candidate = repository / path
            if candidate.is_file() and git_lines(repository, 'hash-object', path)[0] == blob:
                placeholders.add(prefix + path)
        for line in git_lines(repository, 'status', '--porcelain=v1', '--untracked-files=all'):
            if repository == SDK and line[:2].strip() in ('M', '??', 'A'):
                patched.add(line[3:].strip('"'))
    return placeholders, patched


def sdk_content(path, patched):
    data = (SDK / path).read_bytes()
    if path in patched and bytes([0]) not in data[:8192]:
        data = data.replace(bytes([13, 10]), bytes([10]))
    return data


def sdk_files():
    found = []
    for folder, directories, files in os.walk(SDK):
        relative = Path(folder).relative_to(SDK)
        directories[:] = [d for d in directories
                          if d not in SDK_SKIPPED_NAMES and not (str(relative) == '.' and d == 'out')]
        for name in files:
            path = (relative / name).as_posix() if str(relative) != '.' else name
            if name not in SDK_SKIPPED_NAMES and path not in SDK_SKIPPED_FILES:
                found.append(path)
    return sorted(found)


def player_package(destination):
    sums = sha256(EXE) + '  ' + EXE.name + CRLF
    with zipfile.ZipFile(destination, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as package:
        for name in ('CREDITS.md', 'LICENSE', 'THIRD-PARTY-NOTICES.md'):
            package.write(ROOT / name, name)
        package.write(ROOT / 'release/LEIA-ME.txt', 'LEIA-ME.txt')
        package.write(EXE, EXE.name)
        package.writestr('SHA256SUMS.txt', sums)


def source_package(destination):
    tracked = subprocess.run(['git', '-C', str(ROOT), 'ls-files'], capture_output=True, text=True,
                             check=True).stdout.split()
    placeholders, patched = sdk_state()
    files = [path for path in sdk_files() if path not in placeholders]
    contents = {path: sdk_content(path, patched) for path in files}
    manifest = dict(sdk_commit=json.loads((ROOT / 'patches/dependencies.json').read_text())['sdk_commit'],
                    files=[dict(path=path, sha256=hashlib.sha256(contents[path]).hexdigest()) for path in files])
    base = 'MC_LA_Recompiled/'
    with zipfile.ZipFile(destination, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as package:
        for path in tracked:
            package.write(ROOT / path, base + path)
        for path in files:
            info = zipfile.ZipInfo.from_file(SDK / path, base + 'third_party/rexglue-sdk/' + path)
            info.compress_type = zipfile.ZIP_DEFLATED
            package.writestr(info, contents[path], compresslevel=9)
        package.writestr(base + 'third_party/rexglue-sdk/.release-source-manifest.json',
                         json.dumps(manifest, indent=1))
    return len(tracked), len(files), len(placeholders), len(patched)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version', required=True)
    parser.add_argument('--allow-dirty', action='store_true')
    args = parser.parse_args()
    if not EXE.is_file():
        sys.exit('Build the installer first: installer/source/build.ps1')
    dirty = subprocess.run(['git', '-C', str(ROOT), 'status', '--porcelain'], capture_output=True, text=True,
                           check=True).stdout.strip()
    if dirty and not args.allow_dirty:
        sys.exit('The git tree has uncommitted changes; commit them first:' + chr(10) + dirty)
    out = ROOT / 'out/releases' / ('v' + args.version)
    out.mkdir(parents=True, exist_ok=True)
    player = out / 'Midnight-Club-LA-Recompiled-Windows-x64.zip'
    source = out / ('MC_LA_Recompiled-v' + args.version + '-source.zip')
    player_package(player)
    counts = source_package(source)
    lines = ''.join(sha256(path) + '  ' + path.name + CRLF for path in (player, source))
    (out / 'SHA256SUMS.txt').write_bytes(lines.encode('ascii'))
    print('Tracked files:', counts[0], '| SDK files:', counts[1], '| link placeholders left out:', counts[2],
          '| patched files kept with LF:', counts[3])
    print(lines)


if __name__ == '__main__':
    main()

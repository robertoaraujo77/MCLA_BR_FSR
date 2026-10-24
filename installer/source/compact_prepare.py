"""Prepare local game data using an already compiled PC runtime. No compiler or downloads.
This local test package is deliberately isolated from existing installations and saves.
"""
import argparse
import base64
import re
import tomllib
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import uuid
import zipfile

IDENTITY = 'mcla-la-recompiled'


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def safe_extract(archive, destination):
    destination = destination.resolve()
    with zipfile.ZipFile(archive) as package:
        for item in package.infolist():
            target = (destination / item.filename).resolve()
            if not target.is_relative_to(destination):
                raise ValueError('Unsafe package path: ' + item.filename)
        package.extractall(destination)


def verify(bundle):
    manifest = json.loads((bundle / 'payload/manifest.json').read_text(encoding='utf8'))
    for entry in manifest['files']:
        source = (bundle / entry['path']).resolve()
        if not source.is_relative_to(bundle):
            raise ValueError('Invalid manifest path')
        if not source.is_file() or digest(source) != entry['sha256']:
            raise ValueError('Pacote incompleto ou alterado: ' + entry['path'])
    return manifest


def run(*arguments):
    subprocess.run([str(arg) for arg in arguments], check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', type=Path, required=True)
    parser.add_argument('--destination', type=Path)
    parser.add_argument('--iso', type=Path)
    parser.add_argument('--installer-dir', type=Path)
    parser.add_argument('--graphics-settings')
    parser.add_argument('--verify-only', action='store_true')
    # Maintainer-only data-path check. The normal UI always requires the user's ISO.
    parser.add_argument('--test-extracted-game', type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    bundle = args.bundle.resolve()
    print('[ETAPA 1/4] Verificando o pacote local...', flush=True)
    manifest = verify(bundle)
    if args.verify_only:
        print('Pacote verificado. Nenhum download, compilador ou instalador Microsoft foi executado.', flush=True)
        return
    if args.destination is None:
        parser.error('--destination is required')
    target = args.destination.resolve()
    if args.installer_dir and target == args.installer_dir.resolve():
        raise ValueError('A pasta de instalacao nao pode ser a mesma pasta do executavel do instalador. Escolha outra pasta.')
    marker = target / '.mcla-br-install.json'
    if target == bundle or bundle.is_relative_to(target) or target.is_relative_to(bundle):
        raise ValueError('Escolha uma pasta de jogo separada da pasta deste pacote')
    if target.exists() and any(target.iterdir()):
        if not marker.is_file() or json.loads(marker.read_text()).get('identity') != IDENTITY:
            raise ValueError('A pasta ja contem arquivos de outra instalacao. Escolha uma pasta vazia; nada foi substituido.')
    if args.iso and (not args.iso.is_file() or args.iso.suffix.lower() != '.iso'):
        raise ValueError('Selecione um arquivo ISO existente')
    if not args.iso and not args.test_extracted_game:
        parser.error('--iso is required')
    if args.iso and args.iso.resolve().is_relative_to(target):
        raise ValueError('Mantenha a ISO fora da pasta de destino')
    # Only runtime files are published. Preparation sources stay in a private,
    # automatically cleaned workspace outside the player's installation.
    import tempfile
    with tempfile.TemporaryDirectory(prefix='mcla-prepare-') as temporary_root:
        staging = Path(temporary_root)
        safe_extract(bundle / 'payload/project.zip', staging)
        game = staging / 'game'
        if args.test_extracted_game:
            shutil.copytree(args.test_extracted_game.resolve(), game, dirs_exist_ok=True)
        else:
            run(sys.executable, '-u', staging / 'scripts/extract_game.py', args.iso.resolve(), game)
        print('[ETAPA 3/4] Aplicando a traducao PT-BR aos seus dados...', flush=True)
        localized = staging / 'translated'
        run(sys.executable, '-u', staging / 'localization/build_ptbr.py', '--output', localized)
        target.mkdir(parents=True, exist_ok=True)
        marker.write_text(json.dumps(dict(identity=IDENTITY, phase='preparing'), indent=2))
        output_game = target / 'game'
        output_game.mkdir(exist_ok=True)
        for file in localized.iterdir():
            if file.is_file():
                # Move final assets, never expose preparation sources.
                shutil.move(str(file), str(output_game / file.name))
        for file in (bundle / 'payload/runtime').iterdir():
            if file.is_file():
                fresh = target / (file.name + '.new-' + uuid.uuid4().hex[:8])
                shutil.copy2(file, fresh)
                fresh.replace(target / file.name)
        license_root = target / 'licenses'
        shutil.copytree(bundle / 'payload/licenses', license_root, dirs_exist_ok=True)
        settings = target / 'mcla.toml'
        if not settings.exists():
            run(sys.executable, staging / 'scripts/configure_install.py', '--build', target)
        selected = dict(mcla_button_prompts='xbox', mcla_ptbr=True)
        if args.graphics_settings:
            content = base64.b64decode(args.graphics_settings, validate=True).decode('utf8')
            selected.update(tomllib.loads(content))
        # Always point at this installation's translated assets and profile.
        selected.update(game_data_root=output_game.as_posix(), user_data_root=(target/'userdata').as_posix())
        existing = settings.read_text(encoding='utf8')
        for key in selected:
            existing = re.sub(r'^' + re.escape(key) + r'\s*=.*(?:\n|$)', '', existing, flags=re.MULTILINE)
        content = ''.join(key+' = '+json.dumps(value, ensure_ascii=True)+'\n' for key,value in selected.items())
        fresh = settings.with_suffix('.toml.new')
        fresh.write_text(existing + '\n# Configuracoes desta instalacao\n' + content, encoding='utf8')
        fresh.replace(settings)
        marker.write_text(json.dumps(dict(identity=IDENTITY, phase='ready',
            runtime=manifest.get('runtime_version'), executable='mcla.exe'), indent=2))
    print('[ETAPA 4/4] Pronto! Jogo preparado com suas configuracoes.', flush=True)


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print('ERRO:', error, flush=True)
        sys.exit(1)

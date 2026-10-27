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
import tempfile
import time
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


def backup_saves(target, label):
    """Zip the player's data (not the shader cache) before an update touches anything."""
    settings = target / 'mcla.toml'
    root = target / 'userdata'
    if settings.is_file():
        try:
            configured = tomllib.loads(settings.read_text(encoding='utf8')).get('user_data_root')
            if configured:
                root = Path(configured) if Path(configured).is_absolute() else target / configured
        except Exception:
            pass
    if not root.is_dir():
        return None
    destination = target / 'backups' / ('userdata-' + label + '.zip')
    destination.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with zipfile.ZipFile(destination, 'w', zipfile.ZIP_DEFLATED) as archive:
        for file in sorted(root.rglob('*')):
            relative = file.relative_to(root)
            if file.is_file() and relative.parts[0] != 'cache':
                archive.write(file, relative.as_posix())
                count += 1
    print('Copia dos seus saves guardada: ' + str(destination) + ' (' + str(count) + ' arquivos)', flush=True)
    return destination


def update_install(bundle, manifest, target):
    """Bring a ready installation to this package's release. No ISO, and neither the
    saves (userdata), the settings (mcla.toml) nor the game data are replaced: only the
    runtime, and the PT-BR records this release adds. The old runtime is kept in backups."""
    marker_path = target / '.mcla-br-install.json'
    if not marker_path.is_file() or not (target / 'mcla.exe').is_file():
        raise ValueError('Atualizar exige uma instalacao pronta deste programa.')
    marker = json.loads(marker_path.read_text(encoding='utf8'))
    if marker.get('identity') != IDENTITY or marker.get('phase') != 'ready':
        raise ValueError('Essa pasta nao e uma instalacao pronta deste programa.')
    old_release = marker.get('release', '1.0.0')
    new_release = manifest.get('release_version', old_release)
    print('[ETAPA 2/4] Atualizando da v' + old_release + ' para a v' + new_release
          + '. Seus saves e configuracoes nao serao tocados.', flush=True)
    backup_saves(target, 'antes-da-v' + new_release + '-' + time.strftime('%Y%m%d-%H%M%S'))
    game = target / 'game'
    with tempfile.TemporaryDirectory(prefix='mcla-update-') as temporary_root:
        staging = Path(temporary_root)
        safe_extract(bundle / 'payload/project.zip', staging)
        if (game / '.mcla-ptbr.json').is_file():
            print('[ETAPA 3/4] Atualizando a traducao PT-BR dos seus dados...', flush=True)
            run(sys.executable, '-u', staging / 'localization/update_ptbr.py', '--game', game)
        else:
            print('[ETAPA 3/4] Esta instalacao esta sem traducao; nada a traduzir.', flush=True)
    backup = target / 'backups' / ('runtime-v' + old_release + '-' + time.strftime('%Y%m%d-%H%M%S'))
    for file in (bundle / 'payload/runtime').iterdir():
        if file.is_file():
            current = target / file.name
            if current.is_file():
                backup.mkdir(parents=True, exist_ok=True)
                shutil.copy2(current, backup / file.name)
            fresh = target / (file.name + '.new-' + uuid.uuid4().hex[:8])
            shutil.copy2(file, fresh)
            try:
                fresh.replace(current)
            except PermissionError:
                fresh.unlink(missing_ok=True)
                raise ValueError('Nao foi possivel substituir ' + file.name + '. Feche o jogo e tente de novo.')
    shutil.copytree(bundle / 'payload/licenses', target / 'licenses', dirs_exist_ok=True)
    marker.update(runtime=manifest.get('runtime_version'), release=new_release)
    fresh = marker_path.with_suffix('.json.new')
    fresh.write_text(json.dumps(marker, indent=2))
    fresh.replace(marker_path)
    print('[ETAPA 4/4] Pronto! Atualizado para a v' + new_release + '. Saves e configuracoes mantidos.', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', type=Path, required=True)
    parser.add_argument('--destination', type=Path)
    parser.add_argument('--iso', type=Path)
    parser.add_argument('--installer-dir', type=Path)
    parser.add_argument('--graphics-settings')
    parser.add_argument('--verify-only', action='store_true')
    parser.add_argument('--update', action='store_true', help='update an existing installation; no ISO')
    parser.add_argument('--translate', choices=('1', '0'), default='1', help='apply the PT-BR translation (default) or keep the game in English')
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
    if args.update:
        update_install(bundle, manifest, target)
        return
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
        translate = args.translate == '1'
        if translate:
            print('[ETAPA 3/4] Aplicando a traducao PT-BR aos seus dados...', flush=True)
            localized = staging / 'translated'
            run(sys.executable, '-u', staging / 'localization/build_ptbr.py', '--output', localized)
        else:
            print('[ETAPA 3/4] Traducao PT-BR desativada: mantendo o jogo em ingles...', flush=True)
            localized = game
        target.mkdir(parents=True, exist_ok=True)
        marker.write_text(json.dumps(dict(identity=IDENTITY, phase='preparing'), indent=2))
        output_game = target / 'game'
        output_game.mkdir(exist_ok=True)
        for file in localized.iterdir():
            if file.is_file():
                # Move final assets, never expose preparation sources.
                shutil.move(str(file), str(output_game / file.name))
        if not translate:
            # A reinstall without the translation must not leave an earlier one's marker.
            (output_game / '.mcla-ptbr.json').unlink(missing_ok=True)
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
        selected = dict(mcla_button_prompts='xbox', mcla_ptbr=translate)
        if args.graphics_settings:
            content = base64.b64decode(args.graphics_settings, validate=True).decode('utf8')
            selected.update(tomllib.loads(content))
        # Always point at this installation's translated assets and profile.
        selected.update(game_data_root=output_game.as_posix(), user_data_root=(target/'userdata').as_posix(),
                        mcla_ptbr=translate)
        existing = settings.read_text(encoding='utf8')
        for key in selected:
            existing = re.sub(r'^' + re.escape(key) + r'\s*=.*(?:\n|$)', '', existing, flags=re.MULTILINE)
        content = ''.join(key+' = '+json.dumps(value, ensure_ascii=True)+'\n' for key,value in selected.items())
        fresh = settings.with_suffix('.toml.new')
        fresh.write_text(existing + '\n# Configuracoes desta instalacao\n' + content, encoding='utf8')
        fresh.replace(settings)
        marker.write_text(json.dumps(dict(identity=IDENTITY, phase='ready',
            runtime=manifest.get('runtime_version'), release=manifest.get('release_version'),
            translated=translate, executable='mcla.exe'), indent=2))
    print('[ETAPA 4/4] Pronto! Jogo preparado com suas configuracoes.', flush=True)


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print('ERRO:', error, flush=True)
        sys.exit(1)
